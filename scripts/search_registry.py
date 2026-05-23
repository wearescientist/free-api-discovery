#!/usr/bin/env python3
"""Search the local free API registry with natural-language queries."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from intent_router import CATEGORY_ALIASES, GRAPHQL_TERMS, NO_AUTH_TERMS, STOP_TOKENS, contains_alias, detect_categories, significant_tokens, tokenize
from refresh_index import build_registry, default_registry_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search the local free API registry.")
    parser.add_argument("--query", help="Natural-language search query.")
    parser.add_argument("--top", type=int, default=8, help="Maximum number of results to return.")
    parser.add_argument("--refresh", action="store_true", help="Force-refresh the registry before searching.")
    parser.add_argument("--list-categories", action="store_true", help="Print category counts from the local registry.")
    parser.add_argument("--primary-only", action="store_true", help="Only print primary category counts when listing categories.")
    args = parser.parse_args()
    if not args.query and not args.list_categories:
        parser.error("either --query or --list-categories is required")
    return args


def load_registry(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def wants_graphql(query: str) -> bool:
    query_lower = query.lower()
    return any(contains_alias(query_lower, term) for term in GRAPHQL_TERMS)


def prefers_no_auth(query: str) -> bool:
    query_lower = query.lower()
    return any(contains_alias(query_lower, term) for term in NO_AUTH_TERMS)


def category_list(entry: dict[str, Any]) -> list[str]:
    values = entry.get("categories") or []
    if isinstance(values, list) and values:
        return [str(value).strip() for value in values if str(value).strip()]
    fallback = str(entry.get("primary_category") or entry.get("category") or "").strip()
    return [fallback] if fallback else []


def source_kind_adjustment(entry: dict[str, Any]) -> int:
    if entry.get("source") != "graphql-apis":
        return 0
    kind = str(entry.get("source_kind") or "")
    if kind == "apis":
        return 6
    if kind == "proxies":
        return 2
    if kind == "demos":
        return -6
    return 0


def score_entry(
    entry: dict[str, Any],
    tokens: list[str],
    categories: list[str],
    graphql_only: bool,
    no_auth_only: bool,
) -> dict[str, Any]:
    score = 0
    reasons = []
    primary_category = str(entry.get("primary_category") or entry.get("category") or "").strip()
    categories_text = " ".join(category_list(entry))
    haystacks = {
        "name": str(entry.get("name") or "").lower(),
        "description": str(entry.get("description") or "").lower(),
        "category": categories_text.lower(),
        "primary_category": primary_category.lower(),
        "url": str(entry.get("url") or "").lower(),
        "auth": str(entry.get("auth") or "").lower(),
        "docs": " ".join(str(item).lower() for item in entry.get("docs") or []),
    }
    combined_text = " ".join(haystacks.values())

    if graphql_only:
        if entry.get("graphql"):
            score += 45
            reasons.append("graphql-match")
        else:
            score -= 20

    if no_auth_only:
        if haystacks["auth"] == "no":
            score += 30
            reasons.append("no-auth")
        else:
            score -= 10
    elif haystacks["auth"] == "no":
        score += 6
        reasons.append("no-auth-preferred")

    for category in categories:
        category_lower = category.lower()
        if category_lower == haystacks["primary_category"]:
            score += 30
            reasons.append(f"category:{category}")
        elif category_lower in haystacks["category"]:
            score += 22
            reasons.append(f"facet:{category}")
        elif any(contains_alias(combined_text, alias) for alias in CATEGORY_ALIASES.get(category, [])):
            score += 16
            reasons.append(f"theme:{category}")

    requested_domain_categories = [category for category in categories if category != "GraphQL"]
    if graphql_only and requested_domain_categories and haystacks["primary_category"] == "graphql" and len(category_list(entry)) == 1:
        score -= 5

    for token in tokens:
        if len(token) < 2 or token in STOP_TOKENS:
            continue
        if token in haystacks["name"]:
            score += 12
            reasons.append(f"name:{token}")
        if token in haystacks["category"]:
            score += 8
        if token in haystacks["description"]:
            score += 5
        if token in haystacks["url"] or token in haystacks["docs"]:
            score += 2

    if entry.get("source") == "graphql-apis":
        score += 2
    if entry.get("source") == "public-api-lists":
        score += 1
    if entry.get("https"):
        score += 1
    score += source_kind_adjustment(entry)

    return {"score": score, "reasons": sorted(set(reasons))}


def shortlist(query: str, registry: dict[str, Any], top: int) -> dict[str, Any]:
    categories = detect_categories(query)
    tokens = significant_tokens(query)
    graphql_only = wants_graphql(query)
    no_auth_only = prefers_no_auth(query)

    ranked = []
    for entry in registry.get("entries", []):
        scored = score_entry(entry, tokens, categories, graphql_only, no_auth_only)
        if scored["score"] <= 0:
            continue
        ranked.append(
            {
                "score": scored["score"],
                "why": scored["reasons"],
                "name": entry.get("name"),
                "primary_category": entry.get("primary_category", entry.get("category")),
                "categories": category_list(entry),
                "category": entry.get("category"),
                "description": entry.get("description"),
                "auth": entry.get("auth"),
                "type": entry.get("type"),
                "graphql": entry.get("graphql"),
                "url": entry.get("url"),
                "docs": entry.get("docs"),
                "source": entry.get("source"),
                "source_kind": entry.get("source_kind"),
            }
        )

    ranked.sort(
        key=lambda item: (
            -item["score"],
            item["auth"] != "No",
            item["source"] != "public-api-lists",
            item["name"].lower(),
        )
    )

    return {
        "query": query,
        "matched_categories": categories,
        "prefer_no_auth": no_auth_only,
        "prefer_graphql": graphql_only,
        "result_count": min(len(ranked), top),
        "results": ranked[:top],
    }


def list_categories(registry: dict[str, Any], primary_only: bool = False) -> dict[str, Any]:
    return {
        "generated_at": registry.get("generated_at"),
        "entry_count": registry.get("entry_count"),
        "primary_categories": registry.get("primary_category_counts", {}),
        "all_categories": {} if primary_only else registry.get("category_counts", {}),
        "sources": registry.get("sources", {}),
    }


def main() -> None:
    args = parse_args()
    registry_path = default_registry_path()
    if args.refresh or not registry_path.exists():
        registry = build_registry(registry_path)
    else:
        registry = load_registry(registry_path)
    if args.list_categories:
        print(json.dumps(list_categories(registry, primary_only=args.primary_only), ensure_ascii=False, indent=2))
        return
    result = shortlist(str(args.query), registry, max(1, args.top))
    result["registry_path"] = str(registry_path)
    result["generated_at"] = registry.get("generated_at")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
