# Output formats

What each script/tool in this skill actually returns, field by field. All
dataclass responses are converted to plain dicts via the `_jsonable()` helper
in `scripts/notebooklm_client.py` / `mcp_server/tools.py` (dataclasses →
dict, enums → their `.value`) before being printed as JSON or handed back
from an MCP tool.

## `Notebook` (create, list, rename)

```json
{
  "id": "abc123...",
  "title": "AI Agents Research",
  "created_at": "2026-01-01T00:00:00Z",
  "sources_count": 3,
  "is_owner": true,
  "modified_at": "...",
  "role": "...",
  "last_viewed_at": "...",
  "emoji": null,
  "premium_features": [...],
  "chat_sessions": [...],
  "chat_settings": {...}
}
```

`notebooklm_client.py create` additionally returns `source_ids: [...]` for
whatever sources you seeded it with.

## `Source` (add-source, sources)

```json
{
  "id": "src_...",
  "title": "Example Article",
  "url": "https://example.com/article",
  "created_at": "...",
  "status": 2,
  "drive_document_id": null,
  "drive_status": null,
  "download_url": null,
  "viewer_url": "...",
  "content_mime": "text/html",
  "word_count": 1834,
  "revision_id": "...",
  "revision_timestamp": "...",
  "last_modified_at": "..."
}
```

`status`: `1`=processing, `2`=ready, `3`=error, `4`=preparing.

## `SourceGuide` (source-guide)

```json
{"summary": "...", "keywords": ["agent", "framework", "..."]}
```

## `SourceFulltext` (fulltext)

```json
{"source_id": "src_...", "title": "...", "content": "full text or markdown...", "url": "...", "char_count": 12345}
```
`notebooklm_client.py fulltext` (without `--json`) prints just `content`.

## `AskResult` (ask)

```json
{
  "answer": "The key differences are...",
  "conversation_id": "conv_...",
  "turn_number": 1,
  "is_follow_up": false,
  "references": [
    {
      "source_id": "src_...",
      "citation_number": 1,
      "cited_text": "the exact passage quoted",
      "start_char": 120,
      "end_char": 340
    }
  ],
  "next_steps": [...]
}
```
Every citation number in `answer` corresponds to an entry in `references`
with the same `citation_number` — pull `source_id` + `cited_text` from there
to build a proper citation list.

## `GenerationStatus` (generate, before/after `--wait`)

```json
{
  "task_id": "task_...",
  "status": "completed",
  "url": "https://notebooklm.google.com/...",
  "error": null,
  "error_code": null,
  "metadata": {...}
}
```
`status` is one of: `pending`, `in_progress`, `completed`, `failed`,
`not_found`, `unknown`, `suggested`, `pending_review`, `removed`. Only act on
the download once `status == "completed"`.

## `Artifact` (list-artifacts)

```json
{
  "id": "art_...",
  "title": "Deep Dive: AI Agents",
  "status": "completed",
  "created_at": "...",
  "url": "...",
  "generation_prompt": "...",
  "media_urls": ["..."],
  "duration_seconds": 842,
  "slides": null,
  "infographics": null,
  "report_kind": null,
  "source_ids": ["src_...", "..."]
}
```

## Downloaded file formats

| `--type` | File extension | Format |
|---|---|---|
| `audio` | `.m4a` | Audio (AAC) |
| `video` | `.mp4` | Video |
| `report` (incl. study-guide) | `.md` | Markdown text |
| `quiz` | `.json` (default) | `{"questions": [{"question", "options", "answer", ...}]}` |
| `flashcards` | `.json` (default) | `{"cards": [{"front", "back"}]}` |
| `mind-map` | `.json` | Tree: `{"name": "...", "children": [...]}` |
| `slide-deck` | `.pdf` (default) | Rendered slide deck |
| `data-table` | `.csv` (default; pass `--format json` for structured) | Comparison table |
| `infographic` | image | ⚠️ Download is unreliable upstream — expect occasional `ArtifactParseError`; prefer `slide-deck` |

## `ResearchStart` (research)

```json
{"task_id": "rt_...", "report_id": "...", "notebook_id": "...", "query": "...", "mode": "deep"}
```

## `ResearchTask` (research-poll)

```json
{
  "task_id": "rt_...",
  "status": "completed",
  "query": "...",
  "sources": [{"url": "https://...", "title": "...", "result_type": "web", "..." : "..."}],
  "summary": "...",
  "report": "full markdown research report (deep mode only)"
}
```
`notebooklm_client.py research-poll --import-top N` additionally returns
`imported: [{"id": "src_...", "title": "..."}]` for whichever sources were
actually pulled into the notebook.

## `ShareStatus` (share)

```json
{
  "notebook_id": "...",
  "is_public": false,
  "access": "...",
  "view_level": 0,
  "shared_users": [{"email": "...", "permission": 3}],
  "share_url": "https://notebooklm.google.com/notebook/.../share",
  "max_individuals_share_limit": 50,
  "is_public_sharing_allowed": true
}
```

## Research briefs (`scripts/pipeline.py`)

`research-to-article` writes **Markdown**:

```
# Research brief: <title>

_NotebookLM notebook: <id>_

## Sources
- Title — https://...

## Cited findings
**Q: <question>**

<cited answer text>

---
_This is a research brief, not a finished draft. Ask Claude ... to write the article._
```

`research-to-social`, `trend-to-content`, and `batch-digest`'s underlying
brief write the same content as **JSON**:

```json
{
  "notebook_id": "...",
  "qa": [{"question": "...", "answer": "...", "references": [...]}],
  "discovered_sources": [...],
  "report": null,
  "sources": [{"id": "...", "title": "...", "url": "..."}],
  "platform": "threads",
  "note": "This is raw cited material, not finished posts. Ask Claude to write ..."
}
```

These are deliberately **not** finished articles/posts — see the docstring
at the top of `pipeline.py` for why (NotebookLM does research, Claude does
writing; a script templating strings together would just be worse prose).
