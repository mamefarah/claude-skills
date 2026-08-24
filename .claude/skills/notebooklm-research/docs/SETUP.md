# Setup

## 1. Install

This must happen on a machine with a real, interactive browser — the login
step (below) drives Google's actual sign-in flow. It will **not** work in a
headless remote/cloud coding session with no display.

```bash
pip install "notebooklm-py[browser]"
```

`notebooklm-py[browser]` pulls in Playwright, which the login flow uses to
drive a real browser window. If you already have Playwright's Chromium
installed elsewhere, plain `pip install notebooklm-py` plus
`playwright install chromium` works too.

To also use `mcp_server/server.py` (this skill's MCP server, not the
`notebooklm-py`-bundled one):

```bash
pip install notebooklm-py fastmcp==3.4.2
```

(`fastmcp==3.4.2` is pinned to match the version `notebooklm-py` itself
depends on for its own `[mcp]` extra — `pip install "notebooklm-py[mcp]"`
gets you the same thing.)

## 2. Log in (one time, interactive)

```bash
notebooklm login
```

This opens a browser window, walks you through Google sign-in (including
2FA if you have it enabled), and saves a session to
`~/.notebooklm/profiles/<profile>/storage_state.json` (profile defaults to
`default`). The session is reused by every script in this skill — nothing
else needs credentials or an API key.

Verify it worked:

```bash
notebooklm login --check
# or, from this skill's directory:
python3 scripts/auth_helper.py --check
```

Sessions typically last weeks before Google expires them; re-run
`notebooklm login` if `--check` starts failing.

## 3. Try it

```bash
cd .claude/skills/notebooklm-research
python3 scripts/notebooklm_client.py list --json
python3 scripts/notebooklm_client.py create --title "Test Notebook" --sources "https://en.wikipedia.org/wiki/NotebookLM"
```

## 4. (Optional) register the MCP server

Add to your MCP client config (Claude Code, Cursor, Gemini CLI, etc.):

```json
{
  "mcpServers": {
    "notebooklm-research": {
      "command": "python3",
      "args": ["/absolute/path/to/notebooklm-research/mcp_server/server.py"]
    }
  }
}
```

Or over HTTP, for remote/multi-client access:

```bash
python3 mcp_server/server.py --http --port 8766
```
```json
{
  "mcpServers": {
    "notebooklm-research": { "url": "http://localhost:8766/mcp" }
  }
}
```

This is deliberately named `notebooklm-research`, not `notebooklm-mcp` —
`notebooklm-py` already installs its own general-purpose `notebooklm-mcp`
console script (`pip install "notebooklm-py[mcp]"` → `notebooklm-mcp`
binary). This skill's server is narrower and adds the pipeline-style tools
(`nlm_research_pipeline`, `nlm_trend_research`) on top; run whichever one (or
both) fits what you're doing. Don't register both under the same name.

## Multiple accounts / profiles

```bash
notebooklm profile create work
notebooklm profile switch work
notebooklm login   # logs in under the "work" profile
```

Pass `--profile work` to any script in this skill (`notebooklm_client.py`,
`pipeline.py`, `auth_helper.py`) to target a specific profile instead of
whichever one is currently active.

## Remote / cloud coding sessions (Claude Code on the web, CI, etc.)

`notebooklm login` cannot run there — no interactive browser. Instead:

1. Run `notebooklm login` once on your own machine.
2. Copy `~/.notebooklm/profiles/<profile>/storage_state.json` from that
   machine into the remote environment at the same path (or point
   `--profile`/`--storage` at wherever you placed it).
3. Treat that file as a credential: it's a live session cookie for your
   Google account. Don't commit it to a repo, and don't paste it into a
   chat — copy it out-of-band (scp, a secrets manager, etc.).

This skill's scripts never ask for or handle your Google password directly;
they only ever read the already-established session file.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `No valid NotebookLM session found` | Run `notebooklm login` (needs a real browser) |
| `AuthError` after previously working | Session expired — `notebooklm login` again |
| `RateLimitError` / `is_rate_limited: true` | Wait ~60s, retry (see references/pipeline_recipes.md) |
| `ArtifactNotReadyError` | Use `--wait` (CLI) or `wait_for_completion()` (API) instead of downloading immediately |
| Infographic download fails | Expected — known-unreliable upstream; use `--type slide-deck` instead |
| `ModuleNotFoundError: notebooklm` | `pip install notebooklm-py` (the PyPI package name differs from the import name `notebooklm`) |
