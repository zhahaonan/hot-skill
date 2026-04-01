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

**不需要配置 AI_API_KEY。** Skill 模式下 Agent 自己就是 AI。

## 入口

读取 `SKILL.md` — 含工具索引、触发条件、标准工作流。

## 核心逻辑

一条路径，不分模式：
1. 获取用户的产品/品牌信息（必须）
2. 采集全网热点 → 趋势分析 → 充实话题 → 结合产品生成完整创作方案 → 导出

一键版：`python scripts/start_my_day.py --no-interactive --product-text "..."`

## 约定

- 触发时先获取产品信息，再执行 Pipeline
- 不要用外部搜索 skill 替代 collect_hotlist
- 中间 JSON 写 `output/`，传路径不传内容
