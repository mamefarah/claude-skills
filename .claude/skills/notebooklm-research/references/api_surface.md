# notebooklm-py API surface (as installed)

This reference is generated from `pip install notebooklm` (PyPI distribution
`notebooklm-py`), inspected directly with `inspect.signature()` against the
version actually installed — not copied from upstream docs, which can drift.
Re-run the snippet at the bottom of this file after any upgrade to refresh it.

**Installed version at time of writing: notebooklm-py 0.8.1** (import name is
still `notebooklm`, i.e. `from notebooklm import NotebookLMClient`).
SKILL.md's examples were originally written against an older 0.3.x line; the
entry point (`NotebookLMClient.from_storage()` → 8 sub-APIs on `client.*`)
is unchanged, but several enum member names and CLI subcommands differ from
what SKILL.md's prose describes — this file and `scripts/notebooklm_client.py`
reflect the real, currently-installed API.

## Entry point

```python
from notebooklm import NotebookLMClient

async with NotebookLMClient.from_storage(profile=None) as client:
    ...
```

Do **not** `await` `from_storage()` before the `async with` — that form is
deprecated in 0.8.1 (it still works but prints a `DeprecationWarning`; use
`async with NotebookLMClient.from_storage(...) as client:` directly).

`from_storage()` resolves the session path itself (per-profile, under
`~/.notebooklm/profiles/<profile>/storage_state.json`), so scripts never need
to hardcode a storage path.

## Sub-APIs

| Accessor | Class | Purpose |
|---|---|---|
| `client.notebooks` | `NotebooksAPI` | create/list/get/delete/rename/describe/summary/share URL |
| `client.sources` | `SourcesAPI` | add (url/text/file/drive), list, delete, rename, refresh, guide, fulltext, wait |
| `client.chat` | `ChatAPI` | ask, configure persona, history, save answer as note |
| `client.artifacts` | `ArtifactsAPI` | generate (9 types), poll/wait, download, list, delete, rename, revise slide |
| `client.research` | `ResearchAPI` | start/poll/wait_for_completion, import_sources |
| `client.notes` | `NotesAPI` | create/get/list/update/delete notes and mind maps |
| `client.settings` | `SettingsAPI` | account limits, output language |
| `client.sharing` | `SharingAPI` | public link, per-user permissions, view level |
| `client.labels` | `LabelsAPI` | source labels (not wrapped by this skill's scripts) |
| `client.collections` | `CollectionsAPI` | notebook collections (not wrapped by this skill's scripts) |

### `client.notebooks`

```
create(title: str) -> Notebook
list() -> list[Notebook]
get(notebook_id: str) -> Notebook
get_or_none(notebook_id: str) -> Notebook | None
delete(notebook_id: str) -> None
rename(notebook_id: str, new_title: str) -> Notebook
get_summary(notebook_id: str) -> str
get_description(notebook_id: str) -> NotebookDescription   # .summary, .suggested_topics
get_metadata(notebook_id: str) -> NotebookMetadata
get_source_ids(notebook_id: str) -> list[str]
get_share_url(notebook_id: str, artifact_id: str | None = None) -> str
suggest_prompts(notebook_id: str, *, source_ids=None, mode=4, query=None) -> list[PromptSuggestion]
set_emoji(notebook_id: str, emoji: str) -> Notebook
```

### `client.sources`

```
add_url(notebook_id, url, *, wait=False, wait_timeout=120.0, title=None) -> Source
add_text(notebook_id, title, content, *, wait=False, wait_timeout=120.0) -> Source
add_file(notebook_id, file_path, mime_type=None, *, wait=False, wait_timeout=120.0, title=None) -> Source
add_drive(notebook_id, file_id, title, mime_type="application/vnd.google-apps.document", *, wait=False) -> Source
list(notebook_id, *, strict=False, statuses=None, types=None) -> list[Source]
get(notebook_id, source_id) -> Source
delete(notebook_id, source_id) -> None
rename(notebook_id, source_id, new_title) -> Source | None
get_guide(notebook_id, source_id) -> SourceGuide       # .summary, .keywords
get_fulltext(notebook_id, source_id, *, output_format="text"|"markdown") -> SourceFulltext
refresh(notebook_id, source_id) -> None
wait_for_sources(notebook_id, source_ids: list[str], timeout=120.0) -> list[Source]
wait_until_ready(notebook_id, source_id, timeout=120.0) -> Source
```

Source status codes (`Source.status` / `SourceStatus`): `1=processing`,
`2=ready`, `3=error`, `4=preparing`.

### `client.chat`

```
ask(notebook_id, question, source_ids=None, conversation_id=None) -> AskResult
configure(notebook_id, goal: ChatGoal=None, response_length: ChatResponseLength=None, custom_prompt=None) -> None
set_mode(notebook_id, mode: ChatMode) -> None
get_history(notebook_id, limit=100, conversation_id=None) -> list[tuple[str, str]]
save_answer_as_note(notebook_id, ask_result: AskResult, *, title=None) -> Note
```

`AskResult` fields: `answer`, `conversation_id`, `turn_number`, `is_follow_up`,
`references` (list of `ChatReference`: `source_id`, `citation_number`,
`cited_text`, ...), `next_steps`.

`ChatMode` values: `default`, `learning_guide`, `concise`, `detailed`.

### `client.artifacts` — the 9 (10 minus infographic) generatable types

```
generate_audio(notebook_id, source_ids=None, language="en", instructions=None,
                audio_format: AudioFormat=None, audio_length: AudioLength=None) -> GenerationStatus
generate_video(notebook_id, ..., video_format: VideoFormat=None, video_style: VideoStyle=None,
                style_prompt=None) -> GenerationStatus
generate_cinematic_video(notebook_id, source_ids=None, language="en", instructions=None) -> GenerationStatus
generate_report(notebook_id, report_format: ReportFormat=BRIEFING_DOC, source_ids=None,
                 language="en", custom_prompt=None, extra_instructions=None) -> GenerationStatus
generate_study_guide(notebook_id, source_ids=None, language="en", extra_instructions=None) -> GenerationStatus
generate_quiz(notebook_id, source_ids=None, instructions=None,
              quantity: QuizQuantity=None, difficulty: QuizDifficulty=None) -> GenerationStatus
generate_flashcards(notebook_id, ..., quantity, difficulty) -> GenerationStatus
generate_mind_map(notebook_id, source_ids=None, language="en", instructions=None) -> MindMapResult
generate_infographic(notebook_id, ..., orientation, detail_level, style) -> GenerationStatus  # ⚠️ download unreliable
generate_slide_deck(notebook_id, ..., slide_format: SlideDeckFormat=None, slide_length: SlideDeckLength=None) -> GenerationStatus
generate_data_table(notebook_id, source_ids=None, language="en", instructions=None) -> GenerationStatus

poll_status(notebook_id, task_id) -> GenerationStatus
wait_for_completion(notebook_id, task_id, timeout=300.0, on_status_change=None) -> GenerationStatus
list(notebook_id, artifact_type: ArtifactType=None) -> list[Artifact]
get(notebook_id, artifact_id) -> Artifact
rename(notebook_id, artifact_id, new_title) -> Artifact | None
delete(notebook_id, artifact_id) -> None
retry_failed(notebook_id, artifact_id) -> GenerationStatus
revise_slide(notebook_id, artifact_id, slide_index, prompt) -> GenerationStatus

download_audio(notebook_id, output_path, artifact_id=None) -> str
download_video(notebook_id, output_path, artifact_id=None) -> str
download_report(notebook_id, output_path, artifact_id=None) -> str
download_quiz(notebook_id, output_path, artifact_id=None, output_format="json") -> str
download_flashcards(notebook_id, output_path, artifact_id=None, output_format="json") -> str
download_mind_map(notebook_id, output_path, artifact_id=None) -> str
download_slide_deck(notebook_id, output_path, artifact_id=None, output_format="pdf") -> str
download_data_table(notebook_id, output_path, artifact_id=None) -> str
download_infographic(notebook_id, output_path, artifact_id=None) -> str   # ⚠️ unreliable
```

`artifact_id=None` auto-selects the most recently generated artifact of that
type — you don't need to look up the ID for the common case.

`GenerationStatus.status` is a `GenerationState` enum: `pending`,
`in_progress`, `completed`, `failed`, `not_found`, `unknown`, `suggested`,
`pending_review`, `removed`.

**Important:** the *installed* `notebooklm` CLI's `artifact` command group only
covers list/get/rename/delete/export/poll/wait/retry/suggestions — there is
**no built-in `notebooklm generate` or `notebooklm download` CLI command**.
Generation and download only exist in the Python API, which is exactly why
`scripts/notebooklm_client.py` exists.

### `client.research`

```
start(notebook_id, query, source="web"|"drive", mode="fast"|"deep") -> ResearchStart
poll(notebook_id, task_id=None) -> ResearchTask
wait_for_completion(notebook_id, task_id=None, timeout=1800) -> ResearchTask
import_sources(notebook_id, task_id, sources: Sequence[ResearchSource | dict]) -> list[dict]  # [{"id","title"}]
import_sources_with_verification(notebook_id, task_id, sources, *, max_elapsed=1800) -> list[dict]
cancel(notebook_id, run_id) -> None
```

`ResearchTask` fields: `task_id`, `status`, `query`, `sources` (list of
`ResearchSource`: `url`, `title`, `result_type`, ...), `summary`, `report`.
Pass `task.sources` (or a slice of it) straight into `import_sources` — no
reshaping needed.

### `client.notes`

```
create(notebook_id, title="New Note", content="") -> Note
get(notebook_id, note_id) -> Note
list(notebook_id) -> list[Note]
update(notebook_id, note_id, content, title) -> None
delete(notebook_id, note_id) -> None
list_mind_maps(notebook_id) -> list[Any]
delete_mind_map(notebook_id, mind_map_id) -> None
```

Not currently wrapped by `scripts/notebooklm_client.py` — use the library
directly, or the built-in `notebooklm note` CLI group (`create`, `get`,
`list`, `rename`, `delete`, `save`), which does cover this.

### `client.sharing`

```
get_status(notebook_id) -> ShareStatus
set_public(notebook_id, public: bool) -> ShareStatus
add_user(notebook_id, email, permission: SharePermission=VIEWER, notify=True) -> ShareStatus
remove_user(notebook_id, email) -> ShareStatus
update_user(notebook_id, email, permission) -> ShareStatus
set_view_level(notebook_id, level: ShareViewLevel) -> ShareStatus
```

### `client.settings`

```
get_user_settings() -> UserSettings        # .limits, .output_language
get_account_limits() -> AccountLimits       # .notebook_limit, .source_limit, .tier
get_output_language() -> str | None
set_output_language(language: str) -> str | None
```

## Enum values (real, introspected — several differ from earlier drafts of this skill)

```python
AudioFormat: deep_dive=1, brief=2, critique=3, debate=4
AudioLength: short=1, default=2, long=3
VideoFormat: explainer=1, brief=2, cinematic=3, short=4
VideoStyle: auto_select=1, custom=0, classic=2, whiteboard=3, heritage=4,
            paper_craft=5, watercolor=6, anime=7, retro_print=8, kawaii=9
QuizQuantity: fewer=1, standard=2, more=3
QuizDifficulty: easy=1, medium=2, hard=3
SlideDeckFormat: detailed_deck=1, presenter_slides=2
SlideDeckLength: default=1, short=2
InfographicOrientation: landscape=1, portrait=2, square=3
InfographicDetail: concise=1, standard=2, detailed=3
InfographicStyle: auto_select=1, sketch_note=2, professional=3, bento_grid=4,
                   editorial=5, instructional=6, bricks=7, clay=8, anime=9,
                   kawaii=10, scientific=11
ReportFormat (str enum): briefing_doc, study_guide, blog_post, concept_explanation, custom
ChatMode (str enum): default, learning_guide, concise, detailed
ChatGoal: default=1, custom=2, learning_guide=3
ChatResponseLength: default=1, longer=4, shorter=5
ArtifactType (str enum): audio, video, report, quiz, flashcards, mind_map,
                          infographic, slide_deck, data_table, fantasy_map, file, unknown
SharePermission: owner=1, editor=2, viewer=3
ShareViewLevel: full_notebook=0, chat_only=1
ExportType: docs=1, sheets=2
```

Note `VideoStyle` in particular does **not** include `conversational` or
`dynamic` (an earlier draft of this skill claimed those) — the real style
set is the one above.

## Exceptions

```
NotebookLMError
├── ValidationError, ConfigurationError, MissingDependencyError
├── NotFoundError
├── RPCError → DecodingError, UnknownRPCMethodError, AuthError, AuthExtractionError,
│              NetworkError, RPCTimeoutError, RPCResponseTooLargeError,
│              RateLimitError, ServerError, ClientError
├── NotebookError → NotebookNotFoundError, NotebookLimitError
├── ChatError → ChatResponseParseError
├── SourceError → SourceAddError, SourceProcessingError, SourceTimeoutError, SourceNotFoundError
├── ArtifactError → ArtifactFeatureUnavailableError, ArtifactNotFoundError, ArtifactNotReadyError,
│                    ArtifactParseError, ArtifactDownloadError, ArtifactTimeoutError,
│                    ArtifactPendingTimeoutError, ArtifactInProgressTimeoutError
├── ResearchError → AmbiguousResearchTaskError, ResearchStartUnavailableError,
│                    ResearchTimeoutError, ResearchTaskMismatchError
├── NoteError → NoteNotFoundError
├── MindMapError → MindMapNotFoundError
├── LabelError → LabelNotFoundError
├── CollectionError → CollectionNotFoundError
└── WaitTimeoutError (cross-domain umbrella for wait/poll timeouts)
```

`scripts/auth_helper.py` catches `FileNotFoundError` (no stored session) and
`AuthError` (expired/invalid session) specifically, and turns both into a
"run `notebooklm login`" message instead of a traceback.

## Re-deriving this file after an upgrade

```bash
pip install --upgrade notebooklm
python3 - <<'PY'
import inspect, importlib
for modname in ["_notebooks", "_sources", "_chat", "_artifacts", "_research", "_notes", "_settings", "_sharing"]:
    mod = importlib.import_module(f"notebooklm.{modname}")
    for name, obj in inspect.getmembers(mod):
        if inspect.isclass(obj) and name.endswith("API"):
            print(f"--- {name} ---")
            for mname, m in inspect.getmembers(obj):
                if not mname.startswith("_") and inspect.isfunction(m):
                    print(f"  {mname}{inspect.signature(m)}")
PY
```
