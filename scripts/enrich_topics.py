#!/usr/bin/env python3
"""
enrich_topics — Enrich trend topics with real-world context from web search.

This tool does NOT search the web itself.
The Agent uses WebSearch/WebFetch/web-access to gather real articles, data, and URLs
for each topic, then pipes that context into this script to merge with trend data.

This solves the core quality problem: content_brief receives only bare titles from
collect_hotlist, so AI fabricates generic materials. By enriching trends with real
reporting BEFORE content_brief, the AI can produce specific, verifiable, high-quality
creative briefs with real data points, quotes, and source URLs.

Workflow:
  1. trend_analyze outputs topics (title + score + direction)
  2. Agent searches each topic via WebSearch/web-access, collects:
     - Article summaries, key data points, notable quotes
     - Source URLs, publication names
     - Related images/videos if available
  3. Agent pipes {trends, enrichments} into this script
  4. This script merges enrichment data into each trend object
  5. Enriched trends → content_brief → much higher quality output

Anti-hallucination: enrichment data must come from Agent's real search results.
This script only merges/normalizes — it never fabricates information.
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
    "name": "enrich_topics",
    "description": (
        "Merge real-world context (from Agent web search) into trend topics. "
        "Dramatically improves content_brief quality by giving AI real data, quotes, "
        "and source URLs instead of bare titles. Agent searches each topic first, "
        "then pipes results here."
    ),
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
            "enrichments": {
                "type": "array",
                "description": "Agent-collected context for each topic",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string", "description": "Must match a trend topic"},
                        "articles": {
                            "type": "array",
                            "description": "Real articles/reports found by Agent",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                    "source": {"type": "string", "description": "Publication name"},
                                    "summary": {"type": "string", "description": "Key takeaway from the article"},
                                    "date": {"type": "string"}
                                }
                            }
                        },
                        "data_points": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Specific numbers, statistics, facts found"
                        },
                        "quotes": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Notable quotes from people involved"
                        },
                        "background": {
                            "type": "string",
                            "description": "Brief background context (2-3 sentences)"
                        },
                        "controversy": {
                            "type": "string",
                            "description": "Main controversy or debate angle"
                        }
                    },
                    "required": ["topic"]
                }
            }
        },
        "required": ["trends", "enrichments"]
    },
    "output": {
        "type": "object",
        "properties": {
            "trends": {
                "type": "array",
                "description": "Enriched trends — same as input trends but with 'context' field added"
            },
            "enrichment_stats": {
                "type": "object",
                "properties": {
                    "total_topics": {"type": "integer"},
                    "enriched_topics": {"type": "integer"},
                    "total_articles": {"type": "integer"},
                    "total_data_points": {"type": "integer"}
                }
            }
        }
    },
    "examples": {
        "agent_workflow": "trend_analyze -o trends.json -> Agent WebSearches top 8 -> enrich_topics -o enriched.json -> content_brief -i enriched.json",
    },
}


def normalize_enrichment(raw: dict) -> dict:
    """Normalize a single enrichment entry."""
    articles = []
    for a in raw.get("articles", []):
        if not isinstance(a, dict):
            continue
        title = (a.get("title") or "").strip()
        if not title:
            continue
        articles.append({
            "title": title[:200],
            "url": (a.get("url") or a.get("link") or "").strip(),
            "source": (a.get("source") or a.get("publisher") or a.get("domain") or "").strip(),
            "summary": (a.get("summary") or a.get("takeaway") or a.get("snippet") or "").strip()[:500],
            "date": (a.get("date") or a.get("published") or "").strip(),
        })

    data_points = []
    for dp in raw.get("data_points", []):
        s = str(dp).strip()
        if s and len(s) >= 3:
            data_points.append(s[:300])

    quotes = []
    for q in raw.get("quotes", []):
        s = str(q).strip()
        if s and len(s) >= 5:
            quotes.append(s[:300])

    return {
        "articles": articles[:10],
        "data_points": data_points[:10],
        "quotes": quotes[:5],
        "background": (raw.get("background") or "").strip()[:800],
        "controversy": (raw.get("controversy") or "").strip()[:500],
    }


def merge_enrichments(trends: list[dict], enrichments: list[dict]) -> tuple[list[dict], dict]:
    """Merge enrichment data into trends. Returns (enriched_trends, stats)."""
    enrich_map = {}
    for e in enrichments:
        if not isinstance(e, dict):
            continue
        topic = (e.get("topic") or "").strip()
        if topic:
            enrich_map[topic] = normalize_enrichment(e)

    enriched = []
    stats = {"total_topics": len(trends), "enriched_topics": 0, "total_articles": 0, "total_data_points": 0}

    for trend in trends:
        topic = trend.get("topic", "").strip()
        ctx = enrich_map.get(topic)

        if not ctx:
            for key in enrich_map:
                if key in topic or topic in key:
                    ctx = enrich_map[key]
                    break

        if ctx and (ctx["articles"] or ctx["data_points"] or ctx["background"]):
            trend["context"] = ctx
            stats["enriched_topics"] += 1
            stats["total_articles"] += len(ctx["articles"])
            stats["total_data_points"] += len(ctx["data_points"])
        else:
            trend["context"] = None

        enriched.append(trend)

    return enriched, stats


def main():
    parser = base_argparser("Merge web search context into trend topics for richer content briefs")
    args = parser.parse_args()
    handle_schema(args, SCHEMA)

    input_data = read_json_input(args)
    trends = input_data.get("trends", [])
    enrichments = input_data.get("enrichments", [])

    if not trends:
        fail("No trends provided. Pipe output from trend_analyze.")

    if not enrichments:
        print("[enrich_topics] WARNING: No enrichments provided. Passing trends through unchanged.", file=sys.stderr)
        print("[enrich_topics] For better quality, Agent should WebSearch each topic and provide enrichments.", file=sys.stderr)
        write_json_output({"trends": trends, "enrichment_stats": {
            "total_topics": len(trends), "enriched_topics": 0, "total_articles": 0, "total_data_points": 0
        }}, args)
        return

    enriched, stats = merge_enrichments(trends, enrichments)
    print(
        f"[enrich_topics] {stats['enriched_topics']}/{stats['total_topics']} topics enriched, "
        f"{stats['total_articles']} articles, {stats['total_data_points']} data points",
        file=sys.stderr
    )

    write_json_output({"trends": enriched, "enrichment_stats": stats}, args)


if __name__ == "__main__":
    main()
