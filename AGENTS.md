# Agent Instructions

> **CRITICAL**: For any hot topic / trend / content creation task, use ONLY the tools
> provided by this project (`scripts/*.py`). Do NOT use external search skills,
> web search tools, or other analysis skills as substitutes. This project is a
> self-contained toolchain.

## Setup (required before first use)

```bash
git clone https://github.com/zhahaonan/hot-creator.git
cd hot-creator
pip install -r requirements.txt
cp config.example.yaml config.yaml
```

Environment variables (required):
```
AI_API_KEY=your-api-key
AI_MODEL=deepseek/deepseek-chat  # optional, default
```

## Entry point

Read `SKILL.md` — it contains the trigger table, tool index, and standard workflow.

## Standard workflow (must follow this order)

### Basic (CLI one-command)

```bash
python scripts/start_my_day.py
```

### High quality (Agent-driven, recommended)

```bash
# Step 1: Collect trends
python scripts/collect_hotlist.py --platforms weibo,douyin,zhihu -o output/hotlist.json

# Step 2: AI analysis
python scripts/trend_analyze.py -i output/hotlist.json -o output/trends.json

# Step 3: Enrich (CRITICAL for quality)
# Agent WebSearches top topics, collects real articles/data/URLs,
# then pipes enrichments into enrich_topics
echo '{"trends":[...],"enrichments":[...]}' | python scripts/enrich_topics.py -o output/enriched.json

# Step 4: Creative brief (uses real-world context for much better output)
python scripts/content_brief.py -i output/enriched.json --top 8 -o output/briefs.json

# Step 5: Export
python scripts/export_obsidian.py -i output/briefs.json --vault .
python scripts/export_excel.py -i output/briefs.json --xlsx output/report.xlsx
python scripts/export_mindmap.py -i output/briefs.json -o output/mindmap.html
```

## Social media data (web-access collaboration)

hot-creator does NOT have a built-in browser engine.
For platforms requiring browser access (Xiaohongshu, Douyin, Weibo):

1. Agent uses **web-access** skill (CDP) to browse the platform
2. Agent extracts titles/URLs/engagement data
3. Agent pipes the data into `collect_social` for normalization
4. Same for competitor monitoring → `monitor_competitor`

`collect_social` and `monitor_competitor` are pure data normalizers — they never browse.

## Version / updates

- Project version is in repo root `VERSION`. Run `python scripts/check_update.py` to compare with GitHub.
- `start_my_day.py` warns on stderr when upstream is newer (cached ~24h). Set `HOT_CREATOR_SKIP_UPDATE_CHECK=1` to disable.

## Verification (adversarial quality checks)

After any pipeline run, use `verify.py` to proactively find issues:

```bash
python scripts/verify.py -o output/verify-report.json        # All suites
python scripts/verify.py --suite anti-hallucination           # Quick check
python scripts/verify.py --suite boundary                     # Edge cases
```

Key principle: **Every PASS requires executed command evidence. Reading code is not verification.**

`verify.py` is read-only — it never modifies scripts or output files.

## Model tiering & read-write separation

Use different model tiers for different stages (see `reference/orchestration.md`):

| Stage | Model tier | Permission |
|-------|-----------|------------|
| Collect/explore | fast | readonly + network |
| Analyze/brief | default | readonly + AI API |
| **Verify** | **strong** | **readonly only** |
| Export | fast | write output/ |

## Rules

- Use ONLY `scripts/*.py` tools — do NOT substitute with external skills
- All scripts use JSON stdin/stdout
- Intermediate data goes to `output/` as files — pass paths, not content
- Reference docs (`reference/`) load on-demand, never preload all
- `AI_API_KEY` env var is required for AI analysis scripts
- For higher quality briefs, always do Step 3 (enrich with WebSearch) before Step 4
- Run `verify.py` after code changes or pipeline runs to catch regressions

## Allowed operations

- `python scripts/*.py *` — all 15 tool scripts
- `pip install -r requirements.txt` — dependencies
- Read/write `output/`, read `reference/`, `SOP/`
