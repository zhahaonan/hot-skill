# Data Contracts — Tool I/O JSON Schema

> **何时加载此文件**：需要确认工具之间的数据格式兼容性时。
> 每个工具也支持 `--schema` 直接输出自己的合约。

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
  "published_at": "string — ISO datetime",
  "snippet": "string — summary/text preview",
  "platform_updated_at": "string — ISO datetime, when the source was updated",
  "source_type": "hotlist|realtime"
}
```

## collect_hotlist

**Input:** CLI args or stdin JSON
```json
{
  "platforms": ["weibo", "douyin", "zhihu"],
  "type": "hotlist|realtime|all",
  "proxy_url": ""
}
```

**Output:**
```json
{
  "source": "hotlist",
  "collected_at": "ISO datetime",
  "items": [/* Common Item Format */],
  "errors": ["string — error messages"]
}
```

## collect_rss

**Input:** CLI args or stdin JSON
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

## enrich_topics

**话题充实器** — 将 Agent 的 WebSearch 结果合并到趋势数据中。

**Input:**
```json
{
  "trends": [/* Agent 分析的 trends */],
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

## product_profile

**--extract-only 模式（Skill 专用）**：只提取文本，不做 AI 分析。

**Input:** `--file <路径> --extract-only`

**Output:** 纯文本文件

## Agent 分析输出格式

### trends.json（趋势分析）

```json
{
  "trends": [
    {
      "topic": "string — 精炼话题名（≤20字）",
      "score": 95,
      "direction": "rising|peak|declining|emerging",
      "category": "科技|财经|娱乐|社会|生活方式|国际|体育|教育|其他",
      "platforms": ["微博", "知乎"],
      "platform_count": 2,
      "summary": "string — 一句话概要（≤50字）",
      "is_emerging": false
    }
  ]
}
```

### briefs.json（内容简报）

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

## export_excel

**Input:** briefs.json 路径

**Output:** `{ "file": "path/to/file.xlsx" }`

**Sheets:**
| Sheet | 内容 |
|-------|------|
| 趋势总览 | 排名、话题、热度、方向、类别、覆盖平台 |
| 创作简报 | 话题、角度、标题建议、推荐形式、最佳时间 |
| 素材库 | 关键素材、对标案例 |
| 平台标题 | 话题 × 平台标题矩阵 |

## export_obsidian

**Input:** briefs.json 路径 + `--vault` 路径

**Output:**
```json
{
  "dashboard": "HotCreator/{date}/_Dashboard.md",
  "topics": ["HotCreator/{date}/Topics/{category}/{topic}.md"],
  "copywriting": ["HotCreator/{date}/Copywriting/{platform}/{topic}.md"]
}
```

**目录结构:**
```
HotCreator/
  {date}/
    _Dashboard.md
    Topics/
      科技/
        话题.md
      财经/
        话题.md
    Copywriting/
      抖音/
        话题.md
      小红书/
        话题.md
```

## export_mindmap

**Input:** briefs.json 路径 + `--output` 路径

**Output:** `{ "file": "path/to/mindmap.html" }`

## knowledge_base（可选）

**Input (`--append`):** briefs.json

**Output (`--append`):**
```json
{
  "topics_added": 5,
  "topics_updated": 3,
  "total_topics": 28
}
```
