## gstack (recommended)

This project uses [gstack](https://github.com/garrytan/gstack) for AI-assisted workflows.
Install it for the best experience:

```bash
git clone --depth 1 https://github.com/garrytan/gstack.git ~/.claude/skills/gstack
cd ~/.claude/skills/gstack && ./setup --team
```

Skills like /qa, /ship, /review, /investigate, and /browse become available after install.
Use /browse for all web browsing. Use ~/.claude/skills/gstack/... for gstack file paths.

## claude-plugins-community marketplace

This project also uses the [Anthropic community plugin marketplace](https://github.com/anthropics/claude-plugins-community),
a read-only, security-scanned catalog of community-contributed Claude Code plugins.
Register it once to make its plugins installable:

```bash
claude plugin marketplace add anthropics/claude-plugins-community
```

Then install any plugin by name from the catalog:

```bash
claude plugin install <plugin-name>@claude-community
```

Browse available plugins at [claude.com/plugins](https://claude.com/plugins/) or in the
marketplace's `.claude-plugin/marketplace.json`.
