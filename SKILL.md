---
name: hot-creator
version: "5.1.0"
description: 产品 x 热点内容策划工具 — 采集全网热点，结合你的产品生成完整创作方案
user-invocable: true
metadata: {"openclaw": {"emoji": "🔥", "homepage": "https://github.com/zhahaonan/hot-creator", "requires": {"anyBins": ["python3", "python"]}, "install": [{"id": "pip", "kind": "node", "label": "Install deps", "bins": ["python"]}]}}
---

# hot-creator

> **核心逻辑：采集全网热点 → 结合用户的产品/品牌 → 给出完整的创作思路和素材。**

## 安装

```bash
cd {baseDir}
pip install -r requirements.txt
```

## 触发条件

用户意图涉及：热点、趋势、选题、内容创作、热搜、爆款、创作灵感、产品推广、蹭热点

## 强制执行流程

### Step 0 — 获取产品/品牌信息（必须先做）

**这是第一步，没有产品信息无法生成内容方案。**

获取方式：
1. **用户消息中已包含产品描述** → Agent 直接提取产品画像
2. **用户提供了 PDF/文档路径** → 用子智能体提取文本，Agent 再提取画像
   ```bash
   python {baseDir}/scripts/product_profile.py --file <路径> --extract-only -o output/product-raw.txt
   ```
   然后 Agent 读取 `output/product-raw.txt`，提取结构化产品画像
3. **都没有** → 追问用户："你的产品/品牌是什么？请提供产品描述或介绍文档"

**Agent 提取的产品画像格式**（参考 `reference/prompt-templates.md` 的 product_profile 章节）：
```json
{
  "name": "产品/品牌名称",
  "category": "产品类别",
  "one_liner": "一句话描述",
  "target_audience": ["目标人群1", "目标人群2"],
  "usps": ["核心卖点1", "核心卖点2"],
  "keywords": ["关键词1", "关键词2"],
  "industry": "所在行业",
  "tone": "品牌调性"
}
```

### Step 1 — 采集热点

用 **Task 子智能体** 执行采集脚本，只取回文件路径：

```bash
# 热门榜单（默认 29 个平台）
python {baseDir}/scripts/collect_hotlist.py -o output/hotlist.json

# 或指定平台
python {baseDir}/scripts/collect_hotlist.py --platforms weibo,douyin,zhihu -o output/hotlist.json

# 同时采集实时新闻流
python {baseDir}/scripts/collect_hotlist.py --type realtime -o output/realtime.json

# 全部（热门+实时）
python {baseDir}/scripts/collect_hotlist.py --type all -o output/all.json

# RSS 订阅（可选）
python {baseDir}/scripts/collect_rss.py -o output/rss.json
```

**子智能体返回格式**：
```json
{
  "status": "success",
  "output_file": "output/hotlist.json",
  "summary": {"item_count": 150, "platform_count": 5, "errors": []}
}
```

**每条 item 保留上游字段**：title, platform, rank, url, heat, snippet, published_at, platform_updated_at, source_type

### Step 2 — Agent 分析趋势

**Agent 读取采集数据，自己做分析**，输出 JSON 写入 `output/trends.json`。

分析规范参考 `reference/prompt-templates.md` 的 `## trend_analyze` 章节。

分析任务：
- 跨平台去重聚合（同一事件合并）
- 热度评分 0-100（综合排名、覆盖平台数、新鲜度）
- 趋势方向：rising / peak / declining / emerging
- 分类：科技/财经/娱乐/社会/国际/教育/其他
- 一句话概要
- 注意 `platform_updated_at` 和 `source_type` 判断时效性

输出格式：
```json
{
  "trends": [
    {
      "topic": "话题名（≤20字）",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博", "知乎"],
      "platform_count": 2,
      "summary": "一句话概要（≤50字）",
      "is_emerging": false
    }
  ]
}
```

### Step 2.5 — 可选：Web 增强信息获取

**这是可选步骤，用于提升内容质量。**

如果 Agent 有 web-access skill（CDP 能力），可以选择性地：
- 获取小红书热门评论 → 了解用户真实反馈、痛点
- 获取微博评论 → 了解舆论风向、争议点
- 搜索话题相关报道 → 补充真实数据和信源

获取的信息直接写入 trends.json 的 context 字段即可。

**没有 web-access 也不影响核心流程**，Agent 可以用 WebSearch 替代或直接基于采集数据分析。

### Step 3 — Agent 生成完整创作方案

**Agent 读取 trends.json + 产品画像，自己做内容生成**，输出写入 `output/briefs.json`。

**核心原则：只对真正相关的热点生成内容，不强凑。**

#### 关联度判断标准

| 级别 | 判断标准 | 输出要求 |
|------|----------|----------|
| **high** | 用户群体直接重叠 / 解决同一痛点 / 行业直接相关 | 完整内容方案 |
| **medium** | 可从行业视角 / 用户场景 / 价值观角度切入 | 完整内容方案，需加过渡逻辑 |
| **low** | 没有真实连接点 | 只写一句原因，**不生成内容** |

#### 真实性约束（必须遵守）

1. **素材来源**：所有数据点、金句、信源必须来自：
   - 热点原始数据（title, snippet, url）
   - WebSearch/WebFetch 结果
   - 产品资料
   - **禁止编造**任何数字、引语、报道

2. **内容数量**：完整内容方案通常 5-8 个（只对 high/medium 话题），不是越多越好

3. **质量标准**：
   - 每个方案必须有真实的"产品-热点"连接点
   - 素材清单每条都要有来源标注
   - 不确定的信息标注"需核实"

输出规范参考 `reference/prompt-templates.md` 的 `## content_brief` 章节。

#### 每个完整方案包含

1. **产品结合点** — 你的产品跟这个热点的真实连接（第一优先判断）
2. **创作角度**（1-2个）— 具体角度名 + 完整执行步骤 + 产品角色 + 最适合平台
3. **短视频脚本** — hook + 逐句口播 + 画面描述 + CTA
4. **小红书图文** — 封面标题 + 每页内容 + 话题标签
5. **长文大纲** — 标题 + 每章节论点/论据/植入点
6. **素材清单** — 数据点 + 口播金句 + 封面文字 + 信源URL
7. **平台标题** — 抖音/小红书/公众号/知乎/B站各 2 个
8. **发布建议** — 首发平台 + 最佳时间 + 热度窗口期

### Step 4 — 必须执行全部 3 个导出（不可跳过）

**这三个导出是用户最终需要的输出，必须全部执行，不能跳过任何一个。**

用 Task 子智能体并行执行：

```bash
# 1. Obsidian Markdown 笔记（用户在笔记软件中查看）
python {baseDir}/scripts/export_obsidian.py -i output/briefs.json --vault .

# 2. Excel 报表（用户在表格中筛选和分析）
python {baseDir}/scripts/export_excel.py -i output/briefs.json --xlsx output/report.xlsx

# 3. D3 力导向思维导图（用户在浏览器中可视化查看）
python {baseDir}/scripts/export_mindmap.py -i output/briefs.json -o output/mindmap.html
```

**输出文件**：
- `HotCreator/{date}/_Dashboard.md` — 每日概览
- `HotCreator/{date}/Topics/*.md` — 各话题详细笔记
- `output/report.xlsx` — Excel 报表（4 个 Sheet）
- `output/mindmap.html` — 交互式关系图谱

### Step 5 — 告知用户结果

告诉用户生成了哪些文件及路径，简要总结 top 3 话题的创作方向。

## 支持平台

**热门榜单 (29 源)**：微博, 抖音, 知乎, 百度热搜, 今日头条, B站, 澎湃新闻, 虎扑, 百度贴吧, 酷安, 豆瓣, 凤凰网, 牛客, 腾讯新闻, 腾讯视频, 爱奇艺, 虫部落, 36氪人气榜, 华尔街见闻, 财联社热门, 雪球, Hacker News, Product Hunt, GitHub Trending, 少数派, 稀土掘金, Freebuf, Steam

**实时新闻流 (8 源)**：联合早报, 华尔街见闻快讯, 36氪快讯, 财联社电报, IT之家, 格隆汇, 金十数据, 法布财经

> 数据源来自 [NewsNow](https://newsnow.busiyi.world/)

## 工具索引

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| **collect_hotlist** | 全网热榜+实时采集 | 子智能体执行 |
| **collect_rss** | RSS 订阅采集 | 子智能体执行 |
| **product_profile** | PDF/文档文本提取 | 子智能体执行 |
| **export_excel** | Excel 报表导出 | 子智能体执行 |
| **export_obsidian** | Obsidian .md 笔记导出 | 子智能体执行 |
| **export_mindmap** | D3 力导向关系图谱导出 | 子智能体执行 |

> `python {baseDir}/scripts/<tool>.py --schema` 查看接口定义。

## 自修复

| 故障 | 自修复行为 |
|------|-----------|
| 单平台采集超时 | 内置 3 次 retry，指数退避 |
| 依赖未安装 | `ensure_deps()` 自动 pip install |
| 单个 export 失败 | 不影响其他 export，继续执行 |
| 采集全失败 | 用 collect_rss 替代 |

## Harness 模式约定

1. **Step 0 必须先执行** — 没有产品信息无法生成内容方案
2. **采集类脚本用 Task 子智能体执行**，只返回文件路径和摘要，不返回完整数据
3. **中间 JSON 写 `output/`**，传路径不传内容
4. **Agent 自己做 Step 2 和 Step 3 的 AI 分析**，参考 `reference/prompt-templates.md`
5. **Step 4 的 3 个 export 脚本必须全部执行**，用子智能体并行
6. 分析趋势时注意 `platform_updated_at` 和 `source_type` 字段判断时效性
7. 产品画像从用户对话或 PDF 文本中提取，Agent 自己结构化
8. web-access 是可选增强，没有也不影响核心流程
