#!/usr/bin/env python3
"""
content_brief — AI-powered creative brief generation for content creators.
Takes trend analysis output, generates full creative briefs per topic.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from pathlib import Path
from _common import (
    base_argparser, handle_schema, read_json_input, write_json_output,
    fail, SKILL_ROOT, parse_ai_json
)

litellm = None  # lazy import — only needed for CLI mode

SCHEMA = {
    "name": "content_brief",
    "description": "Generate product x trend creative briefs: full content plans combining hot topics with your product/brand. --profile required for best results.",
    "input": {
        "type": "object",
        "properties": {
            "trends": {
                "type": "array",
                "description": "Trends from trend_analyze output",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "score": {"type": "integer"},
                        "direction": {"type": "string"},
                        "category": {"type": "string"},
                        "platforms": {"type": "array"},
                        "summary": {"type": "string"}
                    },
                    "required": ["topic"]
                }
            },
            "profile": {
                "type": "object",
                "description": "Product profile (optional — enables product x trend mode with tailored content ideas)"
            }
        },
        "required": ["trends"]
    },
    "output": {
        "type": "object",
        "properties": {
            "briefed_trends": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "score": {"type": "integer"},
                        "brief": {"type": "object", "description": "Full creative brief — see data-contracts.md for structure"}
                    }
                }
            }
        }
    },
    "examples": {
        "cli": "python scripts/content_brief.py -i trends.json --profile profile.json --top 10 -o briefs.json",
        "agent_native": "Agent reads trends JSON + product info, generates briefs directly"
    },
    "errors": {
        "no_api_key": "AI_API_KEY 未设置 → Agent 原生模式不需要",
        "no_trends": "无 trends 输入 → 先运行 trend_analyze",
        "batch_error": "单个 batch AI 调用失败 → 该 batch 话题标记 error，继续处理其他 batch"
    }
}




def call_ai(system_prompt: str, user_prompt: str, model: str, api_key: str, api_base: str = None,
            batch_size: int = 1) -> str:
    """Call AI model via litellm. Only used in standalone CLI mode."""
    global litellm
    if litellm is None:
        try:
            import litellm as _litellm
            litellm = _litellm
        except ImportError:
            fail("litellm not installed. Standalone CLI mode requires: pip install litellm\n"
                 "As a Skill, Agent does the AI analysis — this script is not needed.")
    max_tokens = max(16000, min(128000, 16000 * batch_size))
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
    }
    if api_key:
        kwargs["api_key"] = api_key
    if api_base:
        kwargs["api_base"] = api_base

    response = litellm.completion(**kwargs)
    return response.choices[0].message.content.strip()


def parse_ai_response(text: str) -> dict:
    """Parse AI response using the shared robust parser, then normalize key names."""
    result = parse_ai_json(text)

    if isinstance(result, list):
        result = {"briefed_trends": result}

    if isinstance(result, dict) and "briefed_trends" not in result:
        for key in ("briefs", "creation_briefs", "trends", "data", "results", "content_briefs"):
            if key in result and isinstance(result[key], list):
                result["briefed_trends"] = result.pop(key)
                break
        if "briefed_trends" not in result:
            for key, val in result.items():
                if isinstance(val, list) and len(val) > 0 and isinstance(val[0], dict):
                    if "topic" in val[0] or "brief" in val[0]:
                        result["briefed_trends"] = result.pop(key)
                        break

    return result


PRODUCT_BRIEF_SYSTEM = """你是一个品牌内容策略师 + 资深文案人。你输出的不是「建议」，而是**拿来就能发的完整内容方案**。

你的判断标准：
- 如果一个热点跟这个产品没关系，就直说「关联弱，不建议硬蹭」，给 product_relevance: "low"，只写一句话
- 如果有关系（high/medium），你要输出**完整的、可直接执行的内容**，包括：
  - 完整的短视频脚本（逐句话术 + 画面描述，不是概要）
  - 完整的小红书图文（封面标题 + 每一页写什么 + 标签）
  - 完整的长文大纲（每个章节的核心论点 + 论据 + 产品植入点）
  - 完整的素材清单（具体数据、具体口播金句、具体封面文字）
  - 每个平台的标题 2 个（直接能用，不是方向建议）

你绝不做的事：
- 不编造产品没有的功能来凑热点
- 不写「可以结合XX」「建议从XX角度」这种半成品——要写就写完整内容
- 不用「深度分析」「情感共鸣」这种万金油词——每一句都要具体到能直接用"""

PRODUCT_BRIEF_USER = """## 我的产品

{profile_json}

## 当前热点

{trends_json}

## 你的任务

### 第一步：判断关联度
- **high**: 产品直接相关（用户群体重叠/解决同一痛点/行业直接相关）→ 输出完整方案
- **medium**: 有间接关系（可以从行业角度/用户场景角度切入）→ 输出完整方案
- **low**: 没什么关系 → 只写 product_tie_in: "关联较弱，不建议硬蹭"，其他字段留空

### 第二步：对 high/medium 的话题，输出完整可执行方案

每个话题必须包含以下**完整内容**（不是建议，是成品）：

**角度**（1-2 个深入的）：
- 角度名要具体到能当标题
- description 要写清楚「第一步做什么、第二步做什么、产品怎么出现」

**短视频脚本**（完整到能直接拍）：
- hook: 开头第一句话的完整话术（15字内，能让人停下来）
- beats: 4-6 个节拍，每个写完整的口播内容（每条 30-60 字）+ 画面描述
- cta: 结尾引导语

**小红书图文**（完整到能直接做图）：
- cover_title: 封面大字（10字内，含 emoji）
- slides: 6-8 张图，每张写清楚「大标题 + 正文内容 + 配图建议」
- hashtags: 8-10 个标签

**长文大纲**（完整到能直接写）：
- title: 公众号标题
- sections: 4-5 个章节，每章包含 heading + core_point（核心论点 2-3 句）+ evidence（论据/数据）+ product_mention（产品怎么自然出现，没有就写 null）

**素材清单**（具体到能直接引用）：
- data_points: 5-8 条，每条含具体数字事实 + 来源 + 用在哪个环节
- sound_bites: 5-8 条口播金句（8-18字，朗朗上口）
- screenshot_lines: 3-5 条封面/字幕文字（≤14字）
- sources: 3-5 条信源（标题 + URL + 一句话要点）

**标题**（每个平台 2 个，直接能用）：
- douyin: 15字内
- xiaohongshu: 含 emoji
- gongzhonghao: 悬念感
- zhihu: 问题式
- bilibili: 口语化

返回严格 JSON（不要 markdown 代码块）：

{{
  "briefed_trends": [
    {{
      "topic": "话题",
      "score": 95,
      "direction": "rising",
      "category": "科技",
      "platforms": ["微博"],
      "summary": "概要",
      "product_relevance": "high",
      "brief": {{
        "product_tie_in": "产品与热点的真实连接（一句话说清楚）",
        "angles": [
          {{
            "name": "具体角度名（能当标题）",
            "description": "完整执行方案：第一步...第二步...产品出现在...",
            "product_role": "产品在此内容中的角色",
            "best_platform": "最适合平台",
            "appeal": "高/中/低"
          }}
        ],
        "outlines": {{
          "short_video": {{
            "hook": "完整的开头话术",
            "beats": [
              {{"content": "完整的口播内容（30-60字）", "visual": "画面描述"}},
              {{"content": "...", "visual": "..."}}
            ],
            "cta": "结尾引导语"
          }},
          "xiaohongshu": {{
            "cover_title": "封面大字 emoji",
            "slides": [
              {{"title": "第1页标题", "content": "正文内容", "image_note": "配图建议"}},
              {{"title": "...", "content": "...", "image_note": "..."}}
            ],
            "hashtags": ["#标签1", "#标签2"]
          }},
          "article": {{
            "title": "公众号标题",
            "sections": [
              {{"heading": "章节标题", "core_point": "核心论点2-3句", "evidence": "论据/数据", "product_mention": "产品植入点或null"}}
            ]
          }}
        }},
        "materials": {{
          "data_points": [{{"fact": "含数字的事实", "source": "来源", "how_to_use": "用在哪个环节"}}],
          "sound_bites": ["8-18字口播金句"],
          "screenshot_lines": ["≤14字封面/字幕文字"],
          "sources": [{{"title": "报道标题", "url": "链接", "takeaway": "一句话要点"}}]
        }},
        "titles": {{
          "douyin": ["标题1", "标题2"],
          "xiaohongshu": ["标题1", "标题2"],
          "gongzhonghao": ["标题1", "标题2"],
          "zhihu": ["标题1", "标题2"],
          "bilibili": ["标题1", "标题2"]
        }},
        "recommendation": {{
          "first_platform": "首发平台",
          "best_time": "最佳发布时间",
          "trending_window": "窗口期",
          "platform_priority": ["平台1", "平台2", "平台3"]
        }},
        "risk_notes": "风险提示（翻车风险、敏感点、法律风险）"
      }}
    }}
  ]
}}"""


def _build_context_block(trend: dict) -> str:
    """Build a real-world context block for the AI prompt from enrichment data."""
    ctx = trend.get("context")
    if not ctx or not isinstance(ctx, dict):
        return ""

    parts = []
    if ctx.get("background"):
        parts.append(f"背景：{ctx['background']}")

    for a in (ctx.get("articles") or [])[:5]:
        line = f"- [{a.get('source', '报道')}] {a.get('title', '')}"
        if a.get("summary"):
            line += f" — {a['summary']}"
        if a.get("url"):
            line += f" ({a['url']})"
        parts.append(line)

    for dp in (ctx.get("data_points") or [])[:5]:
        parts.append(f"- 数据：{dp}")

    for q in (ctx.get("quotes") or [])[:3]:
        parts.append(f"- 引用：「{q}」")

    if ctx.get("controversy"):
        parts.append(f"- 争议焦点：{ctx['controversy']}")

    if not parts:
        return ""
    return "\n".join(parts)


def _prepare_batch_for_prompt(batch: list[dict]) -> list[dict]:
    """Prepare batch data for AI prompt, including context blocks."""
    prepared = []
    for t in batch:
        entry = {k: v for k, v in t.items() if k != "context"}
        ctx_block = _build_context_block(t)
        if ctx_block:
            entry["real_world_context"] = ctx_block
        prepared.append(entry)
    return prepared


def process_batch(trends: list[dict], model: str, api_key: str, api_base: str = None,
                  batch_size: int = 5, profile: dict = None) -> list[dict]:
    """Process trends in batches. Always generates product x trend briefs."""
    sys_prompt = PRODUCT_BRIEF_SYSTEM
    user_template = PRODUCT_BRIEF_USER

    has_context = any(t.get("context") for t in trends)
    if has_context:
        sys_prompt += (
            "\n\n重要：部分话题附带了 real_world_context 字段，这是从真实报道中提取的背景、"
            "数据点、引用和信源 URL。你必须优先使用这些真实信息来生成素材（data_points、quotes、"
            "sources），不要编造。没有 context 的话题，用你的知识尽量给出具体信息。"
        )

    all_briefed = []

    for i in range(0, len(trends), batch_size):
        batch = trends[i:i + batch_size]
        batch_num = i // batch_size + 1
        total_batches = (len(trends) + batch_size - 1) // batch_size

        enriched_count = sum(1 for t in batch if t.get("context"))
        ctx_label = f", {enriched_count} enriched" if enriched_count else ""
        print(
            f"[content_brief] Batch {batch_num}/{total_batches} "
            f"({len(batch)} topics{ctx_label})...",
            file=sys.stderr
        )

        prepared = _prepare_batch_for_prompt(batch)
        trends_json = json.dumps(prepared, ensure_ascii=False, indent=None)
        profile_json = json.dumps(profile or {}, ensure_ascii=False, indent=None)
        user_prompt = (
            user_template
            .replace("{trends_json}", trends_json)
            .replace("{profile_json}", profile_json)
        )

        try:
            response_text = call_ai(sys_prompt, user_prompt, model, api_key, api_base)
            result = parse_ai_response(response_text)

            briefed = result.get("briefed_trends", result if isinstance(result, list) else [])
            if isinstance(briefed, list):
                all_briefed.extend(briefed)
            else:
                all_briefed.append(briefed)
        except Exception as e:
            print(f"[content_brief] Batch {batch_num} error: {e}", file=sys.stderr)
            for trend in batch:
                all_briefed.append({
                    **trend,
                    "brief": {"error": str(e)}
                })

    return all_briefed


def main():
    parser = base_argparser("Generate creative briefs for trending topics")
    parser.add_argument("--model", help="AI model (default: env AI_MODEL or deepseek/deepseek-chat)")
    parser.add_argument("--api-key", help="AI API key (default: env AI_API_KEY)")
    parser.add_argument("--api-base", help="AI API base URL (default: env AI_API_BASE)")
    parser.add_argument("--top", type=int, default=0, help="Only process top N trends (0=all)")
    parser.add_argument("--batch-size", type=int, default=2, help="Topics per AI call (default: 2)")
    parser.add_argument("--profile", help="Path to product profile JSON (enables product x trend mode)")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    model = args.model or os.environ.get("AI_MODEL", "deepseek/deepseek-chat")
    api_key = args.api_key or os.environ.get("AI_API_KEY", "")
    api_base = args.api_base or os.environ.get("AI_API_BASE", "")

    if not api_key:
        fail("AI_API_KEY not set. Export it or pass --api-key.")

    input_data = read_json_input(args)
    trends = input_data.get("trends", [])

    if not trends:
        fail("No trends provided. Pipe output from trend_analyze.")

    profile = input_data.get("profile", None)
    if args.profile:
        with open(args.profile, "r", encoding="utf-8") as f:
            profile_data = json.load(f)
            profile = profile_data.get("profile", profile_data)

    if args.top > 0:
        trends = trends[:args.top]

    effective_batch = 1 if profile else args.batch_size
    product_name = profile.get('name', 'Unknown') if profile else '(no profile)'
    print(f"[content_brief] {len(trends)} topics | batch={effective_batch} | product={product_name} | {model}", file=sys.stderr)

    briefed = process_batch(trends, model, api_key, api_base or None, effective_batch, profile)

    result = {"briefed_trends": briefed}

    print(f"[content_brief] Generated {len(briefed)} briefs", file=sys.stderr)

    write_json_output(result, args)


if __name__ == "__main__":
    main()
