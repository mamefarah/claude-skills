## gstack (recommended)

This project uses [gstack](https://github.com/garrytan/gstack) for AI-assisted workflows.
Install it for the best experience:

```bash
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup --team
```

Skills like /qa, /ship, /review, /investigate, and /browse become available after install.
Use /browse for all web browsing. Use ~/.claude/skills/gstack/... for gstack file paths.

## agentmemory (optional)

[agentmemory](https://github.com/rohitg00/agentmemory) gives Claude Code persistent,
searchable memory across sessions (hybrid BM25 + vector + graph search over past
tool calls and decisions), so you don't have to re-explain a codebase every session.
Install it for the best experience:

```bash
npx -y @agentmemory/agentmemory@latest
```

This starts the local memory server (with its pinned `iii` engine) and walks you
through an interactive setup: pick which agents to wire (Claude Code, Cursor, Codex,
Gemini CLI, etc.) and whether to use an LLM provider or stay keyless (BM25-only search,
no API key required).

For Claude Code specifically, wire the native plugin (12 hooks + 17 skills + the
`@agentmemory/mcp` server, all in one step):

```
/plugin marketplace add rohitg00/agentmemory
/plugin install agentmemory
```

Verify the server is up with `curl http://localhost:3111/agentmemory/health`; the
real-time viewer is at http://localhost:3113.

Run these on your own machine, not inside a disposable Claude Code on the web session —
the memory server is a long-running local daemon and the plugin step modifies your
personal `~/.claude/settings.json`, so it should be an intentional choice you make once
locally rather than something applied automatically per session.
