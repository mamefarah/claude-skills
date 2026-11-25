#!/usr/bin/env python3
"""FastMCP server for the notebooklm-research skill.

Exposes 13 tools (matching SKILL.md's MCP Server section) over the real
notebooklm-py client. Register with Claude Code / Cursor / Gemini CLI as:

    {
      "mcpServers": {
        "notebooklm-research": {
          "command": "python3",
          "args": ["/path/to/notebooklm-research/mcp_server/server.py"]
        }
      }
    }

Named "notebooklm-research" (not "notebooklm-mcp") deliberately: notebooklm-py
already installs its own general-purpose `notebooklm-mcp` console script, and
this server exists specifically for the higher-level pipeline tools
(nlm_research_pipeline, nlm_trend_research) this skill adds on top of it —
using the same name would collide and confuse the two.

Requires a stored login session (../docs/SETUP.md):
    pip install "notebooklm-py[browser]"
    notebooklm login
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tools  # noqa: E402
from auth_helper import require_client  # noqa: E402
from fastmcp import FastMCP  # noqa: E402

mcp = FastMCP("notebooklm-research")


@mcp.tool
async def nlm_create_notebook(title: str, sources: list[str] | None = None, text_sources: list[str] | None = None) -> dict:
    """Create a NotebookLM notebook and seed it with URL and/or text sources."""
    async with require_client() as client:
        return await tools.create_notebook(client, title, sources, text_sources)


@mcp.tool
async def nlm_list() -> list[dict]:
    """List all NotebookLM notebooks."""
    async with require_client() as client:
        return await tools.list_notebooks(client)


@mcp.tool
async def nlm_delete(notebook: str) -> dict:
    """Delete a notebook (irreversible). Accepts a notebook ID or exact title."""
    async with require_client() as client:
        return await tools.delete_notebook(client, notebook)


@mcp.tool
async def nlm_add_source(notebook: str, url: str | None = None, text: str | None = None, file_path: str | None = None) -> dict:
    """Add a source (URL, pasted text, or local file) to an existing notebook."""
    async with require_client() as client:
        return await tools.add_source(client, notebook, url=url, text=text, file_path=file_path)


@mcp.tool
async def nlm_ask(notebook: str, query: str) -> dict:
    """Ask a notebook a question and get a cited answer."""
    async with require_client() as client:
        return await tools.ask(client, notebook, query)


@mcp.tool
async def nlm_summarize(notebook: str) -> dict:
    """Get a comprehensive AI-generated summary of a notebook's sources."""
    async with require_client() as client:
        return await tools.summarize(client, notebook)


@mcp.tool
async def nlm_list_sources(notebook: str) -> list[dict]:
    """List all sources in a notebook."""
    async with require_client() as client:
        return await tools.list_sources(client, notebook)


@mcp.tool
async def nlm_generate(notebook: str, artifact_type: str, lang: str = "en", instructions: str | None = None) -> dict:
    """Generate a Studio artifact.

    artifact_type: one of audio, video, cinematic_video, report, study_guide,
    quiz, flashcards, mind_map, slide_deck, data_table. (infographic is
    excluded — its download is unreliable upstream; use slide_deck instead.)
    Blocks until generation completes.
    """
    async with require_client() as client:
        return await tools.generate(client, notebook, artifact_type, lang=lang, instructions=instructions)


@mcp.tool
async def nlm_download(notebook: str, artifact_type: str, output_path: str) -> dict:
    """Download the most recently generated artifact of a given type to a local file."""
    async with require_client() as client:
        return await tools.download(client, notebook, artifact_type, output_path)


@mcp.tool
async def nlm_list_artifacts(notebook: str, artifact_type: str | None = None) -> list[dict]:
    """List artifacts in a notebook, optionally filtered by type."""
    async with require_client() as client:
        return await tools.list_artifacts(client, notebook, artifact_type)


@mcp.tool
async def nlm_research(notebook: str, query: str, mode: str = "fast") -> dict:
    """Run web research to discover and import new sources into a notebook.

    mode: "fast" (10-30s, URL list) or "deep" (1-5min, full report + URLs).
    """
    async with require_client() as client:
        return await tools.research(client, notebook, query, mode=mode)


@mcp.tool
async def nlm_research_pipeline(sources: list[str], questions: list[str], title: str = "Research", output_format: str = "brief") -> dict:
    """Full pipeline: create a notebook from sources, ask research questions, return cited findings.

    output_format "report" also generates a NotebookLM briefing-doc artifact.
    Returns a research brief (questions, cited answers, notebook_id) — write the
    actual article/post copy yourself using this material, this tool does not
    generate prose.
    """
    async with require_client() as client:
        return await tools.research_pipeline(client, sources, questions, title=title, output_format=output_format)


@mcp.tool
async def nlm_trend_research(topic: str, source_urls: list[str], platform: str = "threads") -> dict:
    """Research a trending topic that was already discovered elsewhere.

    Trend *discovery* requires the separate trend-pulse MCP server's
    get_trending() tool — call that yourself first (this server cannot reach
    other MCP servers), then pass the resulting article URLs as source_urls.
    """
    async with require_client() as client:
        return await tools.trend_research(client, topic, source_urls, platform=platform)


def main() -> None:
    parser = argparse.ArgumentParser(description="notebooklm-research MCP server")
    parser.add_argument("--http", action="store_true", help="Serve over streamable HTTP instead of stdio")
    parser.add_argument("--port", type=int, default=8766, help="Port for --http mode")
    args = parser.parse_args()
    if args.http:
        mcp.run(transport="http", port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
