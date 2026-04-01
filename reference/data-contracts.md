# Data Contracts — Tool I/O JSON Schema

> **何时加载此文件**：需要确认工具之间的数据格式兼容性时。
> 每个工具也支持 `--schema` 直接输出自己的合约。

All tools share a unified item format for composability. Each tool reads JSON from stdin (or `--input`) and writes JSON to stdout (or `--output`).

## Tool Discovery

```bash
# 查看工具自述
python scripts/<tool>.py --help

# 输出 JSON Schema
python scripts/<tool>.py --schema

# 查看版本
python scripts/<tool>.py --version
```

## Common Item Format

All collect tools output items in this format:

```json
{
  "title": "string — topic/article title",
  "platform": "string — display name (e.g. 微博)",
  "platform_id": "string — machine ID (e.g. weibo)",
  "rank": "integer — position on the list (1-based)",
  "url": "string — original URL",
  "heat": "string — heat value if available",
  "published_at": "string — ISO datetime (RSS only)",
  "summary": "string — article summary (RSS only)"
}
```

## collect_hotlist

**Input:**
```json
{
  "platforms": ["weibo", "douyin", "zhihu"],
  "proxy_url": ""
}
```

**Output:**
```json
{
  "source": "hotlist",
  "items": [/* Common Item Format */],
  "errors": ["string — error messages"]
}
```

## collect_rss

**Input:**
```json
{
  "feeds": [
    {
      "id": "hn",
      "name": "Hacker News",
      "url": "https://hnrss.org/frontpage",
      "max_items": 20,
      "max_age_days": 3
    }
  ]
}
```

**Output:**
```json
{
  "source": "rss",
  "items": [/* Common Item Format */],
  "errors": ["string"]
}
```

## collect_social

**纯数据规范化器** — 不做任何浏览器操作。Agent 用 web-access skill 浏览社媒平台，提取数据后传给此工具规范化。

**Input:**
```json
{
  "items": [
    {
      "title": "话题标题",
      "platform_id": "xiaohongshu",
      "url": "https://...",
      "heat": "1.2万",
      "rank": 1
    }
  ],
  "platform_id": "默认 platform_id（如果 items 中没有指定）"
}
```

**Output:**
```json
{
  "source": "social",
  "items": [/* Common Item Format */],
  "errors": ["string"]
}
```

**反幻觉**：无 items 输入则输出空结果，绝不编造数据。

## enrich_topics

**话题充实器** — 将 Agent 的 WebSearch 结果合并到趋势数据中。这是提升 content_brief 输出质量的关键步骤。

**Input:**
```json
{
  "trends": [/* trend_analyze 输出 */],
  "enrichments": [
    {
      "topic": "话题名（必须匹配 trends 中的 topic）",
      "articles": [
        {"title": "报道标题", "url": "https://...", "source": "36氪", "summary": "核心事实一句话"}
      ],
      "data_points": ["具体数字或统计"],
      "quotes": ["相关人物的原话"],
      "background": "2-3句话背景说明",
      "controversy": "主要争议焦点"
    }
  ]
}
```

**Output:**
```json
{
  "trends": [/* 原始 trends + context 字段 */],
  "enrichment_stats": {
    "total_topics": 8,
    "enriched_topics": 6,
    "total_articles": 15,
    "total_data_points": 12
  }
}
```

content_brief 会识别 `context` 字段，在 AI prompt 中注入真实报道信息，生成更具体、可验证的素材。

## trend_analyze

**Input:** Merged items from all collect tools:
```json
{
  "items": [/* all items merged */]
}
```

**Output:**
```json
{
  "trends": [
    {
      "topic": "string — distilled topic name",
      "score": 95,
      "direction": "rising|peak|declining|emerging",
      "category": "科技|财经|娱乐|社会|生活方式|国际|体育|教育|其他",
      "platforms": ["微博", "知乎"],
      "platform_count": 2,
      "summary": "string — one-line summary",
      "is_emerging": false
    }
  ]
}
```

## product_profile

**Input (CLI):**
- `--text "产品描述文本"` 或 `--file product.pdf` 或 stdin JSON：

```json
{
  "text": "string — 产品描述文本",
  "file": "string — 产品文档路径 (PDF/MD/TXT/DOCX)",
  "competitors": ["竞品A", "竞品B"]
}
```

**Output:**
```json
{
  "profile": {
    "name": "string — 产品名称",
    "category": "string — 产品类别",
    "one_liner": "string — 一句话描述",
    "target_audience": ["目标人群1", "目标人群2"],
    "usps": ["核心卖点1", "核心卖点2"],
    "keywords": ["关键词1", "关键词2"],
    "industry": "string — 所在行业",
    "tone": "string — 品牌调性",
    "competitors": ["竞品1", "竞品2"],
    "content_goals": ["内容目标1", "内容目标2"]
  }
}
```

## content_brief

两种模式输出完全不同的结构：

### 热点模式（轻量 — 快速判断用）

**Input:** Output from trend_analyze:
```json
{
  "trends": [/* trend objects */]
}
```

**Output:**
```json
{
  "briefed_trends": [
    {
      "topic": "string",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博"],
      "summary": "string",
      "brief": {
        "insight": "string — 2-3句话核心洞察",
        "angles": [
          {
            "name": "string — 具体角度名",
            "how": "string — 一句话说明",
            "best_platform": "抖音",
            "appeal": "高|中"
          }
        ],
        "hot_keywords": ["关键词1", "#标签1", "SEO词"],
        "titles": {
          "short_form": "string — 抖音/小红书风格",
          "long_form": "string — 公众号/知乎风格"
        },
        "recommendation": {
          "first_platform": "string",
          "trending_window": "string",
          "platform_priority": ["string"]
        }
      }
    }
  ]
}
```

### 产品模式（完整方案 — 拿来就能用）

**Input:** trends + profile JSON 文件 (`--profile profile.json`)

**Output:**
```json
{
  "briefed_trends": [
    {
      "topic": "string",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博"],
      "summary": "string",
      "product_relevance": "high|medium|low",
      "brief": {
        "product_tie_in": "string — 产品与热点的真实连接",
        "angles": [
          {
            "name": "string — 具体角度名（能当标题）",
            "description": "string — 完整执行方案",
            "product_role": "string — 产品在此内容中的角色",
            "best_platform": "string",
            "appeal": "高|中|低"
          }
        ],
        "outlines": {
          "short_video": {
            "hook": "string — 完整开头话术",
            "beats": [{"content": "string — 30-60字口播内容", "visual": "string — 画面描述"}],
            "cta": "string"
          },
          "xiaohongshu": {
            "cover_title": "string — 封面大字含emoji",
            "slides": [{"title": "string", "content": "string", "image_note": "string"}],
            "hashtags": ["string"]
          },
          "article": {
            "title": "string",
            "sections": [
              {
                "heading": "string",
                "core_point": "string — 核心论点2-3句",
                "evidence": "string — 论据/数据",
                "product_mention": "string|null — 产品植入点"
              }
            ]
          }
        },
        "materials": {
          "data_points": [{"fact": "string — 含数字", "source": "string", "how_to_use": "string"}],
          "sound_bites": ["string — 8-18字口播金句"],
          "screenshot_lines": ["string — ≤14字封面/字幕文字"],
          "sources": [{"title": "string", "url": "string", "takeaway": "string"}]
        },
        "titles": {
          "douyin": ["string", "string"],
          "xiaohongshu": ["string", "string"],
          "gongzhonghao": ["string", "string"],
          "zhihu": ["string", "string"],
          "bilibili": ["string", "string"]
        },
        "recommendation": {
          "first_platform": "string",
          "best_time": "string",
          "trending_window": "string",
          "platform_priority": ["string"]
        },
        "risk_notes": "string — 风险提示"
      }
    }
  ]
}
```

> **区别总结**：
> - 热点模式：洞察 + 角度 + 热词 + 2个标题 + 发布建议（快速决策用）
> - 产品模式：完整脚本 + 完整图文 + 完整大纲 + 完整素材 + 每平台标题（拿来就能发）

## industry_insight

**Input:** trends + profile（必填）+ competitor_data（可选）

CLI 支持 `--profile profile.json` 和 `--competitors comp.json` 独立文件，或合并为单一 JSON：
```json
{
  "trends": [/* trend_analyze output */],
  "profile": {/* product_profile output 的 profile 字段 */},
  "competitor_data": [/* monitor_competitor output (可选) */]
}
```

**Output:**
```json
{
  "industry_trends": [
    {
      "topic": "string",
      "relevance_score": 90,
      "relevance_reason": "string",
      "original_score": 85,
      "direction": "string",
      "category": "string",
      "action": "追热点|蹭话题|深度解读|避险",
      "urgency": "高|中|低"
    }
  ],
  "competitor_analysis": {
    "summary": "string",
    "common_themes": ["string"],
    "gaps": ["string"],
    "top_performing": ["string"]
  },
  "opportunities": [
    {
      "title": "string",
      "description": "string",
      "related_trend": "string",
      "difficulty": "高|中|低",
      "expected_impact": "高|中|低",
      "suggested_platforms": ["string"]
    }
  ],
  "warnings": [
    {
      "title": "string",
      "description": "string",
      "suggestion": "string"
    }
  ]
}
```

## knowledge_base

**Input (`--append`):** Output from content_brief:
```json
{
  "briefed_trends": [/* content_brief output */]
}
```

**Output (`--append`):**
```json
{
  "topics_added": 5,
  "topics_updated": 3,
  "total_topics": 28
}
```

**Output (`--query "关键词"`):**
```json
{
  "query": "string",
  "results": [
    {
      "topic": "string",
      "score": 95,
      "category": "string",
      "first_seen": "2025-04-01",
      "last_seen": "2025-04-03",
      "appearances": 3,
      "themes": ["string"],
      "related": ["string"]
    }
  ]
}
```

**Output (`--export-graph --days 7`):**
```json
{
  "nodes": [
    {
      "id": "string",
      "type": "topic|theme",
      "category": "string",
      "color": "#hex",
      "score": 95,
      "radius": 25,
      "is_today": true,
      "is_persistent": false,
      "days": 1,
      "themes": ["string"],
      "summary": "string"
    }
  ],
  "links": [
    {
      "source": "string",
      "target": "string",
      "type": "theme|related"
    }
  ],
  "meta": {
    "total_topics": 28,
    "total_days": 7,
    "rolling_days": 7
  }
}
```

**存储结构 (`output/knowledge_base.json`):**
```json
{
  "version": "1.0",
  "last_updated": "2025-04-01",
  "topics": {
    "话题名": {
      "first_seen": "date",
      "last_seen": "date",
      "appearances": [{"date": "date", "score": 95, "direction": "rising"}],
      "category": "string",
      "themes": ["string"],
      "platforms": ["string"],
      "summary": "string",
      "first_platform": "string",
      "peak_score": 95,
      "related_topics": ["string"]
    }
  },
  "themes": {
    "主题名": {
      "topic_ids": ["string"],
      "first_seen": "date",
      "frequency": 10,
      "last_seen": "date"
    }
  },
  "daily_snapshots": {
    "2025-04-01": {
      "topic_count": 8,
      "hot": 3,
      "emerging": 2,
      "topics": ["string"]
    }
  }
}
```

## export_excel

**Input:** Output from content_brief

**Output:** `{ "file": "path/to/file.xlsx" }`

**Sheets:**
| Sheet | 内容 |
|-------|------|
| 趋势总览 | 排名、话题、热度、方向、类别、覆盖平台 |
| 创作简报 | 话题、角度、标题建议、推荐形式、最佳时间 |
| 素材库 | 关键素材、对标案例（兼容产品模式 brand/topic） |
| 平台标题 | 话题 × 平台标题矩阵（抖音/小红书/公众号/知乎/B站） |

## export_obsidian

**Input:** Output from content_brief + `--vault` path

**Output:**
```json
{
  "dashboard": "HotCreator/{date}/_Dashboard.md",
  "topics": ["HotCreator/{date}/Topics/{category}/{topic}.md"],
  "copywriting": ["HotCreator/{date}/Copywriting/{platform}/{topic}.md"],
  "weekly_digest": "HotCreator/_WeeklyDigest.md"
}
```

**目录结构:**
```
HotCreator/
  {date}/
    _Dashboard.md                     # 每日仪表板
    Topics/
      科技/                           # ← 按 category 归类
        Anthropic Claude Code源码泄露.md
      财经/
        3月PMI.md
    Copywriting/                      # ← 按平台归类的文案草稿
      抖音/
        话题1.md                      # short_video 脚本
      小红书/
        话题1.md                      # 封面标题 + 图片内容 + 话题标签
      公众号/
        话题1.md                      # 长文框架（引言/正文/结语）
  _WeeklyDigest.md                    # 周报（≥2天数据时自动生成）
```

**CLI 选项:** `--no-copywriting` 跳过文案生成

## export_mindmap

**Input:** Output from content_brief + `--output` path
**Output:** `{ "file": "path/to/mindmap.html" }`
