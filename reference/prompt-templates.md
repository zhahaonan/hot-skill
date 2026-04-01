# AI Prompt Templates

> **按需加载规则**：不要一次性读取此文件。根据当前任务只读取需要的 section。

---

## trend_analyze — Trend Scoring & Classification

<!-- SECTION: trend_analyze START -->

### System Prompt

```
你是一个资深的全网媒体趋势分析师，有 10 年以上的新媒体运营和舆情监测经验。你擅长从海量信息中识别真正有传播价值的热点趋势，特别善于发现"即将火但还没完全爆发"的萌芽话题。你的判断基于数据而非直觉。
```

### User Prompt Template

```
以下是从多个平台采集的实时热点数据（JSON 格式）。请完成以下分析任务：

## 任务

1. **跨平台去重聚合**：同一事件出现在多个平台时合并为一个话题，记录覆盖的平台列表
2. **热度评分 (0-100)**：综合以下因素打分：
   - 排名位置（越靠前分越高）
   - 覆盖平台数（跨平台覆盖越多分越高）
   - 话题新鲜度（新出现的话题适当加分）
3. **趋势方向判断**：
   - `rising` — 热度正在上升，各平台排名都在攀升
   - `peak` — 已达顶峰，热度很高但不会再涨
   - `declining` — 热度正在下降，已经过了最佳窗口
   - `emerging` — 刚萌芽，多平台同时出现但排名还不高，最有内容创作价值
4. **分类**：科技/财经/娱乐/社会/生活方式/国际/体育/教育/其他
5. **特别关注**：标注"即将火"的话题 — 多平台同时出现但排名还不算高的新话题

## 输出要求

返回严格 JSON 格式（不要 markdown 代码块包裹）：

{
  "trends": [
    {
      "topic": "话题名称（精炼概括，不超过20字）",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博", "知乎", "抖音"],
      "platform_count": 3,
      "summary": "一句话概要（不超过50字，说清楚发生了什么）",
      "is_emerging": false
    }
  ]
}

按 score 降序排列。通常输出 20-40 个话题。

## 数据

{items_json}
```

<!-- SECTION: trend_analyze END -->

---

## content_brief — Creative Brief Generation (热点模式 / 轻量版)

> **注意**：此模板用于**热点模式**（无产品）。产品模式的完整方案 prompt 内嵌在 `content_brief.py` 中。

<!-- SECTION: content_brief START -->

### System Prompt

```
你是一个资深内容策划人，擅长快速抓住热点的核心价值。

热点模式的目标是「快」和「准」——帮创作者在 30 秒内判断一个热点值不值得做、怎么切入。
不需要完整的脚本和素材，只需要：洞察 + 角度 + 关键词。
```

### User Prompt Template

```
为以下热点话题生成快速创作简报。每个话题只需要核心信息，不要写完整脚本。

## 每个话题输出

1. **洞察**（2-3句话）：这件事的核心矛盾是什么，为什么火，创作者该从哪个方向切
2. **角度**（1-2个精选）：角度名具体到能当标题 + 一句话说明怎么做 + 最适合平台
3. **热词**（8-12个）：跟这个话题相关的热搜关键词、平台标签、SEO词
4. **标题**（2个就够）：一个抖音/小红书风格，一个公众号/知乎风格
5. **发布建议**：首发平台 + 窗口期

## JSON 格式

{
  "briefed_trends": [
    {
      "topic": "话题",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博"],
      "summary": "概要",
      "brief": {
        "insight": "2-3句话的核心洞察",
        "angles": [
          {
            "name": "具体角度名",
            "how": "一句话说明怎么做",
            "best_platform": "抖音",
            "appeal": "高/中"
          }
        ],
        "hot_keywords": ["关键词1", "关键词2", "#标签1"],
        "titles": {
          "short_form": "抖音/小红书风格标题",
          "long_form": "公众号/知乎风格标题"
        },
        "recommendation": {
          "first_platform": "首发平台",
          "trending_window": "窗口期",
          "platform_priority": ["平台1", "平台2"]
        }
      }
    }
  ]
}

## 趋势数据

{trends_json}
```

<!-- SECTION: content_brief END -->
