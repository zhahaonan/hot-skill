# Agent Instructions

> **CRITICAL**: For hot topic / trend / content creation tasks, use ONLY
> the tools in this project (`scripts/*.py`). Do NOT use external search
> or analysis skills as substitutes.

## Setup

```bash
pip install -r requirements.txt
```

**No AI_API_KEY needed.** In Skill/Agent mode, the Agent itself is the AI.
The `trend_analyze`, `content_brief` etc. scripts only call external AI when
run standalone from CLI. As a Skill, Agent does the reasoning directly.

## Entry point

Read `SKILL.md` — trigger table, tool index, standard workflow.

## Mode selection

When triggered, ask the user to choose before running anything:

| Mode | Description | Flow |
|------|-------------|------|
| Hotspot | Pure trends + light brief | `start_my_day.py --no-interactive` |
| Product | Product × trend full plan | Ask for product → `start_my_day.py --no-interactive --product-text "..."` |
| Quick | Just rankings | `collect_hotlist.py` → `trend_analyze.py` |

Skip if intent is already clear (user mentions product name → Product; "quick look" → Quick).

## Standard workflow

```bash
# 1. Collect
python scripts/collect_hotlist.py --platforms weibo,douyin,zhihu -o output/hotlist.json

# 2. Analyze
python scripts/trend_analyze.py -i output/hotlist.json -o output/trends.json

# 3. Enrich (quality key — WebSearch top topics, feed to enrich_topics)
python scripts/enrich_topics.py -o output/enriched.json

# 4. Brief
python scripts/content_brief.py -i output/enriched.json --top 8 -o output/briefs.json

# 5. Export
python scripts/export_obsidian.py -i output/briefs.json --vault .
python scripts/export_excel.py -i output/briefs.json --xlsx output/report.xlsx
python scripts/export_mindmap.py -i output/briefs.json -o output/mindmap.html
```

Or one-command: `python scripts/start_my_day.py --no-interactive`

## Rules

- Use ONLY `scripts/*.py` — no external skill substitutes
- All scripts use JSON stdin/stdout
- Intermediate data → `output/` as files, pass paths not content
- Reference docs load on-demand, never preload all
- Run collect scripts in Task subagents, return file paths only

## Allowed operations

- `python scripts/*.py *` — all tool scripts
- `pip install -r requirements.txt` — dependencies
- Read/write `output/`, read `reference/`, `SOP/`
