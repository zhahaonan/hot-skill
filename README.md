# hot-creator

**产品 x 热点内容策划助手** — AI Agent Skill for content creators.

采集全网热点趋势，结合你的产品/品牌/账号，生成完整的创作思路和素材（短视频脚本、小红书图文、长文大纲、素材清单、平台标题）。输出 Obsidian .md 笔记 + D3 交互式关系图谱。

## Quick Start / 快速开始

```bash
git clone https://github.com/zhahaonan/hot-skill.git
cd hot-creator
pip install -r requirements.txt
```

> 有 `uv` 的话更快：`uv pip install -r requirements.txt`
> **不需要配置 AI API Key** — Agent 自己就是 AI，自己做分析。

装好后对 Agent 说：

```
"我的产品是 XXX，帮我结合当下热点生成内容创作方案"
```

Agent 自动执行：采集全网热点 → 分析趋势 → 结合你的产品生成完整创作方案 → 输出 .md + 思维导图。

## 适用对象

- **企业/品牌** — 提供产品描述、品牌介绍、产品文档
- **个人创作者** — 提供个人定位、内容方向、粉丝画像、账号简介

## What You Get / 输出内容

每个热点话题生成**完整的、可直接执行的内容方案**：

| 内容 | 说明 |
|------|------|
| 产品结合点 | 你的产品跟这个热点怎么关联 |
| 创作角度 | 具体到能当标题，含完整执行步骤 |
| 短视频脚本 | 逐句话术 + 画面描述 + CTA |
| 小红书图文 | 封面标题 + 每页内容 + 标签 |
| 长文大纲 | 章节 + 论据 + 产品植入点 |
| 素材清单 | 数据点、口播金句、封面文字、信源 |
| 平台标题 | 抖音/小红书/公众号/知乎/B站各 2 个 |
| 发布建议 | 首发平台 + 最佳时间 + 窗口期 |

输出格式：
- **Obsidian .md 笔记** — 按类别和平台归类的 Markdown 文档
- **D3 关系图谱** — 交互式 HTML 力导向图，可视化话题关联

## 核心特性

### 真实性保证
- 所有数据点、金句、信源必须来自热点原始数据或 WebSearch/WebFetch 结果
- **禁止编造**任何数字、引语、报道
- 不确定的信息标注"需核实"

### 模型漂移自检
每个 Step 执行后 Agent 自动自检：

| Step | 自检项 |
|------|--------|
| Step 0 | 画像是否包含 name, type, target_audience, usps |
| Step 1 | 采集数量是否 ≥ 50 条 |
| Step 2 | trends 是否 ≥ 10 条，每条是否有 summary, hot_window |
| Step 2.5 | Top 5 热点是否获取了全文或 context |
| Step 3 | 每个方案 12 个字段是否全部填写 |
| Step 4 | 两个导出是否都成功 |

### 用户检查点
4 个检查点让用户可以查看中间结果并修正：

1. **画像确认**（Step 0 后）— 确认提取的产品/创作者画像
2. **热点列表**（Step 2 后）— 查看 `output/trends.json` 分析结果
3. **内容方案**（Step 3 后）— 查看 `output/briefs.json` 产品结合点
4. **导出结果**（Step 4 后）— 查看 MD 文件和思维导图

快速修正命令：
- "重新分析第 X 个话题"
- "补充话题 X 的短视频脚本"
- "Top 3 热点没有获取全文，去获取一下"

## 工具脚本

| 脚本 | 用途 | 调用方式 |
|------|------|----------|
| **collect_hotlist** | 全网热榜采集（29 平台） | 子智能体执行 |
| **collect_rss** | RSS 订阅采集 | 子智能体执行 |
| **product_profile** | PDF/文档文本提取 | 子智能体执行 |
| **export_obsidian** | Obsidian .md 导出 | 子智能体执行 |
| **export_mindmap** | D3 关系图谱导出 | 子智能体执行 |

```bash
python scripts/collect_hotlist.py --help    # Usage
python scripts/collect_hotlist.py --schema  # JSON Schema
```

## Harness 模式

此 Skill 采用 Agent Harness 架构：

1. **采集脚本** — 用 Task 子智能体执行，只返回文件路径，大数据不进主上下文
2. **Agent 分析** — Agent 自己做趋势分析和内容生成，参考 `reference/prompt-templates.md`
3. **导出脚本** — 子智能体并行执行 2 个导出
4. **全文检索** — Step 2.5 用 WebFetch/WebSearch 获取热点原文，提升内容质量

## Self-Healing / 自修复

- 单平台采集超时 → 内置 3 次 retry，指数退避
- 单个 export 失败 → 不影响其他 export
- 依赖未安装 → 自动 pip install

## Supported Platforms / 支持平台

**热门榜单 (29 源):** 微博, 抖音, 知乎, 百度热搜, 今日头条, B站, 澎湃新闻, 虎扑, 百度贴吧, 酷安, 豆瓣, 凤凰网, 牛客, 腾讯新闻, 腾讯视频, 爱奇艺, 虫部落, 36氪人气榜, 华尔街见闻, 财联社热门, 雪球, Hacker News, Product Hunt, GitHub Trending, 少数派, 稀土掘金, Freebuf, Steam

**实时新闻流 (8 源):** 联合早报, 华尔街见闻快讯, 36氪快讯, 财联社电报, IT之家, 格隆汇, 金十数据, 法布财经

> 数据源来自 [NewsNow](https://newsnow.busiyi.world/)

## Requirements / 依赖

- Python >= 3.10
- `requests`, `feedparser`, `pytz`, `pyyaml`, `pypdf`

## License

MIT
