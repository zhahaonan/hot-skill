# Orchestration — 多智能体编排策略

> **核心原则：子智能体隔离采集数据，主 Agent 只做决策和输出。**

## 标准架构模式

```
模式                通信方式              适用场景
──────────────────────────────────────────────────────
Pipeline            上一步输出→下一步输入  分析链
Fan-out/Fan-in      分发后聚合            并行采集、并行导出
Hierarchical        树状层级委派          完整情报全流程
```

## Pattern 1: 快速趋势（Fan-out → Pipeline）

用户："现在什么热点"

```
┌─ [子Agent A] collect_hotlist -o hotlist.json ─┐
│  [子Agent B] collect_rss -o rss.json          ├→ [主Agent] 合并 → 分析趋势 → export_excel
└───────────────────────────────────────────────┘
```

**编排步骤**：

1. **Fan-out**: 启动 2 个 Task 子智能体并行运行 collect_* 脚本
   - 每个子智能体：运行脚本 → 只返回 `{"file": "path.json", "count": N, "errors": []}`
   - 子智能体不返回完整数据，只返回文件路径和摘要统计
2. **Merge**: 主 Agent 读取所有 JSON 文件，合并 `items` 数组
3. **Analyze**: 主 Agent 按 `prompt-templates.md` 的趋势分析规范，输出 trends.json
4. **Export**: `python scripts/export_excel.py -i trends.json --xlsx report.xlsx`

## Pattern 2: 内容选题（Fan-out → Enrich → Pipeline → Export）

用户："帮我找选题灵感"

```
Fan-out(collect_*) → Agent分析趋势 → [Agent WebSearch enrichment] → enrich_topics → Agent生成brief → Fan-out(export_*)
```

**编排步骤**：

1. 采集阶段用子智能体隔离
2. Agent 分析趋势
3. **Agent 对 top N 话题做 WebSearch**，收集真实报道/数据/URL
4. **enrich_topics 把真实信息合并到 trends**
5. Agent 生成内容简报
6. export 阶段可并行（excel + obsidian + mindmap）

## Pattern 3: 产品 x 热点

用户："我的产品怎么蹭热点"

```
product_profile(--extract-only) ───┐
                                    ▼
Fan-out(collect_*) → Agent分析趋势 → Agent生成brief(结合产品) → export_*
```

**编排步骤**：

1. 先获取产品信息
   - 文本描述：Agent 直接从对话提取
   - PDF/文档：`product_profile.py --file <路径> --extract-only` 提取文本
2. Agent 从文本中提取结构化产品画像
3. 并行采集热点
4. Agent 分析趋势 + 生成产品结合的内容方案

## Pattern 4: 完整情报（Hierarchical Delegation）

用户："给我一份完整的热点情报报告"

```
[主 Agent — Supervisor]
 │
 ├─ [子Agent 1: 采集组] Fan-out(collect_hotlist + collect_rss)
 │
 ▼ 等待子 Agent 完成
 │
 ├─ [主Agent] 合并数据 → 分析趋势
 ├─ [主Agent] 生成内容简报
 │
 ▼
 ├─ [子Agent 2: 输出组] Fan-out(export_excel + export_obsidian + export_mindmap)
 │
 ▼
[主Agent] 汇总文件路径，告知用户
```

## 子智能体使用规范

### 何时必须用子智能体

| 场景 | 原因 |
|------|------|
| 运行 collect_* 脚本 | 输出 JSON 体积大（100+ items），不能进主上下文 |
| 并行运行多个 export_* | 互不依赖，加速输出 |

### 何时不用子智能体

| 场景 | 原因 |
|------|------|
| Agent AI 分析 | Agent 自身就是 AI，在主上下文直接分析 |
| 读取小型 JSON（< 50 items） | 数据量小，直接读文件更快 |

### 子智能体返回规范

子智能体执行完毕后，**只返回以下格式**，不返回原始数据：

```json
{
  "status": "success|partial|failed",
  "output_file": "path/to/output.json",
  "summary": {
    "item_count": 150,
    "platform_count": 5,
    "errors": ["weibo: timeout"]
  }
}
```

主 Agent 根据 `output_file` 按需读取数据。

## 数据合并策略

多个 collect_* 输出需要合并：

```python
# 合并逻辑（主 Agent 执行）
merged = {"items": []}
for file in [hotlist_json, rss_json]:
    data = read_json(file)
    merged["items"].extend(data.get("items", []))
# 去重（title 完全相同的合并）
```

## 降级策略

| 条件 | 降级方案 |
|------|---------|
| 网络受限 | 先尝试 collect_hotlist 一个平台，确认后再 Fan-out |
| 上下文快满 | 减少分析话题数量，跳过 brief 只做趋势排行 |

## 模型分层策略

根据任务复杂度选择不同能力级别的模型：

```
阶段          推荐模型层级     原因
──────────────────────────────────────────────────
采集/探索      fast (Haiku级)  机械执行，不需要推理
趋势分析      default (Sonnet级) 需要分类/评分，中等推理
内容简报      default (Sonnet级) 核心创作，需要深度推理
导出          fast            机械格式转换
```

## 读写分离

核心原则：**最小权限 — 只有真正需要写的阶段才给写权限**。

```
阶段            需要的权限
──────────────────────────────────────
探索/规划        只读
采集             网络 + 写 output/
趋势分析         只读
内容简报         只读 + 写 output/
导出             写 output/ + vault
```
