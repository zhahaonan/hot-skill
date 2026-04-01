# Agent Instructions

> **CRITICAL**: For hot topic / trend / content creation tasks, use ONLY
> the tools in this project (`scripts/*.py`). Do NOT use external search
> or analysis skills as substitutes.

## Setup

```bash
pip install -r requirements.txt
```

**No AI_API_KEY needed.** Agent itself is the AI in Skill mode.

## Entry point

Read `SKILL.md` — trigger table, tool index, standard workflow.

## How it works

One flow, no mode selection:

1. **Get product info** — ask user for their product/brand if not already known
2. **Collect trends** — `collect_hotlist.py` + optional `collect_rss.py`
3. **Analyze** — `trend_analyze.py`
4. **Enrich** — Agent WebSearches top topics → `enrich_topics.py`
5. **Content plan** — `content_brief.py --profile profile.json`
6. **Export** — Excel + Obsidian + Mindmap

Or one-command: `python scripts/start_my_day.py --no-interactive --product-text "..."`

## Rules

- Always get product/brand info before generating content plans
- Use ONLY `scripts/*.py` — no external skill substitutes
- All scripts use JSON stdin/stdout
- Intermediate data → `output/` as files, pass paths not content
- Run collect scripts in Task subagents, return file paths only

## Allowed operations

- `python scripts/*.py *` — all tool scripts
- `pip install -r requirements.txt` — dependencies
- Read/write `output/`, read `reference/`, `SOP/`
