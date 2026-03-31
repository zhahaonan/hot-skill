# Agent Instructions

> **IMPORTANT**: Do NOT fetch files one by one from GitHub.
> Clone the repo first, then read files locally. This is much faster.
>
> ```bash
> git clone https://github.com/zhahaonan/hot-creator.git
> cd hot-creator
> pip install -r requirements.txt   # 5 packages, ~5 MB, ~3 seconds
> ```
>
> After cloning, read `SKILL.md` locally — it is the only entry point.

## What is this?

`hot-creator` is an AI Agent Skill for content creators. It collects trending topics from Chinese social media, scores them, and generates creative briefs. Output: Excel (4 sheets) + Obsidian (categorized notes + platform copywriting) + force-directed graph.

## After cloning — setup

```bash
pip install -r requirements.txt     # core only, ~5 MB
cp config.example.yaml config.yaml  # if not exists
```

`litellm` is NOT needed as a Skill (Agent IS the AI). CLI standalone mode only: `pip install -r requirements-cli.txt`

## How to use

1. Read `SKILL.md` — trigger table + tool index + architecture patterns
2. Run scripts: `python scripts/<tool>.py` with JSON stdin/stdout
3. Intermediate data → `output/` directory as files, pass paths not content
4. Reference docs in `reference/` are on-demand, never preload all

## Allowed operations

- `python scripts/*.py *` — all 13 tool scripts
- `pip install -r requirements.txt` — core deps
- Read/write `output/`, read `reference/`, `SOP/`, `site-patterns/`
