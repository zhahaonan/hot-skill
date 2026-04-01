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

**不需要配置 AI_API_KEY。**

## 入口

读取 `SKILL.md` — 含完整的分步执行流程和 JSON 输出结构。

## 强制执行流程

**Step 0: 获取产品信息**（必须先做）
- 用户描述 → Agent 直接提取画像
- PDF 文档 → `product_profile.py --extract-only` → Agent 提取画像
- 都没有 → 追问用户

**Step 1: 采集热点** — 子智能体执行，返回文件路径

**Step 2: 分析趋势** — Agent 自己做，输出 trends.json

**Step 2.5: 可选 Web 增强** — 有 web-access 可获取评论等补充信息

**Step 3: 生成内容方案** — Agent 自己做，结合产品画像，输出 briefs.json

**Step 4: 三个导出全部执行** — 子智能体并行
- export_obsidian → .md 文档
- export_excel → .xlsx 报表
- export_mindmap → HTML 思维导图

**Step 5: 告知用户结果**

## 核心要求

1. **Step 0 必须先执行** — 没有产品信息无法生成内容方案
2. **Agent 自己做 Step 2/3 分析** — 不调用外部 AI 脚本
3. **内容方案必须完整**：完整短视频脚本、完整小红书图文、完整长文大纲、完整素材清单、每平台标题
4. **三个导出脚本必须全部执行，不可跳过**

## 约定

- 采集用 Task 子智能体，只取回文件路径
- 中间 JSON 写 `output/`，传路径不传内容
