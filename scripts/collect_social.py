#!/usr/bin/env python3
"""
collect_social — Normalize social media data into Common Item Format.

This tool does NOT do any browser/CDP operations itself.
Browser scraping is handled by the **web-access** skill (or Agent directly).
This script only normalizes raw data into the standard hot-creator item format.

Workflow:
  1. Agent uses web-access skill (CDP) to browse xiaohongshu/douyin/weibo
  2. Agent extracts titles/urls from the page (via /eval or manual reading)
  3. Agent pipes the raw data into this script as JSON stdin
  4. This script normalizes it into Common Item Format for trend_analyze

Anti-hallucination: if no items are provided, output is empty — never fabricate data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from _common import (
    base_argparser, handle_schema, read_json_input, write_json_output,
    fail, platform_name
)

SCHEMA = {
    "name": "collect_social",
    "description": "Normalize social media data into Common Item Format. Does NOT browse — Agent uses web-access skill for CDP, then pipes raw data here.",
    "input": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "description": "Raw items from Agent's browser scraping. Each: {title, platform_id, url?, heat?, rank?}",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "platform_id": {"type": "string", "enum": ["xiaohongshu", "douyin", "weibo_rising", "bilibili", "zhihu"]},
                        "url": {"type": "string"},
                        "heat": {"type": "string"},
                        "rank": {"type": "integer"}
                    },
                    "required": ["title"]
                }
            },
            "platform_id": {
                "type": "string",
                "description": "Default platform_id if items don't specify one"
            }
        },
        "required": ["items"]
    },
    "output": {
        "type": "object",
        "properties": {
            "source": {"type": "string", "const": "social"},
            "items": {"type": "array", "description": "Normalized Common Item Format"},
            "errors": {"type": "array", "items": {"type": "string"}}
        }
    },
    "examples": {
        "agent_workflow": (
            'Agent uses web-access CDP to browse xiaohongshu, extracts titles, '
            'then: echo \'{"items":[{"title":"话题1","platform_id":"xiaohongshu"}]}\' '
            '| python scripts/collect_social.py -o output/social.json'
        ),
    },
    "errors": {
        "no_items": "stdin 中没有 items → Agent 需要先用 web-access 浏览页面并提取数据",
        "empty_after_filter": "所有 items 的 title 都为空或被过滤 → 检查 Agent 提取逻辑"
    }
}


def normalize_items(raw_items: list, default_platform_id: str = "") -> tuple[list[dict], list[str]]:
    """Normalize raw scraped items into Common Item Format. Returns (items, errors)."""
    items = []
    errors = []
    seen = set()

    for i, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            errors.append(f"Item {i}: not a dict, skipped")
            continue

        title = (raw.get("title") or "").strip()
        if not title or len(title) < 2:
            continue
        if len(title) > 300:
            title = title[:300]

        # Dedup
        if title in seen:
            continue
        seen.add(title)

        pid = raw.get("platform_id") or raw.get("platform") or default_platform_id or "unknown"
        pid_lower = pid.lower().replace(" ", "_")

        # Map Chinese names to platform_id
        cn_map = {"小红书": "xiaohongshu", "抖音": "douyin", "微博": "weibo_rising",
                   "微博上升": "weibo_rising", "b站": "bilibili", "知乎": "zhihu"}
        if pid_lower in cn_map.values():
            pass
        elif pid in cn_map:
            pid_lower = cn_map[pid]
        else:
            pid_lower = pid_lower

        items.append({
            "title": title,
            "platform": platform_name(pid_lower) if pid_lower != "unknown" else pid,
            "platform_id": pid_lower,
            "rank": raw.get("rank") or (len(items) + 1),
            "url": (raw.get("url") or "").strip(),
            "heat": str(raw.get("heat") or "").strip(),
        })

    return items, errors


def main():
    parser = base_argparser("Normalize social media data into Common Item Format")
    parser.add_argument("--platform-id", "-p", default="",
                        help="Default platform_id for items that don't specify one")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    input_data = read_json_input(args)
    raw_items = input_data.get("items", [])
    default_pid = args.platform_id or input_data.get("platform_id", "")

    if not raw_items:
        # Anti-hallucination: no data = empty output, never fabricate
        print("[collect_social] No items provided. Output is empty.", file=sys.stderr)
        write_json_output({"source": "social", "items": [], "errors": ["no_items_provided"]}, args)
        return

    items, errors = normalize_items(raw_items, default_pid)
    print(f"[collect_social] Normalized {len(items)} items from {len(raw_items)} raw entries", file=sys.stderr)

    write_json_output({"source": "social", "items": items, "errors": errors}, args)


if __name__ == "__main__":
    main()
