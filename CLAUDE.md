# hot-creator — Claude Code 配置

> **重要**：热点/趋势/选题/内容创作相关任务，必须且只能用本项目 `scripts/*.py` 工具。
> 不要用 WebSearch 或其他外部 skill 替代采集和分析步骤。

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
cp config.example.yaml config.yaml
```

环境变量：`AI_API_KEY`（必需）、`AI_MODEL`（可选，默认 deepseek/deepseek-chat）

版本更新：`VERSION` 与 GitHub 比对由 `start_my_day` 自动提示；`python scripts/check_update.py` 手动检查；`HOT_CREATOR_SKIP_UPDATE_CHECK=1` 关闭。

## 入口

读取 `SKILL.md` — 含工具索引、触发条件、标准工作流。

## 模式选择（触发时必须先问）

用户触发 hot-creator 时，**在执行任何脚本之前**，先问用户选哪种模式：
1. **热点模式** → `start_my_day.py --no-interactive`
2. **产品模式** → 追问产品描述 → `start_my_day.py --no-interactive --product-text "..."`
3. **快速模式** → `collect_hotlist.py` + `trend_analyze.py`，不生成 brief

用户已明确说了产品名或"快速看看"则跳过询问。

## 约定

- 严格按 SKILL.md 的标准工作流执行：collect → analyze → **enrich** → brief → **verify** → export
- **enrich 步骤关键**：对 top 话题做 WebSearch 获取真实报道，传给 `enrich_topics.py`，再给 content_brief
- **verify 步骤**：代码变更或 Pipeline 执行后运行 `verify.py`，对抗性检查工具链完整性
- 不要用外部搜索 skill 替代 collect_hotlist
- 不要自己分析替代 trend_analyze / content_brief（它们有完整的 AI prompt）
- 社媒采集（小红书/抖音）由 web-access skill 的 CDP 负责，hot-creator 只做数据规范化
- 中间 JSON 写 `output/`，传路径不传内容
- `config.yaml` 含配置，不提交 git
- **模型分层**：采集用快模型，分析用默认模型，验证用最强模型（详见 `reference/orchestration.md`）
- **读写分离**：验证阶段始终只读；探索/规划阶段不需要写权限
