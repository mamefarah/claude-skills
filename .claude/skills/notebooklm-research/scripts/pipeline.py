#!/usr/bin/env python3
"""Higher-level research pipelines for the notebooklm-research skill.

Design note — division of labor (see SKILL.md's Architecture Overview):
NotebookLM does source ingestion, deep research, and cited Q&A. Claude does
original writing. This script only performs the NotebookLM half: it produces
a citation-backed **research brief** (questions asked, cited answers, sources,
optionally a generated report) as structured Markdown/JSON. It deliberately
does NOT fabricate a "finished article" or "social posts" by templating
strings together — a script has no voice and templated output would be worse
than useless. Feed the brief it writes to Claude (in the same conversation
that ran this script) to get the actual article/social copy.

Every pipeline requires a stored NotebookLM login session (see
../docs/SETUP.md) and is run the same way as notebooklm_client.py:

    python3 pipeline.py research-to-article --sources https://a.com https://b.com \\
        --title "AI Agent Frameworks in 2026" --output brief.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth_helper import require_client  # noqa: E402
from notebooklm_client import _jsonable  # noqa: E402

from notebooklm import ReportFormat  # noqa: E402

DEFAULT_QUESTIONS = [
    "What are the key findings or claims across these sources?",
    "Where do the sources agree, and where do they disagree or contradict each other?",
    "What is the most important detail a reader would otherwise miss?",
]


async def _seed_notebook(client, title: str, sources: list[str], text_sources: list[str] | None = None):
    notebook = await client.notebooks.create(title)
    added_ids = []
    for url in sources:
        src = await client.sources.add_url(notebook.id, url)
        added_ids.append(src.id)
    for i, text in enumerate(text_sources or []):
        src = await client.sources.add_text(notebook.id, f"Text source {i + 1}", text)
        added_ids.append(src.id)
    if added_ids:
        await client.sources.wait_for_sources(notebook.id, added_ids)
    return notebook, added_ids


async def _research_brief(
    client,
    notebook_id: str,
    questions: list[str],
    *,
    deep_research_query: str | None = None,
    import_top: int = 5,
    include_report: bool = False,
) -> dict:
    brief: dict = {"notebook_id": notebook_id, "qa": [], "discovered_sources": [], "report": None}

    if deep_research_query:
        start = await client.research.start(notebook_id, deep_research_query, source="web", mode="deep")
        task = await client.research.wait_for_completion(notebook_id, start.task_id)
        if task.sources:
            imported = await client.research.import_sources(
                notebook_id, task.task_id, list(task.sources[:import_top])
            )
            brief["discovered_sources"] = _jsonable(imported)
            new_ids = [s["id"] for s in imported if s.get("id")]
            if new_ids:
                await client.sources.wait_for_sources(notebook_id, new_ids)

    for question in questions:
        result = await client.chat.ask(notebook_id, question)
        brief["qa"].append({"question": question, "answer": result.answer, "references": _jsonable(result.references)})

    if include_report:
        status = await client.artifacts.generate_report(notebook_id, report_format=ReportFormat.BRIEFING_DOC)
        status = await client.artifacts.wait_for_completion(notebook_id, status.task_id)
        if status.status.value == "completed":
            report_path = f"/tmp/notebooklm_report_{notebook_id}.md"
            await client.artifacts.download_report(notebook_id, report_path)
            brief["report"] = Path(report_path).read_text()

    sources = await client.sources.list(notebook_id)
    brief["sources"] = [{"id": s.id, "title": s.title, "url": s.url} for s in sources]
    return brief


def _brief_to_markdown(title: str, brief: dict) -> str:
    lines = [f"# Research brief: {title}", "", f"_NotebookLM notebook: {brief['notebook_id']}_", ""]
    lines.append("## Sources")
    for s in brief["sources"]:
        lines.append(f"- {s['title']}" + (f" — {s['url']}" if s.get("url") else ""))
    lines.append("")
    lines.append("## Cited findings")
    for qa in brief["qa"]:
        lines.append(f"**Q: {qa['question']}**")
        lines.append("")
        lines.append(qa["answer"])
        lines.append("")
    if brief.get("report"):
        lines.append("## NotebookLM briefing doc")
        lines.append(brief["report"])
    lines.append("")
    lines.append(
        "---\n_This is a research brief, not a finished draft. Ask Claude, in this same "
        "conversation, to write the article/post from the cited findings above._"
    )
    return "\n".join(lines)


async def research_to_article(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        if args.notebook:
            notebook_id = args.notebook
        else:
            notebook, _ = await _seed_notebook(client, args.title, args.sources or [], args.text_sources)
            notebook_id = notebook.id

        questions = args.questions or DEFAULT_QUESTIONS
        brief = await _research_brief(
            client, notebook_id, questions,
            deep_research_query=args.deep_research, include_report=args.report,
        )
        markdown = _brief_to_markdown(args.title, brief)
        Path(args.output).write_text(markdown)
        print(f"Wrote research brief to {args.output} ({len(brief['qa'])} Q&A, {len(brief['sources'])} sources)")


async def research_to_social(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        if args.notebook:
            notebook_id = args.notebook
        else:
            notebook, _ = await _seed_notebook(client, args.topic or "Social research", args.sources or [])
            notebook_id = notebook.id

        questions = args.questions or [
            "What is the single most shareable or surprising fact from these sources?",
            "What is a common misconception these sources correct?",
        ]
        brief = await _research_brief(client, notebook_id, questions)
        brief["platform"] = args.platform
        brief["note"] = (
            "This is raw cited material, not finished posts. Ask Claude to write "
            f"{args.platform}-formatted posts from the findings above."
        )
        Path(args.output).write_text(json.dumps(brief, indent=2))
        print(f"Wrote research brief to {args.output} for platform={args.platform}")


async def batch_digest(args: argparse.Namespace) -> None:
    req = urllib.request.Request(args.rss, headers={"User-Agent": "notebooklm-research-skill/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 - user-supplied feed URL, by design
        root = ET.fromstring(resp.read())

    entries = []
    for item in root.iter("item"):  # RSS 2.0
        link = item.findtext("link")
        if link:
            entries.append(link.strip())
    if not entries:
        for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):  # Atom
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
            if link_el is not None and link_el.get("href"):
                entries.append(link_el.get("href"))
    entries = entries[: args.max_entries]
    if not entries:
        sys.exit(f"No entries found in feed: {args.rss}")

    async with require_client(args.profile) as client:
        notebook, source_ids = await _seed_notebook(client, args.title, entries)
        brief = await _research_brief(
            client, notebook.id,
            ["What are the main stories or developments covered across these sources this period?"],
        )
        markdown = _brief_to_markdown(args.title, brief)
        output = args.output or f"{args.title.lower().replace(' ', '_')}_digest.md"
        Path(output).write_text(markdown)
        print(f"Wrote digest brief to {output} ({len(entries)} feed entries ingested)")


async def trend_to_content(args: argparse.Namespace) -> None:
    """Research a pre-selected trending topic.

    Trend *discovery* (trend-pulse's get_trending) is an MCP tool only
    reachable from inside a Claude Code / Claude Desktop conversation — it
    cannot be called from a standalone script. This command does the second
    half: given a topic and either --sources or --trends-file (a JSON list of
    {"title", "url"} you already got from trend-pulse), build the research
    brief. Run the trend-pulse lookup in the same Claude conversation first.
    """
    sources = list(args.sources or [])
    if args.trends_file:
        data = json.loads(Path(args.trends_file).read_text())
        sources.extend(item["url"] for item in data if item.get("url"))
    if not sources:
        sys.exit(
            "No sources to research. Pass --sources, or --trends-file with URLs from "
            "a trend-pulse get_trending() call made earlier in this Claude conversation."
        )

    async with require_client(args.profile) as client:
        notebook, _ = await _seed_notebook(client, args.topic, sources)
        brief = await _research_brief(client, notebook.id, DEFAULT_QUESTIONS)
        brief["platform"] = args.platform
        output = args.output or "trend_brief.json"
        Path(output).write_text(json.dumps(brief, indent=2))
        print(f"Wrote trend research brief to {output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default=None)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("research-to-article", help="Sources -> cited research brief for an article")
    p.add_argument("--sources", nargs="*", default=[])
    p.add_argument("--text-sources", nargs="*", default=[])
    p.add_argument("--notebook", help="Use an existing notebook instead of creating one")
    p.add_argument("--title", required=True)
    p.add_argument("--questions", nargs="*", default=None)
    p.add_argument("--deep-research", default=None, help="Run deep web research with this query first")
    p.add_argument("--report", action="store_true", help="Also generate+include a NotebookLM briefing doc")
    p.add_argument("--output", required=True)
    p.set_defaults(func=research_to_article)

    p = sub.add_parser("research-to-social", help="Sources -> cited research brief for social posts")
    p.add_argument("--sources", nargs="*", default=[])
    p.add_argument("--notebook", help="Use an existing notebook instead of creating one")
    p.add_argument("--topic", default=None)
    p.add_argument("--questions", nargs="*", default=None)
    p.add_argument("--platform", default="threads", choices=["threads", "instagram", "facebook"])
    p.add_argument("--output", required=True)
    p.set_defaults(func=research_to_social)

    p = sub.add_parser("batch-digest", help="RSS/Atom feed -> cited digest brief")
    p.add_argument("--rss", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--max-entries", type=int, default=15)
    p.add_argument("--output", default=None)
    p.set_defaults(func=batch_digest)

    p = sub.add_parser(
        "trend-to-content",
        help="Pre-selected trending topic -> cited research brief (trend discovery is MCP-only, see --help)",
    )
    p.add_argument("--topic", required=True)
    p.add_argument("--sources", nargs="*", default=[])
    p.add_argument("--trends-file", default=None, help="JSON file of trend-pulse results (list of {title,url})")
    p.add_argument("--platform", default="threads")
    p.add_argument("--output", default=None)
    p.set_defaults(func=trend_to_content)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
