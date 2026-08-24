#!/usr/bin/env python3
"""Core wrapper CLI for the notebooklm-research skill.

A thin, scriptable layer over ``notebooklm-py``'s Python API (the installed
package's own ``notebooklm`` CLI does session/notebook/source/chat/sharing
management well, but has no way to *generate* or *download* Studio artifacts
from the command line — that only exists in the Python API. This script
fills that gap and gives every other operation a stable, JSON-friendly CLI
surface for scripting and for the MCP server in ../mcp_server/.)

Requires a stored login session (see ../docs/SETUP.md):
    pip install "notebooklm-py[browser]"
    notebooklm login

Examples:
    python3 notebooklm_client.py create --title "AI Agents" --sources https://a.com https://b.com
    python3 notebooklm_client.py ask --notebook NOTEBOOK_ID --query "What are the key findings?"
    python3 notebooklm_client.py generate --notebook NOTEBOOK_ID --type audio --format deep_dive --wait
    python3 notebooklm_client.py download --notebook NOTEBOOK_ID --type audio --output podcast.m4a
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import json
import sys
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from auth_helper import require_client  # noqa: E402

from notebooklm import (  # noqa: E402
    ArtifactType,
    AudioFormat,
    AudioLength,
    ChatMode,
    InfographicDetail,
    InfographicOrientation,
    InfographicStyle,
    QuizDifficulty,
    QuizQuantity,
    ReportFormat,
    SharePermission,
    SlideDeckFormat,
    SlideDeckLength,
    VideoFormat,
    VideoStyle,
)

# --------------------------------------------------------------------------
# Enum lookup tables (CLI string -> library enum). Values were introspected
# from the installed notebooklm-py; run `python3 -c "from notebooklm import
# types; print(list(types.AudioFormat))"` etc. to re-derive after an upgrade.
# --------------------------------------------------------------------------

AUDIO_FORMATS = {m.name.lower(): m for m in AudioFormat}
AUDIO_LENGTHS = {m.name.lower(): m for m in AudioLength}
VIDEO_FORMATS = {m.name.lower(): m for m in VideoFormat}
VIDEO_STYLES = {m.name.lower(): m for m in VideoStyle}
QUIZ_QUANTITIES = {m.name.lower(): m for m in QuizQuantity}
QUIZ_DIFFICULTIES = {m.name.lower(): m for m in QuizDifficulty}
SLIDE_FORMATS = {m.name.lower(): m for m in SlideDeckFormat}
SLIDE_LENGTHS = {m.name.lower(): m for m in SlideDeckLength}
INFOGRAPHIC_ORIENTATIONS = {m.name.lower(): m for m in InfographicOrientation}
INFOGRAPHIC_DETAILS = {m.name.lower(): m for m in InfographicDetail}
INFOGRAPHIC_STYLES = {m.name.lower(): m for m in InfographicStyle}
REPORT_FORMATS = {m.value: m for m in ReportFormat}
CHAT_MODES = {m.value: m for m in ChatMode}
SHARE_PERMISSIONS = {m.name.lower(): m for m in SharePermission if m.name != "_REMOVE"}

ARTIFACT_TYPES = [
    "audio", "video", "cinematic-video", "report", "study-guide",
    "quiz", "flashcards", "mind-map", "infographic", "slide-deck", "data-table",
]

# artifacts.list()/list(--type) uses the library's own ArtifactType enum
ARTIFACT_TYPE_FILTER = {
    "audio": ArtifactType.AUDIO,
    "video": ArtifactType.VIDEO,
    "report": ArtifactType.REPORT,
    "quiz": ArtifactType.QUIZ,
    "flashcards": ArtifactType.FLASHCARDS,
    "mind-map": ArtifactType.MIND_MAP,
    "infographic": ArtifactType.INFOGRAPHIC,
    "slide-deck": ArtifactType.SLIDE_DECK,
    "data-table": ArtifactType.DATA_TABLE,
}


# --------------------------------------------------------------------------
# Serialization helpers
# --------------------------------------------------------------------------

def _jsonable(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _jsonable(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    return obj


def _print(obj, as_json: bool) -> None:
    if as_json:
        print(json.dumps(_jsonable(obj), indent=2, default=str))
    else:
        print(obj)


def _die(message: str) -> None:
    sys.exit(f"Error: {message}")


# --------------------------------------------------------------------------
# Notebook commands
# --------------------------------------------------------------------------

async def cmd_create(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        notebook = await client.notebooks.create(args.title)
        added = []
        for url in args.sources or []:
            src = await client.sources.add_url(notebook.id, url)
            added.append(src.id)
        for i, text in enumerate(args.text_sources or []):
            title = f"Text source {i + 1}"
            src = await client.sources.add_text(notebook.id, title, text)
            added.append(src.id)
        if args.wait and added:
            await client.sources.wait_for_sources(notebook.id, added)
        _print(
            {"notebook_id": notebook.id, "title": notebook.title, "source_ids": added},
            args.json,
        )


async def cmd_list(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        notebooks = await client.notebooks.list()
        _print(notebooks, args.json)


async def cmd_delete(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        await client.notebooks.delete(args.notebook)
        _print({"deleted": args.notebook}, args.json)


async def cmd_rename(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        notebook = await client.notebooks.rename(args.notebook, args.title)
        _print(notebook, args.json)


async def cmd_describe(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        description = await client.notebooks.get_description(args.notebook)
        _print(description, args.json)


async def cmd_share(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        if args.public is not None:
            status = await client.sharing.set_public(args.notebook, args.public)
        elif args.add:
            permission = SHARE_PERMISSIONS[args.permission]
            status = await client.sharing.add_user(args.notebook, args.add, permission)
        elif args.remove:
            status = await client.sharing.remove_user(args.notebook, args.remove)
        else:
            status = await client.sharing.get_status(args.notebook)
        _print(status, args.json)


# --------------------------------------------------------------------------
# Source commands
# --------------------------------------------------------------------------

async def cmd_add_source(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        if args.url:
            src = await client.sources.add_url(args.notebook, args.url, wait=args.wait, title=args.title)
        elif args.text is not None:
            title = args.text_title or "Untitled text source"
            src = await client.sources.add_text(args.notebook, title, args.text, wait=args.wait)
        elif args.file:
            src = await client.sources.add_file(args.notebook, args.file, wait=args.wait, title=args.title)
        elif args.drive_id:
            src = await client.sources.add_drive(
                args.notebook, args.drive_id, args.drive_title or "Drive source", wait=args.wait
            )
        else:
            _die("one of --url, --text, --file, --drive-id is required")
        _print(src, args.json)


async def cmd_sources(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        sources = await client.sources.list(args.notebook)
        _print(sources, args.json)


async def cmd_source_guide(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        guide = await client.sources.get_guide(args.notebook, args.source)
        _print(guide, args.json)


async def cmd_fulltext(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        fulltext = await client.sources.get_fulltext(args.notebook, args.source, output_format=args.format)
        if args.json:
            _print(fulltext, True)
        else:
            print(fulltext.content)


# --------------------------------------------------------------------------
# Chat commands
# --------------------------------------------------------------------------

async def cmd_ask(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        if args.mode:
            await client.chat.set_mode(args.notebook, CHAT_MODES[args.mode])
        result = await client.chat.ask(
            args.notebook, args.query, source_ids=args.sources, conversation_id=args.conversation
        )
        _print(result, args.json)


async def cmd_summarize(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        summary = await client.notebooks.get_summary(args.notebook)
        _print({"notebook_id": args.notebook, "summary": summary}, args.json)


async def cmd_podcast(args: argparse.Namespace) -> None:
    """Convenience shortcut: generate audio --format deep_dive."""
    async with require_client(args.profile) as client:
        status = await client.artifacts.generate_audio(
            args.notebook, language=args.lang, audio_format=AUDIO_FORMATS["deep_dive"]
        )
        if args.wait:
            status = await client.artifacts.wait_for_completion(args.notebook, status.task_id)
        _print(status, args.json)


async def cmd_qa(args: argparse.Namespace) -> None:
    """Generate Q&A pairs: AI-suggested prompts, each answered with citations."""
    async with require_client(args.profile) as client:
        suggestions = await client.notebooks.suggest_prompts(args.notebook)
        pairs = []
        for suggestion in suggestions[: args.count]:
            question = getattr(suggestion, "text", None) or getattr(suggestion, "prompt", str(suggestion))
            result = await client.chat.ask(args.notebook, question)
            pairs.append({"question": question, "answer": result.answer})
        _print(pairs, args.json)


# --------------------------------------------------------------------------
# Artifact generation / download
# --------------------------------------------------------------------------

async def _generate(client, args: argparse.Namespace):
    kind = args.type
    source_ids = args.source_ids
    if kind == "audio":
        return await client.artifacts.generate_audio(
            args.notebook, source_ids=source_ids, language=args.language,
            instructions=args.instructions,
            audio_format=AUDIO_FORMATS[args.format] if args.format else None,
            audio_length=AUDIO_LENGTHS[args.length] if args.length else None,
        )
    if kind == "video":
        return await client.artifacts.generate_video(
            args.notebook, source_ids=source_ids, language=args.language,
            instructions=args.instructions,
            video_format=VIDEO_FORMATS[args.format] if args.format else None,
            video_style=VIDEO_STYLES[args.style] if args.style else None,
            style_prompt=args.style_prompt,
        )
    if kind == "cinematic-video":
        return await client.artifacts.generate_cinematic_video(
            args.notebook, source_ids=source_ids, language=args.language, instructions=args.instructions
        )
    if kind == "report":
        return await client.artifacts.generate_report(
            args.notebook,
            report_format=REPORT_FORMATS[args.format] if args.format else ReportFormat.BRIEFING_DOC,
            source_ids=source_ids, language=args.language,
            custom_prompt=args.custom_prompt, extra_instructions=args.instructions,
        )
    if kind == "study-guide":
        return await client.artifacts.generate_study_guide(
            args.notebook, source_ids=source_ids, language=args.language, extra_instructions=args.instructions
        )
    if kind == "quiz":
        return await client.artifacts.generate_quiz(
            args.notebook, source_ids=source_ids, instructions=args.instructions,
            quantity=QUIZ_QUANTITIES[args.quantity] if args.quantity else None,
            difficulty=QUIZ_DIFFICULTIES[args.difficulty] if args.difficulty else None,
        )
    if kind == "flashcards":
        return await client.artifacts.generate_flashcards(
            args.notebook, source_ids=source_ids, instructions=args.instructions,
            quantity=QUIZ_QUANTITIES[args.quantity] if args.quantity else None,
            difficulty=QUIZ_DIFFICULTIES[args.difficulty] if args.difficulty else None,
        )
    if kind == "mind-map":
        return await client.artifacts.generate_mind_map(
            args.notebook, source_ids=source_ids, language=args.language, instructions=args.instructions
        )
    if kind == "infographic":
        print(
            "Warning: infographic download is unreliable upstream (fragile API "
            "structure parsing). Prefer --type slide-deck for downloadable visuals.",
            file=sys.stderr,
        )
        return await client.artifacts.generate_infographic(
            args.notebook, source_ids=source_ids, language=args.language, instructions=args.instructions,
            orientation=INFOGRAPHIC_ORIENTATIONS[args.orientation] if args.orientation else None,
            detail_level=INFOGRAPHIC_DETAILS[args.detail] if args.detail else None,
            style=INFOGRAPHIC_STYLES[args.style] if args.style else None,
        )
    if kind == "data-table":
        return await client.artifacts.generate_data_table(
            args.notebook, source_ids=source_ids, language=args.language, instructions=args.instructions
        )
    if kind == "slide-deck":
        return await client.artifacts.generate_slide_deck(
            args.notebook, source_ids=source_ids, language=args.language, instructions=args.instructions,
            slide_format=SLIDE_FORMATS[args.format] if args.format else None,
            slide_length=SLIDE_LENGTHS[args.length] if args.length else None,
        )
    _die(f"unknown artifact type: {kind}")


async def cmd_generate(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        status = await _generate(client, args)
        if args.wait:
            task_id = getattr(status, "task_id", None)
            if task_id:
                status = await client.artifacts.wait_for_completion(args.notebook, task_id)
        _print(status, args.json)


async def cmd_list_artifacts(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        artifact_type = ARTIFACT_TYPE_FILTER.get(args.type) if args.type else None
        artifacts = await client.artifacts.list(args.notebook, artifact_type=artifact_type)
        _print(artifacts, args.json)


_DOWNLOAD_METHODS = {
    "audio": ("download_audio", {}),
    "video": ("download_video", {}),
    "report": ("download_report", {}),
    "quiz": ("download_quiz", {"output_format": "format"}),
    "flashcards": ("download_flashcards", {"output_format": "format"}),
    "mind-map": ("download_mind_map", {}),
    "slide-deck": ("download_slide_deck", {"output_format": "format"}),
    "data-table": ("download_data_table", {}),
    "infographic": ("download_infographic", {}),
}


async def cmd_download(args: argparse.Namespace) -> None:
    if args.type not in _DOWNLOAD_METHODS:
        _die(f"unknown artifact type: {args.type} (choices: {sorted(_DOWNLOAD_METHODS)})")
    if args.type == "infographic":
        print(
            "Warning: infographic download is unreliable upstream. "
            "If this fails, regenerate the content as --type slide-deck instead.",
            file=sys.stderr,
        )
    method_name, extra_arg_map = _DOWNLOAD_METHODS[args.type]
    async with require_client(args.profile) as client:
        method = getattr(client.artifacts, method_name)
        kwargs = {}
        for kw, attr in extra_arg_map.items():
            value = getattr(args, attr, None)
            if value:
                kwargs[kw] = value
        path = await method(args.notebook, args.output, args.artifact, **kwargs)
        _print({"downloaded_to": path}, args.json)


# --------------------------------------------------------------------------
# Research
# --------------------------------------------------------------------------

async def cmd_research(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        start = await client.research.start(args.notebook, args.query, source=args.source, mode=args.mode)
        _print(start, args.json)


async def cmd_research_poll(args: argparse.Namespace) -> None:
    async with require_client(args.profile) as client:
        task = await client.research.poll(args.notebook, args.task)
        imported = []
        if args.import_top and task.sources:
            imported = await client.research.import_sources(
                args.notebook, task.task_id, list(task.sources[: args.import_top])
            )
        _print({"task": _jsonable(task), "imported": imported}, args.json)


# --------------------------------------------------------------------------
# Parser
# --------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", default=None, help="notebooklm CLI profile to use (default: active profile)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create", help="Create a notebook, optionally seeded with sources")
    p.add_argument("--title", required=True)
    p.add_argument("--sources", nargs="*", default=[], help="URLs to add as sources")
    p.add_argument("--text-sources", nargs="*", default=[], help="Raw text blocks to add as sources")
    p.add_argument("--wait", action="store_true", help="Block until all added sources finish processing")
    p.set_defaults(func=cmd_create)

    p = sub.add_parser("list", help="List all notebooks")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("delete", help="Delete a notebook")
    p.add_argument("--notebook", required=True)
    p.set_defaults(func=cmd_delete)

    p = sub.add_parser("rename", help="Rename a notebook")
    p.add_argument("--notebook", required=True)
    p.add_argument("--title", required=True)
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("describe", help="Get AI-generated summary and suggested topics")
    p.add_argument("--notebook", required=True)
    p.set_defaults(func=cmd_describe)

    p = sub.add_parser("share", help="Manage notebook sharing")
    p.add_argument("--notebook", required=True)
    p.add_argument("--public", dest="public", action="store_const", const=True, default=None)
    p.add_argument("--private", dest="public", action="store_const", const=False)
    p.add_argument("--add", metavar="EMAIL", help="Grant an email access")
    p.add_argument("--remove", metavar="EMAIL", help="Revoke an email's access")
    p.add_argument("--permission", choices=sorted(SHARE_PERMISSIONS), default="viewer")
    p.set_defaults(func=cmd_share)

    p = sub.add_parser("add-source", help="Add a source to a notebook")
    p.add_argument("--notebook", required=True)
    p.add_argument("--url")
    p.add_argument("--text")
    p.add_argument("--text-title")
    p.add_argument("--file")
    p.add_argument("--drive-id")
    p.add_argument("--drive-title")
    p.add_argument("--title", help="Custom title (url/file sources)")
    p.add_argument("--wait", action="store_true", help="Block until the source finishes processing")
    p.set_defaults(func=cmd_add_source)

    p = sub.add_parser("sources", help="List sources in a notebook")
    p.add_argument("--notebook", required=True)
    p.set_defaults(func=cmd_sources)

    p = sub.add_parser("source-guide", help="Get AI summary + keywords for a source")
    p.add_argument("--notebook", required=True)
    p.add_argument("--source", required=True)
    p.set_defaults(func=cmd_source_guide)

    p = sub.add_parser("fulltext", help="Get the full indexed text of a source")
    p.add_argument("--notebook", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--format", choices=["text", "markdown"], default="text")
    p.set_defaults(func=cmd_fulltext)

    p = sub.add_parser("ask", help="Ask a notebook a question, get a cited answer")
    p.add_argument("--notebook", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--sources", nargs="*", default=None, help="Restrict to these source IDs")
    p.add_argument("--conversation", help="Existing conversation ID for a follow-up")
    p.add_argument("--mode", choices=sorted(CHAT_MODES), default=None, help="Set chat persona before asking")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("summarize", help="Get a comprehensive notebook summary")
    p.add_argument("--notebook", required=True)
    p.set_defaults(func=cmd_summarize)

    p = sub.add_parser("podcast", help="Shortcut: generate a deep-dive audio overview")
    p.add_argument("--notebook", required=True)
    p.add_argument("--lang", default="en")
    p.add_argument("--wait", action="store_true")
    p.set_defaults(func=cmd_podcast)

    p = sub.add_parser("qa", help="Generate Q&A pairs from AI-suggested prompts")
    p.add_argument("--notebook", required=True)
    p.add_argument("--count", type=int, default=5)
    p.set_defaults(func=cmd_qa)

    p = sub.add_parser("generate", help="Generate a Studio artifact")
    p.add_argument("--notebook", required=True)
    p.add_argument("--type", required=True, choices=ARTIFACT_TYPES)
    p.add_argument("--source-ids", nargs="*", default=None)
    p.add_argument("--language", default="en")
    p.add_argument("--instructions", help="Extra instructions / focus guidance")
    p.add_argument("--format", help="audio: deep_dive|brief|critique|debate; video: explainer|brief|cinematic|short; report: briefing_doc|study_guide|blog_post|concept_explanation|custom; slide-deck: detailed_deck|presenter_slides")
    p.add_argument("--length", help="audio: short|default|long; slide-deck: default|short")
    p.add_argument("--style", help="video: auto_select|classic|whiteboard|kawaii|anime|watercolor|retro_print|heritage|paper_craft; infographic: auto_select|sketch_note|professional|bento_grid|editorial|instructional|bricks|clay|anime|kawaii|scientific")
    p.add_argument("--style-prompt", help="video: freeform style description (pairs with --style custom)")
    p.add_argument("--quantity", choices=sorted(QUIZ_QUANTITIES), help="quiz/flashcards: fewer|standard|more")
    p.add_argument("--difficulty", choices=sorted(QUIZ_DIFFICULTIES), help="quiz/flashcards: easy|medium|hard")
    p.add_argument("--orientation", choices=sorted(INFOGRAPHIC_ORIENTATIONS), help="infographic: landscape|portrait|square")
    p.add_argument("--detail", choices=sorted(INFOGRAPHIC_DETAILS), help="infographic: concise|standard|detailed")
    p.add_argument("--custom-prompt", help="report --format custom: the custom prompt text")
    p.add_argument("--wait", action="store_true", help="Block until generation completes")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("list-artifacts", help="List artifacts in a notebook")
    p.add_argument("--notebook", required=True)
    p.add_argument("--type", choices=sorted(ARTIFACT_TYPE_FILTER), default=None)
    p.set_defaults(func=cmd_list_artifacts)

    p = sub.add_parser("download", help="Download a generated artifact")
    p.add_argument("--notebook", required=True)
    p.add_argument("--type", required=True, choices=sorted(_DOWNLOAD_METHODS))
    p.add_argument("--output", required=True, help="Output file path")
    p.add_argument("--artifact", default=None, help="Specific artifact ID (default: most recent of --type)")
    p.add_argument("--format", default=None, help="quiz/flashcards: json (default); slide-deck: pdf (default)")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("research", help="Start web or Drive research to discover new sources")
    p.add_argument("--notebook", required=True)
    p.add_argument("--query", required=True)
    p.add_argument("--source", choices=["web", "drive"], default="web")
    p.add_argument("--mode", choices=["fast", "deep"], default="fast")
    p.set_defaults(func=cmd_research)

    p = sub.add_parser("research-poll", help="Poll a research task and optionally import top sources")
    p.add_argument("--notebook", required=True)
    p.add_argument("--task", default=None, help="Task ID (default: most recent research task)")
    p.add_argument("--import-top", type=int, default=0, help="Import this many top discovered sources")
    p.set_defaults(func=cmd_research_poll)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(args.func(args))


if __name__ == "__main__":
    main()
