# hot-creator — Claude Code 配置

> **重要**：热点/趋势/选题/内容创作任务，只能用本项目 `scripts/*.py` 工具。

## 允许的命令

```
allow: python scripts/*.py *
allow: python -m py_compile *
allow: pip install -r requirements.txt
allow: uv pip install *
```

## 安装

```bash
pip install -r requirements.txt
```

**不需要配置 AI_API_KEY。** Skill 模式下 Agent 自己就是 AI，不需要额外的 AI 密钥。
仅独立 CLI 运行时才需要 `AI_API_KEY`。

## 入口

读取 `SKILL.md` — 含工具索引、触发条件、标准工作流。

## 模式选择

触发时先问用户选模式：
1. **热点模式** → `start_my_day.py --no-interactive`
2. **产品模式** → 追问产品描述 → `start_my_day.py --no-interactive --product-text "..."`
3. **快速模式** → `collect_hotlist.py` + `trend_analyze.py`

用户已明确说了产品名或"快速看看"则跳过询问。

## 约定

- 严格按 SKILL.md 标准工作流执行：collect → analyze → enrich → brief → export
- enrich 步骤关键：对 top 话题做 WebSearch，传给 `enrich_topics.py`
- 不要用外部搜索 skill 替代 collect_hotlist
- 中间 JSON 写 `output/`，传路径不传内容
- `config.yaml` 含配置，不提交 git
