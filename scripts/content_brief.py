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
    fail, SKILL_ROOT
)

try:
    import litellm
except ImportError:
    fail("litellm not installed. Run: pip install -r requirements.txt")

SCHEMA = {
    "name": "content_brief",
    "description": "Generate creative briefs per trend topic. Pass --profile for product x trend mode. CLI needs AI_API_KEY; Agent-native: Agent generates briefs directly.",
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
        "cli_generic": "python scripts/content_brief.py -i trends.json --top 15 -o output/briefs.json",
        "cli_product": "python scripts/content_brief.py -i trends.json --profile profile.json --top 10 -o briefs.json",
        "agent_native": "Agent reads trends JSON + prompt-templates.md#content_brief, generates briefs in dialogue"
    },
    "errors": {
        "no_api_key": "AI_API_KEY 未设置 → Agent 原生模式不需要",
        "no_trends": "无 trends 输入 → 先运行 trend_analyze",
        "batch_error": "单个 batch AI 调用失败 → 该 batch 话题标记 error，继续处理其他 batch"
    }
}


def load_brief_prompt() -> tuple[str, str]:
    """Load content_brief prompts from reference/prompt-templates.md."""
    tmpl_path = SKILL_ROOT / "reference" / "prompt-templates.md"

    default_sys = "你是一个全平台内容策划专家，服务过大量头部创作者。你的建议实操性强，不说空话。"
    default_user = "请为以下热点话题生成完整创作简报，返回 JSON 格式。\n\n{trends_json}"

    if not tmpl_path.exists():
        return default_sys, default_user

    content = tmpl_path.read_text(encoding="utf-8")

    sys_prompt = ""
    user_prompt = ""

    in_section = False
    in_code = False
    code_lines = []
    last_heading = ""

    for line in content.split("\n"):
        if not in_code:
            if line.startswith("## ") and "content_brief" in line:
                in_section = True
                continue
            if in_section and line.startswith("## ") and "content_brief" not in line:
                break

        if in_section:
            if not in_code and "### " in line:
                last_heading = line.strip().lower()
                continue

            if line.strip().startswith("```") and not in_code:
                in_code = True
                code_lines = []
                continue
            elif line.strip().startswith("```") and in_code:
                in_code = False
                block = "\n".join(code_lines)
                if "system" in last_heading and block.strip():
                    sys_prompt = block
                elif "{trends_json}" in block:
                    user_prompt = block
                continue
            if in_code:
                code_lines.append(line)

    if not sys_prompt:
        sys_prompt = default_sys
    if not user_prompt:
        user_prompt = default_user

    return sys_prompt, user_prompt


def call_ai(system_prompt: str, user_prompt: str, model: str, api_key: str, api_base: str = None,
            batch_size: int = 1) -> str:
    """Call AI model via litellm."""
    max_tokens = max(16000, min(64000, 16000 * batch_size))
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


def _try_fix_truncated_json(text: str) -> dict | None:
    """Attempt to fix truncated JSON by closing open brackets/braces."""
    import re
    for trim in range(min(200, len(text)), 0, -1):
        candidate = text[:len(text) - trim + 1]
        last_bracket = max(candidate.rfind('}'), candidate.rfind(']'))
        if last_bracket < 0:
            continue
        candidate = candidate[:last_bracket + 1]
        opens = candidate.count('{') - candidate.count('}')
        open_arr = candidate.count('[') - candidate.count(']')
        candidate += ']' * open_arr + '}' * opens
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue
    return None


def parse_ai_response(text: str) -> dict:
    """Parse AI response, handling markdown code fences, truncation, and various key names."""
    import re
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)

    result = None
    try:
        result = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                result = json.loads(match.group())
            except json.JSONDecodeError:
                result = _try_fix_truncated_json(match.group())
        if result is None:
            result = _try_fix_truncated_json(cleaned)
        if result is None:
            raise json.JSONDecodeError("Cannot parse AI response after all fallbacks", cleaned, 0)

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


PRODUCT_BRIEF_SYSTEM = """你是一个品牌内容策略师。你的工作是帮产品找到与热点之间的「真实连接」，而不是把产品硬塞进每个热点里。

你的判断标准：
- 如果一个热点跟这个产品没关系，就直说「关联弱，不建议硬蹭」，给 product_relevance: low
- 如果有关系，要说清楚关系到底是什么——是用户群体重叠？是解决了同一个痛点？是行业上下游？
- 结合方式必须让用户看完觉得「哦这确实有关系」，而不是「这也太牵强了」

你绝不做的事：
- 不编造产品没有的功能来凑热点
- 不在每个热点里都提产品名——有些热点用「行业视角」比「产品视角」更合适
- 不写「可以结合XX」这种废话——要写就写具体怎么结合、具体说什么话"""

PRODUCT_BRIEF_USER = """## 我的产品

{profile_json}

## 当前热点

{trends_json}

## 你的任务

先判断每个热点跟我的产品有没有「真实连接」：
- **high**: 产品直接相关（用户群体重叠/解决同一痛点/行业直接相关）→ 深入做
- **medium**: 有间接关系（可以从行业角度/用户场景角度切入）→ 选择性做
- **low**: 没什么关系 → 简单标注，不硬蹭

对 high/medium 的话题：
1. **结合点**：产品和这个热点的真实关系是什么（不是「都跟XX有关」这种废话）
2. **角度**（1-2个深入的）：产品在这个角度里自然出现，不是硬塞
3. **大纲**：只写最合适的形式，产品出现要自然（不是每句话都提）
4. **素材**：产品相关的真实数据 + 热点相关素材
5. **标题**：每平台 2 个
6. **风险**：这个结合有没有翻车风险

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
      "product_relevance": "high/medium/low",
      "brief": {{
        "product_tie_in": "真实的结合点（low 的写「关联较弱，不建议硬蹭」）",
        "angles": [
          {{
            "name": "具体角度",
            "description": "怎么做，产品怎么自然出现",
            "product_role": "产品的角色",
            "best_platform": "平台",
            "appeal": "高/中/低"
          }}
        ],
        "outlines": {{
          "short_video": {{"hook": "", "beats": [{{"content": "", "visual": ""}}], "cta": ""}},
          "xiaohongshu": {{"cover_title": "", "slides": [], "hashtags": []}},
          "article": {{"title": "", "sections": [{{"heading": "", "core_point": ""}}]}}
        }},
        "materials": {{
          "data_points": [{{"fact": "", "source": "", "how_to_use": ""}}],
          "sound_bites": [],
          "sources": [{{"title": "", "url": "", "takeaway": ""}}]
        }},
        "titles": {{"douyin": [], "xiaohongshu": [], "gongzhonghao": [], "zhihu": [], "bilibili": []}},
        "recommendation": {{"first_platform": "", "best_time": "", "trending_window": "", "platform_priority": []}},
        "risk_notes": "风险提示"
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
    """Process trends in batches. If profile is provided, generates product x trend briefs."""
    if profile:
        sys_prompt = PRODUCT_BRIEF_SYSTEM
        user_template = PRODUCT_BRIEF_USER
    else:
        sys_prompt, user_template = load_brief_prompt()

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
        mode_label = "product x trend" if profile else "generic"
        ctx_label = f", {enriched_count} enriched" if enriched_count else ""
        print(
            f"[content_brief] Batch {batch_num}/{total_batches} "
            f"({len(batch)} topics{ctx_label}, {mode_label})...",
            file=sys.stderr
        )

        prepared = _prepare_batch_for_prompt(batch)
        trends_json = json.dumps(prepared, ensure_ascii=False, indent=None)

        if profile:
            profile_json = json.dumps(profile, ensure_ascii=False, indent=None)
            user_prompt = (
                user_template
                .replace("{trends_json}", trends_json)
                .replace("{profile_json}", profile_json)
            )
        else:
            user_prompt = user_template.replace("{trends_json}", trends_json)

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

    mode = "product x trend" if profile else "generic"
    print(f"[content_brief] Mode: {mode} | {len(trends)} topics | {model}", file=sys.stderr)
    if profile:
        print(f"[content_brief] Product: {profile.get('name', 'Unknown')}", file=sys.stderr)

    briefed = process_batch(trends, model, api_key, api_base or None, args.batch_size, profile)

    result = {"briefed_trends": briefed}

    print(f"[content_brief] Generated {len(briefed)} briefs", file=sys.stderr)

    write_json_output(result, args)


if __name__ == "__main__":
    main()
