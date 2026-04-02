---
name: hot-creator
version: "5.8.0"
description: 产品 x 热点内容策划工具 — 采集全网热点，结合你的产品生成完整创作方案
user-invocable: true
metadata: {"openclaw": {"emoji": "🔥", "homepage": "https://github.com/zhahaonan/hot-skill", "requires": {"anyBins": ["python3", "python"]}, "install": [{"id": "pip", "kind": "node", "label": "Install deps", "bins": ["python"]}]}}
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

### Step 0 — 获取产品/品牌/用户画像（必须先做）

**这是第一步，没有画像信息无法生成内容方案。**

**适用对象**：
- **企业/品牌**：提供产品描述、品牌介绍、产品文档
- **个人创作者**：提供个人定位、内容方向、粉丝画像、账号简介

获取方式：
1. **用户消息中已包含描述** → Agent 直接提取画像
2. **用户提供了 PDF/文档路径** → 用子智能体提取文本，Agent 再提取画像
   ```bash
   python {baseDir}/scripts/product_profile.py --file <路径> -o output/profile-raw.txt
   ```
   然后 Agent 读取 `output/profile-raw.txt`，提取结构化画像
3. **都没有** → 追问用户："请提供你的产品/品牌/个人账号介绍，或告诉我你的内容定位和目标受众"

**Agent 提取的画像格式**（参考 `reference/prompt-templates.md` 的 product_profile 章节）：
```json
{
  "name": "产品/品牌/账号名称",
  "type": "product/brand/creator",
  "category": "类别",
  "one_liner": "一句话描述",
  "target_audience": ["目标人群1", "目标人群2"],
  "usps": ["核心卖点/特色1", "核心卖点/特色2"],
  "keywords": ["关键词1", "关键词2"],
  "industry": "所在行业/领域",
  "tone": "品牌调性/内容风格",
  "platforms": ["主要运营平台"],
  "content_direction": ["内容方向1", "内容方向2"]
}
```

> **注意**：获取画像后，后续步骤直接生成全部内容，不再询问用户。用户要的是"拿来就能发"的成品。

---

### Step 1 — 采集热点

用 **Task 子智能体** 执行采集脚本，只取回文件路径：

```bash
# 热门榜单（默认 29 个平台）
python {baseDir}/scripts/collect_hotlist.py -o output/hotlist.json

# 或指定平台
python {baseDir}/scripts/collect_hotlist.py --platforms weibo,douyin,zhihu -o output/hotlist.json

# 同时采集实时新闻流
python {baseDir}/scripts/collect_hotlist.py --type all -o output/all.json
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

---

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

**时间标签（必须包含）**：
- `collected_at`: 采集时间（ISO 8601 格式，如 2026-04-01T14:30:00+08:00）
- 每条趋势的 `hot_window`: 热度窗口期（如 "4月1日 14:00 - 4月2日 10:00"）

输出格式：
```json
{
  "collected_at": "2026-04-01T14:30:00+08:00",
  "trends": [
    {
      "topic": "话题名（≤20字）",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博", "知乎"],
      "platform_count": 2,
      "summary": "一句话概要（≤50字）",
      "hot_window": "4月1日 14:00 - 4月2日 10:00",
      "is_emerging": false
    }
  ]
}
```

---

### Step 2.5 — 判断热点与产品的相关性（必须先做，再生成方案）

**Agent 在生成内容方案前，必须先对每个趋势话题做"产品相关性评分"，只为高相关和部分中相关话题生成完整方案，避免硬蹭。**

#### 评分维度（总分 100）

| 维度 | 分值 | 评分标准 |
|------|------|----------|
| **目标用户重叠度** | 0-25 | 这个热点关注人群，是否与产品目标用户高度重叠。若只是大众围观、与产品用户无明显交集，低分。 |
| **用户情绪/痛点重叠度** | 0-25 | 热点引发的情绪、焦虑、欲望、讨论点，是否与产品解决的问题一致。若只能表面借题发挥，低分。 |
| **产品能力承接度** | 0-25 | 产品是否有明确功能、机制、体验可以承接这个热点。必须说清楚"产品具体通过什么能力切入"。如果只能讲品牌价值观，不能讲产品承接，最多给中分。 |
| **内容传播适配度** | 0-15 | 这个话题是否容易转成短视频、图文、长文等具体内容形态。是否容易形成标题、hook、评论互动。 |
| **品牌与舆情风险** | -10 到 +10 | 若热点涉及灾难、死亡、刑事、极端争议等高风险议题，需谨慎减分；若产品切入角度克制、真诚、具公共讨论价值，可少量加分；若存在明显消费苦难、误导、蹭敏感事件风险，直接降到 low。 |

#### 分级标准

| 级别 | 分数范围 | 处理方式 |
|------|----------|----------|
| **high** | 75-100 | 可生成完整内容方案 |
| **medium** | 55-74 | 可生成完整方案，但必须明确"过渡逻辑"和产品切入链路 |
| **low** | 0-54 | 不生成完整方案，只写一句"为什么不建议蹭" |

#### 输出要求

在 `output/trends.json` 中为每个趋势增加以下字段：

```json
{
  "topic": "话题名",
  "score": 88,
  "product_relevance": "high",
  "relevance_score": 82,
  "relevance_reason": "目标用户关注数字身份与情感表达，该热点触发关于记忆保留与数字痕迹的讨论，产品可通过 AI 原生记忆和数字分身能力自然切入",
  "relevance_breakdown": {
    "audience_overlap": 20,
    "pain_overlap": 24,
    "product_fit": 23,
    "content_fit": 11,
    "brand_risk": 4
  }
}
```

#### 强制约束

1. **不允许**因为热点热度高，就默认适合产品
2. **不允许**只因"都和 AI 有关"就判定 high
3. **不允许**对 low 相关话题生成完整脚本、图文和长文
4. 若 high + medium 话题总数不足 5 个，则只生成实际够格的话题，**不强行凑满 top 8**

---

### Step 2.6 — 强烈建议：Web 增强获取全文

**这一步对内容质量至关重要，强烈建议执行。**

热点采集通常只有标题和摘要，缺少完整上下文。Agent 应该：

1. **获取热点原文**（优先级最高）：
   - 用 WebFetch 访问热点 URL，获取完整报道内容
   - 如果 URL 不可访问，用 WebSearch 搜索话题，找到可访问的信源
   - 至少获取 Top 5 热点的全文内容

2. **获取社交反馈**（如果有 web-access）：
   - 小红书热门评论 → 用户真实反馈、痛点
   - 微博评论 → 舆论风向、争议点

3. **获取的信息写入 trends.json**：
   ```json
   {
     "topic": "话题名",
     "context": {
       "full_article": "从原文获取的完整内容",
       "key_facts": ["事实1", "事实2"],
       "social_sentiment": "舆论倾向",
       "source_url": "原文链接"
     }
   }
   ```

**没有全文会导致**：内容方案缺乏真实细节，AI 只能泛泛而谈。

---

### Step 3 — Agent 生成完整创作方案

**Agent 读取 `output/trends.json`，结合用户的产品信息，优先为 `product_relevance = high` 的话题生成完整方案；若 high 不足，再补充部分 medium 话题。不要为了凑数量而硬生成。通常输出 5-8 个方案即可。**

输出写入 `output/briefs.json`。

---

#### 热点不适配时的 Fallback 模式

**如果所有热点相关性评分都为 low**，执行 Fallback：

```
当热榜无合适切入点时，自动切换为「行业趋势 + 用户情绪 + Evergreen」模式：

1. **行业趋势**（从产品所在行业切入）：
   - 用 WebSearch 搜索 "{industry} 趋势 2024" 或 "{industry} 用户痛点"
   - 生成 2-3 个行业视角的内容方案

2. **用户情绪**（从目标用户痛点切入）：
   - 基于画像中的 target_audience，思考他们当下的焦虑/期待
   - 生成 2-3 个情绪共鸣型内容方案

3. **Evergreen 议题**（长期有效的选题）：
   - 教程类：如何解决 XX 问题
   - 清单类：XX 个工具/方法推荐
   - 观点类：对 XX 现象的看法
```

**Fallback 输出说明**：Agent 要明确告诉用户"今日热榜与产品相关性低，已切换为行业/情绪/长青模式"。

---

#### 真实性约束（必须遵守）

1. **素材来源**：所有数据点、金句、信源必须来自：
   - 热点原始数据（title, snippet, url）
   - WebSearch/WebFetch 结果
   - 产品资料
   - **禁止编造**任何数字、引语、报道

2. **事实标记**：每条素材必须标记类型：
   - `fact`: 有明确来源的事实（必须带 source_url）
   - `inference`: 基于事实的合理推断
   - `suggestion`: 建议/观点（无需来源）

3. **时效降权**：热点超过以下时间自动降权：
   - 超过 6 小时：score -10
   - 超过 12 小时：score -20
   - 超过 24 小时：不作为热点处理

4. **质量标准**：
   - 每个方案必须有真实的"产品-热点"连接点
   - 素材清单每条都要有来源标注
   - 不确定的信息标注"需核实"

输出规范参考 `reference/prompt-templates.md` 的 `## content_brief` 章节。

---

#### 每个完整方案包含（必须全部填写，不可留空）

**以下每个字段都必须填写具体内容，不能是空字符串或空数组：**

1. **产品结合点** — 必须明确写出"目标用户为什么会因为这个热点想到这个产品"以及"产品的哪个能力承接这个讨论"。
   - 如果无法清楚说明"用户-痛点-产品能力"这条链路，则该话题不得进入完整方案。
   - 对低相关话题，只输出一句"不建议硬蹭"的原因，不生成后续内容。
   - 示例：`"目标用户关注效率提升，热点触发对AI写作工具的讨论，产品通过一键生成大纲能力承接'如何快速产出内容'这一痛点"`

2. **创作角度**（1-2个）— 必须包含：
   - `name`: 具体角度名（可直接当标题用）
   - `description`: 完整执行步骤（第一步做什么、第二步做什么、产品怎么出现）
   - `product_role`: 产品在此内容中的具体角色
   - `best_platform`: 最适合平台
   - `appeal`: 吸引力评估（高/中/低）

3. **短视频脚本** — 必须包含：
   - `hook`: 开头第一句完整话术（15字内）
   - `beats`: 4-6个节拍，每个包含完整口播内容（30-60字）+ 画面描述
   - `cta`: 结尾引导语

4. **小红书图文** — 必须包含：
   - `cover_title`: 封面大字（含emoji）
   - `slides`: 6-8张图，每张含标题+正文内容+配图建议
   - `hashtags`: 8-10个标签

5. **长文大纲** — 必须包含：
   - `title`: 公众号标题
   - `sections`: 4-5个章节，每章含heading、core_point、evidence、product_mention

6. **素材清单** — 必须包含（每类至少3条）：
   ```json
   {
     "data_points": [
       {"content": "XX功能上线3天，用户增长50%", "type": "fact", "source_url": "https://..."},
       {"content": "预计将继续增长", "type": "inference", "source_url": null}
     ],
     "sound_bites": [
       {"content": "这个功能绝了", "type": "suggestion"}
     ],
     "screenshot_lines": ["3天增长50%", "用户实测"],
     "sources": [
       {"title": "报道标题", "url": "https://..."}
     ]
   }
   ```

7. **平台标题** — 抖音/小红书/公众号/知乎/B站各 2 个

8. **发布建议** — 必须包含：
   - `first_platform`: 首发平台（思维导图必填）
   - `best_time`: 最佳发布时间
   - `trending_window`: 热度窗口期

> **关键**：如果某个字段留空，导出的 MD 文档和思维导图就会显示空白。用户要的是"拿来就能发"的完整内容，不是框架和方向建议。

---

### Step 4 — 必须执行全部 2 个导出（不可跳过）

**这两个导出是用户最终需要的输出，必须全部执行。**

用 Task 子智能体并行执行：

```bash
# 1. Obsidian Markdown 笔记
python {baseDir}/scripts/export_obsidian.py -i output/briefs.json --vault .

# 2. D3 力导向思维导图
python {baseDir}/scripts/export_mindmap.py -i output/briefs.json -o output/mindmap.html
```

**输出文件**：
- `HotCreator/{date}/_Dashboard.md` — 每日概览
- `HotCreator/{date}/Topics/*.md` — 各话题详细笔记
- `output/mindmap.html` — 交互式关系图谱

---

### Step 5 — 告知用户结果

告诉用户生成了哪些文件及路径，简要总结 top 3 话题的创作方向。

**如果是 Fallback 模式**：明确说明"今日热榜与产品相关性低，已切换为行业/情绪/长青模式"。

---

## 模型漂移自检（每步执行）

Agent 在每个 Step 执行后，必须自检是否符合预期：

| Step | 自检项 | 不符合时的处理 |
|------|--------|---------------|
| Step 0 | 画像是否包含 name, type, target_audience, usps | 重新提取缺失字段 |
| Step 1 | 采集数量是否 ≥ 50 条 | 尝试更多平台或检查网络 |
| Step 2 | trends 数量是否 ≥ 10 条，每条是否有 summary, hot_window | 补充缺失字段 |
| Step 2.5 | 每个话题是否都有 relevance_score 和 product_relevance | 补充评分字段 |
| Step 2.6 | Top 5 热点是否获取了全文或 context | 用 WebFetch/WebSearch 补充 |
| Step 3 | 每个方案是否只对 high/medium 话题生成，所有字段是否填写 | 检查评分，补充空白字段 |
| Step 4 | 两个导出是否都成功 | 检查错误日志重试 |

**自检时机**：每完成一个 Step，立即检查输出文件，确认无误后再进入下一步。

---

## 用户检查与修正

用户可以在以下检查点查看和修正问题：

### 检查点 1：画像确认（Step 0 后）
- **文件**：无（Agent 内部状态）
- **检查方式**：Agent 应该向用户展示提取的画像，用户确认是否正确
- **修正方式**：用户补充或纠正信息，Agent 重新提取

### 检查点 2：热点列表与相关性评分（Step 2.5 后）
- **文件**：`output/trends.json`
- **检查方式**：用户查看每个话题的 relevance_score 和 product_relevance 是否合理
- **修正方式**：告诉 Agent "话题 X 的评分不对，应该从 XX 角度重新评估"

### 检查点 3：内容方案（Step 3 后）
- **文件**：`output/briefs.json`
- **检查方式**：用户查看某个话题的内容方案是否完整、是否真正结合产品
- **修正方式**：告诉 Agent "话题 X 的产品结合点不对，应该从 XX 角度..."

### 检查点 4：导出结果（Step 4 后）
- **文件**：`HotCreator/{date}/` 和 `output/mindmap.html`
- **检查方式**：用户打开 MD 文件或 HTML 查看最终输出
- **修正方式**：告诉 Agent "内容不够具体 / 某话题缺失"，Agent 回到 Step 3 修正

### 快速修正命令

用户可以直接要求 Agent：
- "重新分析第 X 个话题的相关性"
- "话题 X 评分太低，应该从 XX 角度重新评估"
- "补充话题 X 的短视频脚本"
- "Top 3 热点没有获取全文，去获取一下"

---

## 平台差异化模板

不同平台的内容风格差异很大，Agent 生成内容时必须遵循：

### 抖音/短视频
- **开头**：3秒内必须出 hook，用反问/悬念/冲突开场
- **句长**：每句 10-20 字，口语化
- **节奏**：每 5-7 秒一个信息点
- **CTA**：引导点赞/评论/关注，不要硬广
- **敏感表达**：避免"第一""最""绝对"等极限词

### 小红书
- **封面**：大字标题 + emoji + 数字
- **正文**：分段清晰，每段 2-3 句，多用 emoji
- **语气**：闺蜜分享感，避免说教
- **标签**：8-10 个，包含 1-2 个热门标签
- **敏感表达**：避免医疗功效宣称、过度营销

### 公众号
- **标题**：15-25 字，可设悬念/反差
- **正文**：1500-3000 字，结构化分段
- **语气**：专业但不晦涩，有观点
- **产品植入**：自然融入，不生硬
- **敏感表达**：避免政治敏感、舆论操控

### 知乎
- **开头**：先抛观点，再用数据/案例支撑
- **正文**：逻辑清晰，分点论述
- **语气**：专业理性，避免情绪化
- **产品植入**：作为解决方案出现，非广告
- **敏感表达**：避免站队敏感话题

### B站
- **开头**：可玩梗，快速建立人设
- **正文**：有深度，可长视频逻辑
- **语气**：年轻化，可吐槽可认真
- **CTA**：一键三连，弹幕互动
- **敏感表达**：避免低俗、引战

---

## 支持平台

**热门榜单 (29 源)**：微博, 抖音, 知乎, 百度热搜, 今日头条, B站, 澎湃新闻, 虎扑, 百度贴吧, 酷安, 豆瓣, 凤凰网, 牛客, 腾讯新闻, 腾讯视频, 爱奇艺, 虫部落, 36氪人气榜, 华尔街见闻, 财联社热门, 雪球, Hacker News, Product Hunt, GitHub Trending, 少数派, 稀土掘金, Freebuf, Steam

**实时新闻流 (8 源)**：联合早报, 华尔街见闻快讯, 36氪快讯, 财联社电报, IT之家, 格隆汇, 金十数据, 法布财经

> 数据源来自 [NewsNow](https://newsnow.busiyi.world/)

---

## 工具索引

| 工具 | 用途 | 调用方式 |
|------|------|----------|
| **collect_hotlist** | 全网热榜+实时采集 | 子智能体执行 |
| **collect_rss** | RSS 订阅采集 | 子智能体执行 |
| **product_profile** | PDF/文档文本提取 | 子智能体执行 |
| **export_obsidian** | Obsidian .md 笔记导出 | 子智能体执行 |
| **export_mindmap** | D3 力导向关系图谱导出 | 子智能体执行 |

> `python {baseDir}/scripts/<tool>.py --schema` 查看接口定义。

---

## 自修复

| 故障 | 自修复行为 |
|------|-----------|
| 单平台采集超时 | 内置 3 次 retry，指数退避 |
| 依赖未安装 | `ensure_deps()` 自动 pip install |
| 单个 export 失败 | 不影响其他 export，继续执行 |
| 采集全失败 | 用 collect_rss 替代 |
| 无相关热点 | 自动切换 Fallback 模式 |

---

## Harness 模式约定

1. **Step 0 必须先执行** — 没有产品信息无法生成内容方案
2. **采集类脚本用 Task 子智能体执行**，只返回文件路径和摘要，不返回完整数据
3. **中间 JSON 写 `output/`**，传路径不传内容
4. **Agent 自己做 Step 2 和 Step 3 的 AI 分析**，参考 `reference/prompt-templates.md`
5. **Step 2.5 相关性评分必须执行**，低于阈值不生成内容，避免硬蹭
6. **Fallback 模式自动触发**，无合适热点时不卡死
7. **Step 4 的 2 个 export 脚本必须全部执行**，用子智能体并行
8. 分析趋势时注意 `platform_updated_at` 和 `source_type` 字段判断时效性
