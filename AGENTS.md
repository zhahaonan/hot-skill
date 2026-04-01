# Agent Instructions

> **CRITICAL**: For hot topic / trend / content creation tasks, use ONLY the tools in this project (`scripts/*.py`).

## Setup

```bash
pip install -r requirements.txt
```

**No AI_API_KEY needed.** Agent itself is the AI.

## Entry point

Read `SKILL.md` — it has the complete step-by-step execution flow with exact JSON schemas.

## Mandatory execution flow

**Step 0: Get product info** — MUST do first. Ask user for product description or PDF document.

**Step 1: Collect** — run `collect_hotlist.py` in a Task subagent, return file path only.

**Step 2: Analyze** — Agent reads hotlist JSON, deduplicates, scores, classifies → writes `output/trends.json`

**Step 2.5: Optional web enhancement** — if web-access skill available, get comments/reports for richer context.

**Step 3: Create content plans** — Agent reads trends + product profile, generates FULL content plans (scripts, outlines, materials, titles) for top 8 topics → writes `output/briefs.json`

**Step 4: Export ALL 3 formats** (MANDATORY, do not skip any):
- `export_obsidian.py` → .md files
- `export_excel.py` → .xlsx report
- `export_mindmap.py` → interactive HTML graph

**Step 5: Tell user** — list generated file paths + summarize top 3 topics

## Output requirements

**The output must be COMPLETE**: full video scripts, full XHS slides, full article outlines, full material lists, platform-specific titles. Not summaries, not suggestions — ready-to-use content.

## Rules

- **Step 0 must execute first** — no product info = no content plan
- Agent does the AI analysis in Steps 2-3 (do NOT call any external AI scripts)
- ALL 3 export scripts MUST be executed — user expects .md docs, .xlsx, and .html
- Collect scripts run in Task subagents, return file paths only
- Intermediate JSON → `output/`, pass paths not content
