"""Tool implementations for the notebooklm-research MCP server.

Kept separate from server.py so the FastMCP wiring (server.py) stays a thin
registration layer and the actual logic here can be unit-tested without
spinning up an MCP transport. Every function takes an already-open
``NotebookLMClient`` as its first argument; server.py owns opening/closing
the client per call via ``auth_helper.require_client``.
"""

from __future__ import annotations

import dataclasses
import sys
from enum import Enum
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from notebooklm_client import (  # noqa: E402
    _DOWNLOAD_METHODS,
    ARTIFACT_TYPE_FILTER,
)

from notebooklm import ReportFormat  # noqa: E402


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


async def resolve_notebook(client, notebook: str) -> str:
    """Resolve a notebook ID, ID prefix, or exact title to a real notebook ID."""
    notebooks = await client.notebooks.list()
    for nb in notebooks:
        if nb.id == notebook:
            return nb.id
    matches = [nb for nb in notebooks if nb.id.startswith(notebook)]
    if len(matches) == 1:
        return matches[0].id
    title_matches = [nb for nb in notebooks if nb.title.lower() == notebook.lower()]
    if len(title_matches) == 1:
        return title_matches[0].id
    if len(matches) > 1 or len(title_matches) > 1:
        raise ValueError(f"'{notebook}' matches multiple notebooks; use the full ID")
    raise ValueError(f"No notebook found matching ID or title '{notebook}'")


# --------------------------------------------------------------------------
# Core notebook operations
# --------------------------------------------------------------------------

async def create_notebook(client, title: str, sources: list[str] | None = None, text_sources: list[str] | None = None) -> dict:
    notebook = await client.notebooks.create(title)
    added = []
    for url in sources or []:
        src = await client.sources.add_url(notebook.id, url)
        added.append(src.id)
    for i, text in enumerate(text_sources or []):
        src = await client.sources.add_text(notebook.id, f"Text source {i + 1}", text)
        added.append(src.id)
    if added:
        await client.sources.wait_for_sources(notebook.id, added)
    return {"notebook_id": notebook.id, "title": notebook.title, "source_ids": added}


async def list_notebooks(client) -> list[dict]:
    notebooks = await client.notebooks.list()
    return [_jsonable(nb) for nb in notebooks]


async def delete_notebook(client, notebook: str) -> dict:
    notebook_id = await resolve_notebook(client, notebook)
    await client.notebooks.delete(notebook_id)
    return {"deleted": notebook_id}


async def add_source(
    client, notebook: str, url: str | None = None, text: str | None = None, file_path: str | None = None
) -> dict:
    notebook_id = await resolve_notebook(client, notebook)
    if url:
        src = await client.sources.add_url(notebook_id, url, wait=True)
    elif text is not None:
        src = await client.sources.add_text(notebook_id, "Text source", text, wait=True)
    elif file_path:
        src = await client.sources.add_file(notebook_id, file_path, wait=True)
    else:
        raise ValueError("one of url, text, file_path is required")
    return _jsonable(src)


async def ask(client, notebook: str, query: str) -> dict:
    notebook_id = await resolve_notebook(client, notebook)
    result = await client.chat.ask(notebook_id, query)
    return {"answer": result.answer, "conversation_id": result.conversation_id, "references": _jsonable(result.references)}


async def summarize(client, notebook: str) -> dict:
    notebook_id = await resolve_notebook(client, notebook)
    summary = await client.notebooks.get_summary(notebook_id)
    return {"notebook_id": notebook_id, "summary": summary}


async def list_sources(client, notebook: str) -> list[dict]:
    notebook_id = await resolve_notebook(client, notebook)
    sources = await client.sources.list(notebook_id)
    return [_jsonable(s) for s in sources]


# --------------------------------------------------------------------------
# Artifact operations
# --------------------------------------------------------------------------

_GENERATORS = {
    "audio": lambda c, nb, lang, instr: c.artifacts.generate_audio(nb, language=lang, instructions=instr),
    "video": lambda c, nb, lang, instr: c.artifacts.generate_video(nb, language=lang, instructions=instr),
    "cinematic_video": lambda c, nb, lang, instr: c.artifacts.generate_cinematic_video(nb, language=lang, instructions=instr),
    "report": lambda c, nb, lang, instr: c.artifacts.generate_report(
        nb, report_format=ReportFormat.BRIEFING_DOC, language=lang, extra_instructions=instr,
    ),
    "study_guide": lambda c, nb, lang, instr: c.artifacts.generate_study_guide(nb, language=lang, extra_instructions=instr),
    "quiz": lambda c, nb, lang, instr: c.artifacts.generate_quiz(nb, instructions=instr),
    "flashcards": lambda c, nb, lang, instr: c.artifacts.generate_flashcards(nb, instructions=instr),
    "mind_map": lambda c, nb, lang, instr: c.artifacts.generate_mind_map(nb, language=lang, instructions=instr),
    "infographic": lambda c, nb, lang, instr: c.artifacts.generate_infographic(nb, language=lang, instructions=instr),
    "slide_deck": lambda c, nb, lang, instr: c.artifacts.generate_slide_deck(nb, language=lang, instructions=instr),
    "data_table": lambda c, nb, lang, instr: c.artifacts.generate_data_table(nb, language=lang, instructions=instr),
}


async def generate(client, notebook: str, artifact_type: str, lang: str = "en", instructions: str | None = None, wait: bool = True) -> dict:
    if artifact_type not in _GENERATORS:
        raise ValueError(f"Unknown artifact type '{artifact_type}'. Choices: {sorted(_GENERATORS)}")
    if artifact_type == "infographic":
        raise ValueError(
            "infographic generation/download is unreliable upstream (fragile API structure "
            "parsing). Use artifact_type='slide_deck' for downloadable visual content instead."
        )
    notebook_id = await resolve_notebook(client, notebook)
    status = await _GENERATORS[artifact_type](client, notebook_id, lang, instructions)
    if wait:
        task_id = getattr(status, "task_id", None)
        if task_id:
            status = await client.artifacts.wait_for_completion(notebook_id, task_id)
    return _jsonable(status)


_DOWNLOAD_TYPE_ALIASES = {"slide_deck": "slide-deck", "data_table": "data-table", "mind_map": "mind-map"}


async def download(client, notebook: str, artifact_type: str, output_path: str) -> dict:
    key = _DOWNLOAD_TYPE_ALIASES.get(artifact_type, artifact_type)
    if key not in _DOWNLOAD_METHODS:
        raise ValueError(f"Unknown artifact type '{artifact_type}'. Choices: {sorted(_DOWNLOAD_METHODS)}")
    notebook_id = await resolve_notebook(client, notebook)
    method_name, _ = _DOWNLOAD_METHODS[key]
    method = getattr(client.artifacts, method_name)
    path = await method(notebook_id, output_path)
    return {"downloaded_to": path}


async def list_artifacts(client, notebook: str, artifact_type: str | None = None) -> list[dict]:
    notebook_id = await resolve_notebook(client, notebook)
    filt = ARTIFACT_TYPE_FILTER.get(artifact_type.replace("_", "-")) if artifact_type else None
    artifacts = await client.artifacts.list(notebook_id, artifact_type=filt)
    return [_jsonable(a) for a in artifacts]


# --------------------------------------------------------------------------
# Research operations
# --------------------------------------------------------------------------

async def research(client, notebook: str, query: str, mode: str = "fast", import_top: int = 5) -> dict:
    notebook_id = await resolve_notebook(client, notebook)
    start = await client.research.start(notebook_id, query, source="web", mode=mode)
    task = await client.research.wait_for_completion(notebook_id, start.task_id)
    imported = []
    if task.sources and import_top:
        imported = await client.research.import_sources(notebook_id, task.task_id, list(task.sources[:import_top]))
    return {"task_id": task.task_id, "summary": task.summary, "sources": _jsonable(task.sources), "imported": imported}


# --------------------------------------------------------------------------
# Pipeline operations
# --------------------------------------------------------------------------

async def research_pipeline(client, sources: list[str], questions: list[str], title: str = "Research", output_format: str = "brief") -> dict:
    notebook = await client.notebooks.create(title)
    added = []
    for url in sources:
        src = await client.sources.add_url(notebook.id, url)
        added.append(src.id)
    if added:
        await client.sources.wait_for_sources(notebook.id, added)

    qa = []
    for question in questions:
        result = await client.chat.ask(notebook.id, question)
        qa.append({"question": question, "answer": result.answer, "references": _jsonable(result.references)})

    payload = {"notebook_id": notebook.id, "title": title, "qa": qa}
    if output_format == "report":
        status = await client.artifacts.generate_report(notebook.id, report_format=ReportFormat.BRIEFING_DOC)
        status = await client.artifacts.wait_for_completion(notebook.id, status.task_id)
        payload["report_artifact"] = _jsonable(status)
    return payload


async def trend_research(client, topic: str, source_urls: list[str], platform: str = "threads") -> dict:
    """Research a topic already identified as trending.

    Trend *discovery* is a separate MCP server (trend-pulse); this server has
    no way to call it directly. Callers (Claude) must run trend-pulse's
    get_trending() themselves first and pass the resulting article URLs in
    as ``source_urls``. This tool only does the NotebookLM research half.
    """
    if not source_urls:
        raise ValueError(
            "source_urls is empty. Call trend-pulse's get_trending() in this same "
            "conversation first, then pass the discovered article URLs here."
        )
    return await research_pipeline(
        client, source_urls,
        [
            "What is this trend about, and why is it significant right now?",
            "What are the different perspectives or angles being taken on this?",
        ],
        title=topic,
    ) | {"platform": platform}
