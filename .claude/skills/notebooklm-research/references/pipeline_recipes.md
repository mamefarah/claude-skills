# Pipeline recipes

Command sequences for common jobs, using the scripts in `../scripts/`. All
of these assume a valid stored login (`notebooklm login` already run on this
machine — see `../docs/SETUP.md`) and are run from the skill's root
directory (`cd .claude/skills/notebooklm-research`).

## 1. Research a topic from a handful of known URLs, write an article

```bash
python3 scripts/pipeline.py research-to-article \
  --sources "https://arxiv.org/abs/2401.12345" "https://blog.example.com/agents" \
  --title "AI Agent Frameworks in 2026" \
  --questions \
    "What are the main architectural approaches described?" \
    "What tradeoffs do the sources highlight?" \
  --report \
  --output brief.md
```
Then, in the same Claude conversation: "Write a 1000-word article from
`brief.md`, in my usual voice." Claude does the writing; the brief supplies
the citations.

## 2. Deep research (auto-discover sources you didn't know existed)

```bash
python3 scripts/notebooklm_client.py create --title "AI Coding Assistants" --sources \
  "https://seed-article.com"
# note the returned notebook_id, then:
python3 scripts/notebooklm_client.py research \
  --notebook NOTEBOOK_ID --query "AI coding assistants 2026 comparison" --mode deep
python3 scripts/notebooklm_client.py research-poll --notebook NOTEBOOK_ID --import-top 5 --json
```
Or in one step via `pipeline.py`:
```bash
python3 scripts/pipeline.py research-to-article \
  --title "AI Coding Assistants" \
  --deep-research "AI coding assistants 2026 comparison" \
  --sources "https://seed-article.com" \
  --output brief.md
```

## 3. Generate a podcast + companion article

```bash
NB=$(python3 scripts/notebooklm_client.py create --title "Weekly Digest" \
  --sources "https://a.com" "https://b.com" --json | python3 -c "import json,sys; print(json.load(sys.stdin)['notebook_id'])")

python3 scripts/notebooklm_client.py generate --notebook "$NB" --type audio --format deep_dive --wait --json
python3 scripts/notebooklm_client.py download --notebook "$NB" --type audio --output podcast.m4a

python3 scripts/pipeline.py research-to-article --notebook "$NB" --title "Weekly Digest" --output brief.md
```
The article brief and the podcast come from the same underlying research —
use the article as show notes, or vice versa.

## 4. Quiz + flashcards from an existing notebook

```bash
python3 scripts/notebooklm_client.py generate --notebook NOTEBOOK_ID --type quiz --quantity standard --difficulty medium --wait
python3 scripts/notebooklm_client.py download --notebook NOTEBOOK_ID --type quiz --output quiz.json

python3 scripts/notebooklm_client.py generate --notebook NOTEBOOK_ID --type flashcards --wait
python3 scripts/notebooklm_client.py download --notebook NOTEBOOK_ID --type flashcards --output flashcards.json
```

## 5. Slide deck (use instead of infographic — see the warning in SKILL.md)

```bash
python3 scripts/notebooklm_client.py generate --notebook NOTEBOOK_ID --type slide-deck --format detailed_deck --wait
python3 scripts/notebooklm_client.py download --notebook NOTEBOOK_ID --type slide-deck --output slides.pdf
```

## 6. Weekly RSS digest

```bash
python3 scripts/pipeline.py batch-digest \
  --rss "https://example.com/feed.xml" \
  --title "Weekly AI Digest" \
  --max-entries 15 \
  --output digest.md
```

## 7. Trending topic → researched content (requires trend-pulse MCP)

Trend *discovery* only works inside a Claude conversation that also has the
`trend-pulse` MCP server connected — `pipeline.py` cannot call it directly.
Two-step flow:

1. In the conversation, ask Claude to call trend-pulse's
   `get_trending(geo="US", count=20)` and save the interesting entries'
   URLs to a JSON file, e.g. `trends.json`:
   ```json
   [{"title": "...", "url": "https://..."}, ...]
   ```
2. Then research the chosen topic:
   ```bash
   python3 scripts/pipeline.py trend-to-content \
     --topic "The topic Claude picked" \
     --trends-file trends.json \
     --platform threads \
     --output trend_brief.json
   ```
   Or skip the file and pass URLs directly with `--sources`.

The same two-step split applies to the MCP server's `nlm_trend_research`
tool — it takes `source_urls` as an argument rather than calling trend-pulse
itself, for the same reason.

## 8. Share a notebook

```bash
python3 scripts/notebooklm_client.py share --notebook NOTEBOOK_ID --public
python3 scripts/notebooklm_client.py share --notebook NOTEBOOK_ID --add teammate@example.com --permission editor
```

## Rate limits

See SKILL.md's Rate Limits table for estimated safe call rates per operation
type (undocumented upstream; back off ~60s on a `RateLimitError` /
`is_rate_limited: true`). None of the scripts here retry automatically on
rate limits — if you're scripting a loop over many notebooks/artifacts, add
your own `time.sleep()` between calls.
