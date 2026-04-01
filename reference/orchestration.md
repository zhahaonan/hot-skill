# Orchestration — 多智能体编排策略

> **何时加载此文件**：编排多工具流水线时。约 ~1800 tokens。
> 此文件定义 Agent 如何编排 hot-creator 的 13 个工具。
> 核心原则：**子智能体隔离采集数据，主 Agent 只做决策和输出。**

## 六种标准架构模式

> 对齐 Agent Harness 工程的 6 种经验证模式。

```
模式                通信方式              适用场景
──────────────────────────────────────────────────────
Pipeline            上一步输出→下一步输入  分析链（analyze → brief → export）
Fan-out/Fan-in      分发后聚合            并行采集（collect_*）、并行导出
Expert Pool         按任务选专家          竞品/行业/产品分析（动态选工具）
Producer-Reviewer   生产→审核→迭代        brief 质量检查、内容审核
Hierarchical        树状层级委派          完整情报全流程（Pattern 5）
Orchestrator        编排器统一调度        start_my_day 一键模式
```

## Pattern 1: 快速趋势（Fan-out → Pipeline）

用户："现在什么热点"

```
┌─ [子Agent A] collect_hotlist -o hotlist.json ─┐
│  [子Agent B] collect_rss -o rss.json          ├→ [主Agent] 合并 → trend_analyze → export_excel
└─ (CDP可用?) [子Agent C] collect_social -o s.json ┘
```

**编排步骤**：

1. **Fan-out**: 启动 2-3 个 Task 子智能体并行运行 collect_* 脚本
   - 每个子智能体：运行脚本 → 只返回 `{"file": "path.json", "count": N, "errors": []}`
   - 子智能体不返回完整数据，只返回文件路径和摘要统计
2. **Merge**: 主 Agent 读取所有 JSON 文件，合并 `items` 数组写入 `merged.json`
3. **Pipeline**: 
   - Agent 原生模式：读取 merged.json，按 prompt-templates 的 trend_analyze 规范分析
   - CLI 模式：`python scripts/trend_analyze.py -i merged.json -o trends.json`
4. **Export**: `python scripts/export_excel.py -i trends.json --xlsx report.xlsx`

## Pattern 2: 内容选题（Fan-out → Enrich → Pipeline → Export）

用户："帮我找选题灵感"

```
Fan-out(collect_*) → trend_analyze → [Agent WebSearch enrichment] → enrich_topics → content_brief → Fan-out(export_*)
```

比 Pattern 1 多两步：enrich_topics（质量关键）和 content_brief。
- 采集阶段用子智能体隔离
- **Agent 对 top N 话题做 WebSearch**，收集真实报道/数据/URL
- **enrich_topics 把真实信息合并到 trends**，content_brief 才能生成高质量素材
- export 阶段可并行（excel + obsidian + mindmap）

## Pattern 3: 产品 x 热点（Pipeline + Expert）

用户："我的产品怎么蹭热点"

```
product_profile ───┐
                   ▼
Fan-out(collect_*) → trend_analyze → content_brief(--profile) → export_*
```

1. 先获取产品信息（Agent 原生：直接从用户对话提取画像；CLI：`product_profile.py`）
2. 并行采集热点
3. content_brief 使用 `--profile` 传入产品画像

## Pattern 4: 竞品监控（Fan-out → Expert）

用户："看看竞品在做什么内容"

```
monitor_competitor ──┐
product_profile ─────┤
                     ▼
              industry_insight → export_excel
```

- monitor_competitor 需要 CDP，运行在子智能体中
- industry_insight 在主 Agent 或 CLI 中运行

## Pattern 5: 完整情报（Hierarchical Delegation）

用户："给我一份完整的热点情报报告"

这是最复杂的模式，采用层级委派：

```
[主 Agent — Supervisor]
 ├─ [子Agent 1: 采集组] Fan-out(collect_hotlist + collect_rss + collect_social)
 ├─ [子Agent 2: 竞品组] monitor_competitor（如果有竞品信息）
 ├─ [子Agent 3: 产品组] product_profile（如果用户提供了产品信息）
 │
 ▼ 等待所有子 Agent 完成
 │
 ├─ [主Agent] 合并数据 → trend_analyze
 ├─ [主Agent] industry_insight（如果有产品画像）
 ├─ [主Agent] content_brief（--profile 如果有产品画像，--top 15）
 │
 ▼
 ├─ [子Agent 4: 输出组] Fan-out(export_excel + export_obsidian + export_mindmap)
 │
 ▼
 [主Agent] 汇总文件路径，告知用户
```

## Pattern 6: 产品搜索 + 热点内容（Agent Search → Pipeline）

用户："搜索我的产品 XXX 并结合热点给我内容思路"

```
[Agent WebSearch] 搜索产品信息 ──→ product_profile(Agent 原生提取)
                                    │
Fan-out(collect_*) ─────────────────┤
                                    ▼
                  trend_analyze → content_brief(--profile) → export_*
                                    │
                  (可选) industry_insight → 行业视角补充
```

**编排步骤**：

1. **产品信息获取**：Agent 用 WebSearch 搜索产品官网/介绍，提取关键信息
2. **画像生成**：
   - Agent 原生模式：直接从搜索结果 + 用户对话提取结构化 profile
   - CLI 模式：`python scripts/product_profile.py --text "..." -o profile.json`
3. **并行采集热点**：子智能体运行 collect_* 脚本
4. **趋势分析**：trend_analyze
5. **产品 × 热点简报**：`content_brief --profile profile.json`
6. **可选深度分析**：`industry_insight --profile profile.json -i trends.json`
7. **并行导出**

与 CLI 的 `start_my_day --profile` 或 `start_my_day --product-text` 对应。

## Pattern 7: Brief 质量审核（Producer-Reviewer）

用户："帮我做选题但要高质量" 或 Agent 自主判断需要质量检查

```
content_brief(producer) → Agent 审核(reviewer) → 修正/补充 → 最终输出
```

**编排步骤**：

1. **Producer**：运行 content_brief 生成初版 briefs
2. **Reviewer**：Agent 读取 briefs.json，逐条审核：
   - 角度是否具体（非"深度分析"类万金油表述）
   - 标题是否符合平台特征
   - 素材是否足够具体可引用
   - product_tie_in 是否自然
3. **迭代**：标记不合格话题，补充/重写对应 brief
4. **输出**：审核通过的 briefs 进入 export 阶段

适用于：用户明确要求高质量输出、确保品牌安全、或 brief 数量较少（≤5）值得精打细磨的场景。大批量（>10）时跳过以节省上下文。

## Pattern 8: 对抗性验证（Adversarial Verification）

用户：任何流水线执行后的质量保障，或 Agent 主动自检

```
Pipeline output → verify.py (all suites) → PASS/FAIL 报告
```

**编排步骤**：

1. **触发**：Pipeline 任一阶段完成后，或全流程结束后
2. **执行**：`python scripts/verify.py -o output/verify-report.json`
3. **审查**：Agent 读取报告，对 FAIL 项定位原因并修复
4. **重验**：修复后重跑对应 suite 确认 PASS

**核心规则**：
- 每个检查必须有 `command_run` 证据，没有执行的不算 PASS
- verify.py 是**纯只读**的 — 它不修改任何脚本或输出文件
- 推荐用最强模型解读 FAIL 报告（对抗性思维需要高智能）

**检查套件**：

| Suite | 探测目标 | 时机 |
|-------|---------|------|
| `schema` | 工具自描述合规 | 工具代码变更后 |
| `boundary` | 边界值/异常输入 | 数据规范化器变更后 |
| `pipeline` | 步骤间数据兼容 | Pipeline 结构变更后 |
| `idempotency` | 幂等性/无重复 | 规范化逻辑变更后 |
| `anti-hallucination` | 空输入不编造 | 任何工具变更后 |

## 子智能体使用规范

### 何时必须用子智能体

| 场景 | 原因 |
|------|------|
| 运行 collect_* 脚本 | 输出 JSON 体积大（100+ items），不能进主上下文 |
| 运行 monitor_competitor | CDP 操作耗时长，可能失败重试 |
| 并行运行多个 export_* | 互不依赖，加速输出 |

### 何时不用子智能体

| 场景 | 原因 |
|------|------|
| Agent 原生 AI 分析 | Agent 自身就是 AI，在主上下文直接分析 |
| 读取小型 JSON（< 50 items） | 数据量小，直接读文件更快 |
| 单个 export 输出 | 一个工具没必要开子智能体 |

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

多个 collect_* 输出需要合并为 trend_analyze 的输入：

```python
# 合并逻辑（主 Agent 或合并脚本）
merged = {"items": []}
for file in [hotlist_json, rss_json, social_json]:
    data = read_json(file)
    merged["items"].extend(data.get("items", []))
write_json(merged, "merged.json")
```

合并后对 items 做轻量去重（title 完全相同的合并）。

## 降级策略

| 条件 | 降级方案 |
|------|---------|
| CDP 不可用 | 跳过 collect_social 和 monitor_competitor，只用 API 热榜 |
| AI API 不可用（CLI 模式） | 跳过 trend_analyze/content_brief，直接用原始热榜数据 export |
| 网络受限 | 先尝试 collect_hotlist 一个平台（如 weibo），确认后再 Fan-out |
| 上下文快满 | 减小 --top N，或只做 Pattern 1（快速趋势）不做 brief |

## 模型分层策略（Model Tiering）

根据任务复杂度选择不同能力级别的模型。核心原则：**把算力花在最需要智能的环节**。

```
阶段          推荐模型层级     权限     原因
──────────────────────────────────────────────────────────
采集/探索      fast (Haiku级)   只读     机械执行，不需要推理
趋势分析      default (Sonnet级) 只读   需要分类/评分，中等推理
话题充实      fast → default    只读     WebSearch + 数据整理
内容简报      default (Sonnet级) 只读   核心创作，需要深度推理
质量验证      strong (Opus级)   只读     对抗性思维，最需要智能
导出          fast              写入     机械格式转换
```

### 为什么验证用最强模型

验证阶段的思维模式与其他阶段完全不同：
- 采集/分析是**建设性**思维（生成正确结果）
- 验证是**破坏性**思维（证明结果有问题）

对抗性验证需要：识别边界条件、怀疑"看起来没问题"的判断、构造攻击向量的创造力。
弱模型做验证容易变成"看了一下代码，应该没问题"。

## 读写分离（Read-Write Separation）

核心原则：**最小权限 — 只有真正需要写的阶段才给写权限**。

```
阶段            需要的权限          原因
──────────────────────────────────────────────────────
探索/规划        只读 (readonly)    只读文件和搜索，不产生副作用
采集             网络 + 写 output/  需要写采集结果到文件
趋势分析         只读 + AI API      读取采集数据，AI 分析，写 output/
话题充实         只读               读取 trends，WebSearch 不写文件
内容简报         只读 + AI API      读取 enriched，AI 生成，写 output/
验证             只读               只执行检查命令，不修改任何文件
导出             写 output/ + vault 生成 Excel/Obsidian/HTML
```

> **verify.py 始终只读**：它只执行命令并捕获输出，从不修改工具脚本或输出文件。
> 这是设计约束：验证者绝不能修改被验证的对象。

### 在 Agent 框架中的实践

```python
Task(subagent_type="shell", model="fast")             # 采集（快模型，写权限）
Task(subagent_type="generalPurpose", readonly=True)    # 分析（默认模型，只读）
Task(subagent_type="generalPurpose", readonly=True)    # 验证（强模型，只读）
Task(subagent_type="shell", model="fast")              # 导出（快模型，写权限）
```

## Agent 原生模式 vs CLI 模式

| 环节 | Agent 原生 | CLI |
|------|-----------|-----|
| 采集 | 子智能体运行脚本 | 命令行运行脚本 |
| AI 分析 | Agent 自身按 prompt-templates 分析 | 脚本调 litellm API |
| 输出 | 子智能体运行 export 脚本 | 命令行运行脚本 |
| 优势 | 无需 AI API 配置，更灵活 | 可自动化/定时任务 |
