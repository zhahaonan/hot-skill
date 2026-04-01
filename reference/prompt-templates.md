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

> **content_brief** 的产品 x 热点 prompt 内嵌在 `content_brief.py` 的 `PRODUCT_BRIEF_SYSTEM` / `PRODUCT_BRIEF_USER` 中。
> 完整输出结构见 `reference/data-contracts.md`。
