#!/usr/bin/env python3
"""
monitor_competitor — Normalize competitor content data into structured format.

This tool does NOT do any browser/CDP operations itself.
Browser scraping is handled by the **web-access** skill (or Agent directly).
This script only normalizes raw competitor data that the Agent has collected.

Workflow:
  1. Agent uses web-access skill (CDP) to browse competitor pages
  2. Agent extracts post titles/urls/engagement from the page
  3. Agent pipes the raw data into this script as JSON stdin
  4. This script normalizes it into structured competitor format for industry_insight

Anti-hallucination: if no data is provided, output is empty — never fabricate data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import json
from _common import (
    base_argparser, handle_schema, read_json_input, write_json_output,
    fail
)

SCHEMA = {
    "name": "monitor_competitor",
    "description": "Normalize competitor content data into structured format. Does NOT browse — Agent uses web-access skill for CDP, then pipes raw data here.",
    "input": {
        "type": "object",
        "properties": {
            "competitors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Competitor name"},
                        "platform": {"type": "string", "description": "Platform name (小红书/微博/抖音/微信公众号)"},
                        "posts": {
                            "type": "array",
                            "description": "Raw posts from Agent's browser scraping",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "content_preview": {"type": "string"},
                                    "engagement": {"type": "string"},
                                    "date": {"type": "string"}
                                }
                            }
                        },
                        "themes": {"type": "array", "items": {"type": "string"}},
                        "content_frequency": {"type": "string"}
                    },
                    "required": ["name"]
                },
                "description": "List of competitors with their scraped data"
            }
        },
        "required": ["competitors"]
    },
    "output": {
        "type": "object",
        "properties": {
            "competitor_data": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "platform": {"type": "string"},
                        "posts": {"type": "array"},
                        "themes": {"type": "array", "items": {"type": "string"}},
                        "content_frequency": {"type": "string"}
                    }
                }
            },
            "errors": {"type": "array", "items": {"type": "string"}}
        }
    },
    "examples": {
        "agent_workflow": (
            'Agent uses web-access CDP to browse competitor Xiaohongshu pages, '
            'extracts posts, then: echo \'{"competitors":[{"name":"竞品A","platform":"小红书",'
            '"posts":[{"title":"标题1","url":"...","engagement":"1.2万"}]}]}\' '
            '| python scripts/monitor_competitor.py -o output/comp.json'
        ),
    },
    "errors": {
        "no_competitors": "stdin 中没有 competitors → Agent 需要先用 web-access 浏览竞品页面并提取数据",
        "empty_posts": "竞品没有 posts 数据 → Agent 需要从浏览器中提取内容"
    }
}


def normalize_post(raw: dict) -> dict:
    """Normalize a single post entry."""
    return {
        "title": (raw.get("title") or "").strip()[:200],
        "content_preview": (raw.get("content_preview") or raw.get("summary") or "").strip()[:500],
        "url": (raw.get("url") or raw.get("link") or "").strip(),
        "engagement": str(raw.get("engagement") or raw.get("likes") or "").strip(),
        "date": (raw.get("date") or raw.get("published_at") or "").strip(),
    }


def normalize_competitor(comp: dict) -> tuple[dict, list[str]]:
    """Normalize a single competitor entry. Returns (normalized, errors)."""
    errors = []
    name = (comp.get("name") or "Unknown").strip()
    platform = (comp.get("platform") or "").strip()

    raw_posts = comp.get("posts", [])
    if not isinstance(raw_posts, list):
        errors.append(f"{name}: posts is not a list")
        raw_posts = []

    posts = []
    for p in raw_posts:
        if isinstance(p, dict):
            norm = normalize_post(p)
            if norm["title"]:
                posts.append(norm)
        elif isinstance(p, str) and p.strip():
            posts.append({"title": p.strip(), "content_preview": "", "url": "", "engagement": "", "date": ""})

    themes = comp.get("themes", [])
    if not isinstance(themes, list):
        themes = []
    themes = [str(t).strip() for t in themes if t]

    return {
        "name": name,
        "platform": platform,
        "posts": posts,
        "themes": themes,
        "content_frequency": str(comp.get("content_frequency") or "").strip(),
    }, errors


def main():
    parser = base_argparser("Normalize competitor content data into structured format")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    input_data = read_json_input(args)
    competitors = input_data.get("competitors", [])

    if not competitors:
        print("[monitor_competitor] No competitors provided. Output is empty.", file=sys.stderr)
        write_json_output({"competitor_data": [], "errors": ["no_competitors_provided"]}, args)
        return

    all_data = []
    all_errors = []

    for comp in competitors:
        if not isinstance(comp, dict):
            all_errors.append(f"Invalid competitor entry: {comp}")
            continue
        data, errs = normalize_competitor(comp)
        all_data.append(data)
        all_errors.extend(errs)
        post_count = len(data["posts"])
        print(f"[monitor_competitor] {data['name']} ({data['platform']}): {post_count} posts", file=sys.stderr)

    write_json_output({"competitor_data": all_data, "errors": all_errors}, args)


if __name__ == "__main__":
    main()
