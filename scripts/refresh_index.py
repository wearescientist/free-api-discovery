#!/usr/bin/env python3
"""Build a local API discovery registry from public-api-lists and graphql-apis."""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from intent_router import CATEGORY_ALIASES, contains_alias


PUBLIC_API_LISTS_URL = "https://public-api-lists.github.io/public-api-lists/api/all.json"
GRAPHQL_APIS_URL = "https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/apis.json"
GRAPHQL_DEMOS_URL = "https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/demos.json"
GRAPHQL_PROXIES_URL = "https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/proxies.json"
USER_AGENT = "free-api-discovery/1.0"
SNAPSHOT_FILES = {
    "public-api-lists": "public-api-lists-all.json",
    "graphql-apis": "graphql-apis-apis.json",
    "graphql-demos": "graphql-apis-demos.json",
    "graphql-proxies": "graphql-apis-proxies.json",
}
DOMAIN_ALIASES = {category: aliases for category, aliases in CATEGORY_ALIASES.items() if category != "GraphQL"}


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def default_registry_path() -> Path:
    return skill_root() / "assets" / "registry.json"


def default_snapshot_dir() -> Path:
    return skill_root() / "assets" / "snapshots"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Refresh the local free API discovery registry.")
    parser.add_argument(
        "--prefer-snapshots",
        action="store_true",
        help="Build from local raw snapshots when they already exist.",
    )
    return parser.parse_args()


def fetch_json(url: str) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_or_load_json(url: str, snapshot_name: str, prefer_snapshot: bool = False) -> tuple[Any, str, Path]:
    snapshot_path = default_snapshot_dir() / snapshot_name
    if prefer_snapshot and snapshot_path.exists():
        return load_json(snapshot_path), "snapshot", snapshot_path
    try:
        payload = fetch_json(url)
        write_json(snapshot_path, payload)
        return payload, "remote", snapshot_path
    except Exception:
        if snapshot_path.exists():
            return load_json(snapshot_path), "snapshot-fallback", snapshot_path
        raise


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return value.strip("-") or "entry"


def unique_list(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def infer_domain_tags(*parts: str) -> list[str]:
    text = " ".join(str(part or "") for part in parts).lower()
    tags = []
    for category, aliases in DOMAIN_ALIASES.items():
        if any(contains_alias(text, alias) for alias in aliases):
            tags.append(category)
    return unique_list(tags)


def count_entries_by_key(entries: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for entry in entries:
        values = entry.get(field_name) or []
        if not isinstance(values, list):
            values = [values]
        for value in values:
            key = str(value or "").strip()
            if not key:
                continue
            counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def normalize_public_api_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = []
    for row in payload.get("entries", []):
        name = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        description = str(row.get("description") or "").strip()
        category = str(row.get("category") or "").strip() or "Uncategorized"
        auth = str(row.get("auth") or "").strip() or "Unknown"
        cors = str(row.get("cors") or "").strip() or "Unknown"
        if not name or not url:
            continue
        entries.append(
            {
                "id": f"public-api-lists:{slugify(name)}:{slugify(category)}",
                "source": "public-api-lists",
                "source_kind": "rest",
                "type": "rest",
                "graphql": False,
                "primary_category": category,
                "categories": [category],
                "name": name,
                "url": url,
                "description": description,
                "auth": auth,
                "https": bool(row.get("https")),
                "cors": cors,
                "category": category,
                "docs": [url],
            }
        )
    return entries


def graphql_auth(entry: dict[str, Any]) -> str:
    rules = entry.get("security") or []
    if not rules:
        return "Unknown"
    parts = []
    for item in rules:
        title = str(item.get("title") or item.get("type") or "").strip()
        location = str(item.get("in") or "").strip()
        prefix = str(item.get("prefix") or "").strip()
        bit = " ".join(part for part in [title, location, prefix] if part).strip()
        if bit:
            parts.append(bit)
    return "; ".join(parts) if parts else "Unknown"


def normalize_graphql_entries(payload: list[dict[str, Any]], source_kind: str) -> list[dict[str, Any]]:
    entries = []
    for row in payload:
        info = row.get("info") or {}
        name = str(info.get("title") or row.get("url") or "").strip()
        url = str(row.get("url") or "").strip()
        description = str(info.get("description") or "").strip()
        docs = []
        for item in row.get("externalDocs") or []:
            doc_url = str(item.get("url") or "").strip()
            if doc_url:
                docs.append(doc_url)
        if not name or not url:
            continue
        domain_tags = infer_domain_tags(name, description, url, " ".join(docs))
        entries.append(
            {
                "id": f"graphql-apis:{source_kind}:{slugify(name)}",
                "source": "graphql-apis",
                "source_kind": source_kind,
                "type": "graphql",
                "graphql": True,
                "primary_category": "GraphQL",
                "categories": unique_list(["GraphQL"] + domain_tags),
                "name": name,
                "url": url,
                "description": description,
                "auth": graphql_auth(row),
                "https": url.startswith("https://"),
                "cors": "Unknown",
                "category": "GraphQL",
                "docs": docs or [url],
            }
        )
    return entries


def build_registry(registry_path: Path | None = None, prefer_snapshot: bool = False) -> dict[str, Any]:
    registry_path = registry_path or default_registry_path()
    public_payload, public_mode, public_snapshot = fetch_or_load_json(
        PUBLIC_API_LISTS_URL,
        SNAPSHOT_FILES["public-api-lists"],
        prefer_snapshot=prefer_snapshot,
    )
    graphql_apis, graphql_apis_mode, graphql_apis_snapshot = fetch_or_load_json(
        GRAPHQL_APIS_URL,
        SNAPSHOT_FILES["graphql-apis"],
        prefer_snapshot=prefer_snapshot,
    )
    graphql_demos, graphql_demos_mode, graphql_demos_snapshot = fetch_or_load_json(
        GRAPHQL_DEMOS_URL,
        SNAPSHOT_FILES["graphql-demos"],
        prefer_snapshot=prefer_snapshot,
    )
    graphql_proxies, graphql_proxies_mode, graphql_proxies_snapshot = fetch_or_load_json(
        GRAPHQL_PROXIES_URL,
        SNAPSHOT_FILES["graphql-proxies"],
        prefer_snapshot=prefer_snapshot,
    )

    entries = []
    entries.extend(normalize_public_api_entries(public_payload))
    entries.extend(normalize_graphql_entries(graphql_apis, "apis"))
    entries.extend(normalize_graphql_entries(graphql_demos, "demos"))
    entries.extend(normalize_graphql_entries(graphql_proxies, "proxies"))

    registry = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sources": {
            "public-api-lists": {
                "url": PUBLIC_API_LISTS_URL,
                "mode": public_mode,
                "snapshot": str(public_snapshot),
                "count": len([entry for entry in entries if entry["source"] == "public-api-lists"]),
            },
            "graphql-apis": {
                "urls": [GRAPHQL_APIS_URL, GRAPHQL_DEMOS_URL, GRAPHQL_PROXIES_URL],
                "modes": {
                    "apis": graphql_apis_mode,
                    "demos": graphql_demos_mode,
                    "proxies": graphql_proxies_mode,
                },
                "snapshots": {
                    "apis": str(graphql_apis_snapshot),
                    "demos": str(graphql_demos_snapshot),
                    "proxies": str(graphql_proxies_snapshot),
                },
                "count": len([entry for entry in entries if entry["source"] == "graphql-apis"]),
            },
        },
        "primary_category_counts": count_entries_by_key(entries, "primary_category"),
        "category_counts": count_entries_by_key(entries, "categories"),
        "entry_count": len(entries),
        "entries": entries,
    }

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    return registry


def main() -> None:
    args = parse_args()
    registry = build_registry(prefer_snapshot=args.prefer_snapshots)
    print(
        json.dumps(
            {
                "registry_path": str(default_registry_path()),
                "snapshot_dir": str(default_snapshot_dir()),
                "generated_at": registry["generated_at"],
                "entry_count": registry["entry_count"],
                "sources": registry["sources"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
