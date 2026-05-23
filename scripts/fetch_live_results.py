#!/usr/bin/env python3
"""Route natural-language requests to source pools, then aggregate direct results."""

from __future__ import annotations

import argparse
import html
import http.client
import json
import re
import time
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from intent_router import contains_alias, detect_intent, domain_terms
from refresh_index import USER_AGENT, build_registry, default_registry_path
from search_registry import load_registry, shortlist


OKSURF_NEWS_FEED_URL = "https://ok.surf/api/v1/news-feed"
COINDESK_RSS_URL = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS_URL = "https://cointelegraph.com/rss"
THEBLOCK_RSS_URL = "https://www.theblock.co/rss.xml"
DECRYPT_RSS_URL = "https://decrypt.co/feed"
BBC_WORLD_RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"
NPR_TOP_RSS_URL = "https://www.npr.org/rss/rss.php?id=1001"
NPR_BUSINESS_RSS_URL = "https://www.npr.org/rss/rss.php?id=1006"
NYT_TOP_RSS_URL = "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
NYT_BUSINESS_RSS_URL = "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml"
COINPAPRIKA_GLOBAL_URL = "https://api.coinpaprika.com/v1/global"
COINPAPRIKA_TICKERS_URL = "https://api.coinpaprika.com/v1/tickers"
COINPAPRIKA_SEARCH_URL = "https://api.coinpaprika.com/v1/search"
COINLORE_TICKERS_URL = "https://api.coinlore.net/api/tickers/"
COINRANKING_COINS_URL = "https://api.coinranking.com/v2/coins"
BLOCKCHAIN_STATS_URL = "https://api.blockchain.info/stats"
GATEIO_TICKER_URL = "https://api.gateio.ws/api/v4/spot/tickers"
GEMINI_TICKER_URL = "https://api.gemini.com/v1/pubticker"
VALUERAY_MARKET_REGIME_URL = "https://www.valueray.com/api/v1/marketRegime"
VALUERAY_SYMBOL_DATA_URL = "https://www.valueray.com/api/v1/symbolData"
PREDSCOPE_MARKETS_URL = "https://predscope.com/api/markets.json"
STATS_WORLD_COUNTRY_URL = "https://statisticsoftheworld.com/api/v1/countries"
STOOQ_SYMBOL_URL = "https://stooq.com/q/l/"
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
TRANSLATE_TEXT_LIMIT = 900

GENERIC_QUERY_TERMS = {
    "api",
    "apis",
    "news",
    "latest",
    "today",
    "crypto",
    "market",
    "markets",
    "finance",
    "financial",
    "stock",
    "stocks",
    "token",
    "tokens",
    "coin",
    "coins",
    "price",
    "prices",
    "headlines",
    "headline",
    "data",
}

COIN_ALIASES = {
    "btc": ("btc-bitcoin", "Bitcoin", "BTC"),
    "bitcoin": ("btc-bitcoin", "Bitcoin", "BTC"),
    "\u6bd4\u7279\u5e01": ("btc-bitcoin", "Bitcoin", "BTC"),
    "eth": ("eth-ethereum", "Ethereum", "ETH"),
    "ethereum": ("eth-ethereum", "Ethereum", "ETH"),
    "\u4ee5\u592a\u574a": ("eth-ethereum", "Ethereum", "ETH"),
    "sol": ("sol-solana", "Solana", "SOL"),
    "solana": ("sol-solana", "Solana", "SOL"),
    "bnb": ("bnb-binance-coin", "BNB", "BNB"),
    "xrp": ("xrp-xrp", "XRP", "XRP"),
    "doge": ("doge-dogecoin", "Dogecoin", "DOGE"),
    "dogecoin": ("doge-dogecoin", "Dogecoin", "DOGE"),
    "sui": ("sui-sui", "Sui", "SUI"),
    "trx": ("trx-tron", "TRON", "TRX"),
    "tron": ("trx-tron", "TRON", "TRX"),
    "ton": ("ton-toncoin", "Toncoin", "TON"),
    "toncoin": ("ton-toncoin", "Toncoin", "TON"),
    "ada": ("ada-cardano", "Cardano", "ADA"),
    "cardano": ("ada-cardano", "Cardano", "ADA"),
}

COINRANKING_UUIDS = {
    "BTC": "Qwsogvtv82FCd",
    "ETH": "razxDUgYGNAdQ",
    "BNB": "WcwrkfNI4FUAe",
    "USDT": "HIVsRcGKkPFtW",
    "XRP": "-l8Mn2pVlRs-p",
    "SOL": "zNZHO_Sjf",
    "DOGE": "a91GCGd_u96cF",
    "ADA": "qzawljRxB5bYu",
}

GATEIO_SYMBOLS = {
    "BTC": "BTC_USDT",
    "ETH": "ETH_USDT",
    "BNB": "BNB_USDT",
    "XRP": "XRP_USDT",
    "SOL": "SOL_USDT",
    "DOGE": "DOGE_USDT",
}

GEMINI_SYMBOLS = {
    "BTC": "btcusd",
    "ETH": "ethusd",
    "DOGE": "dogeusd",
    "SOL": "solusd",
    "LINK": "linkusd",
}

STOCK_ALIASES = {
    "aapl": "AAPL",
    "apple": "AAPL",
    "\u82f9\u679c": "AAPL",
    "msft": "MSFT",
    "microsoft": "MSFT",
    "\u5fae\u8f6f": "MSFT",
    "nvda": "NVDA",
    "nvidia": "NVDA",
    "\u82f1\u4f1f\u8fbe": "NVDA",
    "tsla": "TSLA",
    "tesla": "TSLA",
    "\u7279\u65af\u62c9": "TSLA",
    "amzn": "AMZN",
    "amazon": "AMZN",
    "\u4e9a\u9a6c\u900a": "AMZN",
    "googl": "GOOGL",
    "goog": "GOOG",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "\u8c37\u6b4c": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "\u8138\u4e66": "META",
    "spy": "SPY",
    "qqq": "QQQ",
    "dia": "DIA",
    "tsm": "TSM",
    "\u53f0\u79ef\u7535": "TSM",
}

SYMBOL_DISPLAY_NAMES = {
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "GOOGL": "Google",
    "META": "Meta",
    "TSM": "TSMC",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "SOL": "Solana",
    "BNB": "BNB",
    "DOGE": "Dogecoin",
    "XRP": "XRP",
}

COUNTRY_ALIASES = {
    "usa": "USA",
    "us": "USA",
    "united states": "USA",
    "\u7f8e\u56fd": "USA",
    "china": "CHN",
    "\u4e2d\u56fd": "CHN",
    "japan": "JPN",
    "\u65e5\u672c": "JPN",
    "uk": "GBR",
    "united kingdom": "GBR",
    "britain": "GBR",
    "\u82f1\u56fd": "GBR",
    "eu": "EMU",
    "eurozone": "EMU",
    "\u6b27\u5143\u533a": "EMU",
    "india": "IND",
    "\u5370\u5ea6": "IND",
}

MACRO_HINTS = {
    "gdp": ["gdp", "\u56fd\u5185\u751f\u4ea7\u603b\u503c"],
    "inflation": ["inflation", "cpi", "\u901a\u80c0", "\u901a\u8d27\u81a8\u80c0"],
    "unemployment": ["unemployment", "\u5931\u4e1a"],
    "population": ["population", "\u4eba\u53e3"],
    "rate": ["rate", "yield", "interest", "\u5229\u7387", "\u6536\u76ca\u7387"],
    "debt": ["debt", "\u503a\u52a1"],
    "stock": ["stock", "stocks", "\u80a1\u5e02", "\u80a1\u7968", "\u7f8e\u80a1"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch live results or discover APIs from a natural-language query.")
    parser.add_argument("--query", required=True, help="Natural-language request.")
    parser.add_argument("--top", type=int, default=8, help="Maximum number of results to return.")
    parser.add_argument("--refresh", action="store_true", help="Force-refresh the local registry before routing.")
    parser.add_argument("--mode", choices=["auto", "fetch", "discover"], default="auto", help="Override routing mode.")
    return parser.parse_args()


def read_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                try:
                    return response.read()
                except http.client.IncompleteRead as exc:
                    return exc.partial
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < 2:
                time.sleep(0.8 * (attempt + 1))
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError, http.client.RemoteDisconnected) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(0.4 * (attempt + 1))
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError(f"Failed to read bytes from {url}")


def read_json(url: str) -> Any:
    return json.loads(read_bytes(url).decode("utf-8"))


def read_text(url: str) -> str:
    return read_bytes(url).decode("utf-8", errors="replace")


def strip_html(value: Any) -> str:
    text = html.unescape(re.sub(r"<[^>]+>", " ", str(value or "")))
    return re.sub(r"\s+", " ", text).strip()


def truncate_text(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    clipped = value[:limit].rsplit(" ", 1)[0].strip()
    return clipped or value[:limit].strip()


def contains_cjk(value: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", value or ""))


@lru_cache(maxsize=512)
def translate_text_to_zh(value: str) -> str:
    cleaned = truncate_text(strip_html(value), TRANSLATE_TEXT_LIMIT)
    if not cleaned or contains_cjk(cleaned):
        return cleaned
    params = urllib.parse.urlencode(
        {
            "client": "gtx",
            "sl": "auto",
            "tl": "zh-CN",
            "dt": "t",
            "q": cleaned,
        }
    )
    for _ in range(2):
        try:
            payload = json.loads(read_text(f"{GOOGLE_TRANSLATE_URL}?{params}"))
            segments = payload[0] if isinstance(payload, list) and payload else []
            translated = "".join(str(segment[0]) for segment in segments if isinstance(segment, list) and segment)
            translated = strip_html(translated)
            if translated and (contains_cjk(translated) or translated != cleaned):
                return translated
        except Exception:  # noqa: BLE001
            continue
    return cleaned


def choose_news_preview(descriptions: list[str]) -> str:
    cleaned = [strip_html(description) for description in descriptions if strip_html(description)]
    if not cleaned:
        return ""
    return max(cleaned, key=len)


def build_news_meta_summary(publishers: list[str], providers: list[str], sections: list[str]) -> str:
    source_text = "、".join(publishers[:2]) if publishers else "未知来源"
    provider_text = "、".join(providers) if providers else "未知抓取源"
    section_text = "、".join(sections[:2]) if sections else "未分类"
    return f"来源：{source_text} | 抓取源：{provider_text} | 分区：{section_text}"


def build_news_fallback_summary(title_zh: str, publishers: list[str], sections: list[str]) -> str:
    source_text = "、".join(publishers[:2]) if publishers else "该来源"
    section_text = "、".join(sections[:2]) if sections else "新闻"
    return f"{source_text}发布了一条{section_text}快讯：{title_zh}"


def load_or_build_registry(refresh: bool) -> tuple[dict[str, Any], Path]:
    registry_path = default_registry_path()
    if refresh or not registry_path.exists():
        return build_registry(registry_path), registry_path
    return load_registry(registry_path), registry_path


def to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def format_money(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    abs_number = abs(number)
    if abs_number >= 1_000_000_000_000:
        return f"${number / 1_000_000_000_000:.2f}T"
    if abs_number >= 1_000_000_000:
        return f"${number / 1_000_000_000:.2f}B"
    if abs_number >= 1_000_000:
        return f"${number / 1_000_000:.2f}M"
    if abs_number >= 1_000:
        return f"${number / 1_000:.2f}K"
    if abs_number >= 1:
        return f"${number:.2f}"
    return f"${number:.4f}"


def format_percent(value: Any) -> str:
    number = to_float(value)
    if number is None:
        return "N/A"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.2f}%"


def average(values: list[float | None]) -> float | None:
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def normalize_title(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def build_result(kind: str, title: str, summary: str, source: str, provider: str, url: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = {
        "kind": kind,
        "title": title,
        "summary": summary,
        "source": source,
        "provider": provider,
        "url": url,
    }
    if extra:
        payload.update(extra)
    return payload


def pool_coverage(attempted: list[str], succeeded: list[str], failed: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "providers_attempted": attempted,
        "providers_succeeded": succeeded,
        "providers_failed": failed,
        "provider_count": len(succeeded),
    }


def run_source_pool(specs: list[tuple[str, Callable[[], list[dict[str, Any]]]]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    attempted = [name for name, _ in specs]
    succeeded: list[str] = []
    failed: list[dict[str, str]] = []
    payloads: dict[str, list[dict[str, Any]]] = {}
    with ThreadPoolExecutor(max_workers=max(1, min(len(specs), 6))) as executor:
        future_map = {executor.submit(loader): name for name, loader in specs}
        for future in as_completed(future_map):
            name = future_map[future]
            try:
                rows = future.result()
                if rows:
                    payloads[name] = rows
                    succeeded.append(name)
                else:
                    failed.append({"provider": name, "error": "empty"})
            except Exception as exc:  # noqa: BLE001
                failed.append({"provider": name, "error": str(exc)})
    return payloads, pool_coverage(attempted, succeeded, failed)


def significant_query_tokens(intent: dict[str, Any]) -> list[str]:
    return [token for token in intent.get("query_tokens", []) if token not in GENERIC_QUERY_TERMS]


def extract_named_coin(query: str) -> tuple[str, str, str] | None:
    lowered = query.lower()
    for alias, meta in COIN_ALIASES.items():
        if contains_alias(lowered, alias):
            return meta
    return None


def resolve_coin(query: str, intent: dict[str, Any]) -> tuple[str, str, str] | None:
    direct_hit = extract_named_coin(query)
    if direct_hit:
        return direct_hit
    for token in significant_query_tokens(intent):
        params = urllib.parse.urlencode({"q": token, "c": "currencies"})
        payload = read_json(f"{COINPAPRIKA_SEARCH_URL}?{params}")
        currencies = sorted(payload.get("currencies") or [], key=lambda row: row.get("rank") or 999999)
        if currencies:
            coin = currencies[0]
            return (str(coin.get("id")), str(coin.get("name")), str(coin.get("symbol")))
    return None


def extract_stock_symbol(query: str) -> str | None:
    lowered = query.lower()
    for alias, symbol in STOCK_ALIASES.items():
        if contains_alias(lowered, alias):
            return symbol
    for raw_token in re.findall(r"\b[A-Za-z]{1,5}\b", query):
        token = raw_token.upper()
        if token in {"API", "NEWS", "TOP", "GET", "THE", "NOW", "AI"}:
            continue
        return token
    return None


def detect_country_code(query: str) -> str | None:
    lowered = query.lower()
    for alias, code in COUNTRY_ALIASES.items():
        if contains_alias(lowered, alias):
            return code
    return None


def detect_macro_topics(query: str) -> list[str]:
    lowered = query.lower()
    topics = []
    for topic, aliases in MACRO_HINTS.items():
        if any(contains_alias(lowered, alias) for alias in aliases):
            topics.append(topic)
    return topics


def looks_like_news_query(intent: dict[str, Any]) -> bool:
    return intent.get("result_kind") == "news"


def score_news_item(
    title: str,
    publisher: str,
    section: str,
    query: str,
    intent: dict[str, Any],
    rank_hint: int = 0,
) -> int:
    preferred_sections = intent.get("matched_sections") or []
    domains = intent.get("domains") or ["News"]
    domain_aliases = domain_terms([domain for domain in domains if domain in {"News", "Finance", "Cryptocurrency"}])
    query_tokens = significant_query_tokens(intent)
    haystack = f"{title} {publisher} {section}".lower()

    score = max(0, 18 - rank_hint)
    if preferred_sections and section in preferred_sections:
        score += 14
    if not preferred_sections and section in {"World", "US", "Business", "Technology"}:
        score += 4
    for token in query_tokens:
        if token in haystack:
            score += 10
    for alias in domain_aliases:
        if contains_alias(haystack, alias):
            score += 6
    if "Cryptocurrency" in domains and section in {"Business", "Technology"}:
        score += 4
    if "Finance" in domains and section == "Business":
        score += 6
    return score


def fetch_oksurf_news(query: str, intent: dict[str, Any], top: int, sections: list[str] | None = None) -> list[dict[str, Any]]:
    payload = read_json(OKSURF_NEWS_FEED_URL)
    selected_sections = set(sections or payload.keys())
    rows = []
    for section, articles in payload.items():
        if section not in selected_sections:
            continue
        for index, article in enumerate(articles or []):
            title = str(article.get("title") or "").strip()
            link = str(article.get("link") or "").strip()
            publisher = str(article.get("source") or "").strip() or "Unknown"
            if not title or not link:
                continue
            score = score_news_item(title, publisher, section, query, intent, rank_hint=index)
            rows.append(
                {
                    "kind": "news",
                    "title": title,
                    "url": link,
                    "provider": "OkSurf",
                    "publisher": publisher,
                    "section": section,
                    "description": str(article.get("description") or article.get("summary") or "").strip(),
                    "image": article.get("og"),
                    "score": score,
                }
            )
    rows.sort(key=lambda item: (-item["score"], item["section"], item["title"]))
    return rows[: max(top * 3, top)]


def filter_news_rows_by_terms(rows: list[dict[str, Any]], terms: list[str]) -> list[dict[str, Any]]:
    filtered = []
    for row in rows:
        text = f"{row.get('title', '')} {row.get('publisher', '')} {row.get('section', '')}".lower()
        if any(contains_alias(text, term) for term in terms):
            filtered.append(row)
    return filtered


def fetch_rss_news(feed_url: str, provider: str, query: str, intent: dict[str, Any], top: int, section: str = "Cryptocurrency") -> list[dict[str, Any]]:
    text = read_text(feed_url)
    root = ET.fromstring(text)
    rows = []
    for index, item in enumerate(root.findall(".//item")):
        title = str(item.findtext("title") or "").strip()
        link = str(item.findtext("link") or "").strip()
        if not title or not link:
            continue
        description = str(item.findtext("description") or "").strip()
        score = score_news_item(title, provider, section, query, intent, rank_hint=index)
        score += 12
        rows.append(
            {
                "kind": "news",
                "title": title,
                "url": link,
                "provider": provider,
                "publisher": provider,
                "section": section,
                "description": description,
                "score": score,
            }
        )
    rows.sort(key=lambda item: (-item["score"], item["title"]))
    return rows[: max(top * 3, top)]


def aggregate_news_rows(rows: list[dict[str, Any]], top: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = normalize_title(row.get("title")) or str(row.get("url"))
        group = grouped.setdefault(
            key,
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "providers": [],
                "publishers": [],
                "sections": [],
                "images": [],
                "descriptions": [],
                "score": 0,
            },
        )
        group["score"] = max(group["score"], int(row.get("score") or 0))
        group["providers"].append(str(row.get("provider")))
        group["publishers"].append(str(row.get("publisher")))
        group["sections"].append(str(row.get("section")))
        if row.get("description"):
            group["descriptions"].append(str(row.get("description")))
        if row.get("image"):
            group["images"].append(row.get("image"))

    ranked = sorted(grouped.values(), key=lambda item: (-item["score"], item["title"].lower()))
    results = []
    for group in ranked[:top]:
        original_title = str(group["title"])
        providers = sorted(set(group["providers"]))
        publishers = sorted(set(group["publishers"]))
        sections = sorted(set(group["sections"]))
        preview = choose_news_preview(group["descriptions"])
        preview = truncate_text(preview, 320) if preview else ""
        title_zh = translate_text_to_zh(original_title) or original_title
        preview_zh = translate_text_to_zh(preview) if preview else ""
        meta_summary = build_news_meta_summary(publishers, providers, sections)
        summary_zh = preview_zh or build_news_fallback_summary(title_zh, publishers, sections)
        results.append(
            build_result(
                kind="news",
                title=title_zh,
                summary=summary_zh,
                source=", ".join(publishers),
                provider=", ".join(providers),
                url=str(group["url"]),
                extra={
                    "title_original": original_title,
                    "title_zh": title_zh,
                    "summary_original": preview or None,
                    "summary_zh": summary_zh,
                    "content_preview": preview or None,
                    "content_preview_zh": preview_zh or None,
                    "content_available": bool(preview),
                    "meta_summary": meta_summary,
                    "providers": providers,
                    "provider_count": len(providers),
                    "publishers": publishers,
                    "publisher_count": len(publishers),
                    "sections": sections,
                    "image": group["images"][0] if group["images"] else None,
                },
            )
        )
    return results


def fetch_coinpaprika_assets(intent: dict[str, Any], top: int, coin_symbol: str | None = None) -> list[dict[str, Any]]:
    if coin_symbol:
        coin = resolve_coin(coin_symbol, {"query_tokens": [coin_symbol]})
        if coin:
            coin_id, coin_name, symbol = coin
            ticker = read_json(f"{COINPAPRIKA_TICKERS_URL}/{coin_id}")
            usd = ((ticker.get("quotes") or {}).get("USD") or {})
            return [
                {
                    "symbol": symbol,
                    "name": coin_name,
                    "provider": "Coinpaprika",
                    "price": to_float(usd.get("price")),
                    "percent_change_24h": to_float(usd.get("percent_change_24h")),
                    "volume_24h": to_float(usd.get("volume_24h")),
                    "market_cap": to_float(usd.get("market_cap")),
                    "rank": to_float(ticker.get("rank")),
                    "url": f"{COINPAPRIKA_TICKERS_URL}/{coin_id}",
                }
            ]
    tickers = read_json(f"{COINPAPRIKA_TICKERS_URL}?limit={max(top * 2, 12)}")
    rows = []
    for ticker in tickers:
        usd = ((ticker.get("quotes") or {}).get("USD") or {})
        rows.append(
            {
                "symbol": str(ticker.get("symbol")),
                "name": str(ticker.get("name")),
                "provider": "Coinpaprika",
                "price": to_float(usd.get("price")),
                "percent_change_24h": to_float(usd.get("percent_change_24h")),
                "volume_24h": to_float(usd.get("volume_24h")),
                "market_cap": to_float(usd.get("market_cap")),
                "rank": to_float(ticker.get("rank")),
                "url": f"{COINPAPRIKA_TICKERS_URL}/{ticker.get('id')}",
            }
        )
    return rows


def fetch_coinlore_assets(top: int, coin_symbol: str | None = None) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"start": 0, "limit": max(top * 2, 20)})
    payload = read_json(f"{COINLORE_TICKERS_URL}?{params}")
    rows = []
    for item in payload.get("data") or []:
        symbol = str(item.get("symbol"))
        if coin_symbol and symbol.upper() != coin_symbol.upper():
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": str(item.get("name")),
                "provider": "Coinlore",
                "price": to_float(item.get("price_usd")),
                "percent_change_24h": to_float(item.get("percent_change_24h")),
                "volume_24h": to_float(item.get("volume24")),
                "market_cap": to_float(item.get("market_cap_usd")),
                "rank": to_float(item.get("rank")),
                "url": "https://www.coinlore.com/cryptocurrency-data-api",
            }
        )
    return rows


def fetch_coinranking_assets(top: int, coin_symbol: str | None = None) -> list[dict[str, Any]]:
    params = {"limit": max(top * 2, 20)}
    if coin_symbol and coin_symbol.upper() in COINRANKING_UUIDS:
        params = {"uuids[]": COINRANKING_UUIDS[coin_symbol.upper()]}
    payload = read_json(f"{COINRANKING_COINS_URL}?{urllib.parse.urlencode(params, doseq=True)}")
    rows = []
    for item in ((payload.get("data") or {}).get("coins") or []):
        symbol = str(item.get("symbol"))
        if coin_symbol and symbol.upper() != coin_symbol.upper():
            continue
        rows.append(
            {
                "symbol": symbol,
                "name": str(item.get("name")),
                "provider": "CoinRanking",
                "price": to_float(item.get("price")),
                "percent_change_24h": to_float(item.get("change")),
                "volume_24h": to_float(item.get("24hVolume")),
                "market_cap": to_float(item.get("marketCap")),
                "rank": to_float(item.get("rank")),
                "url": COINRANKING_COINS_URL,
            }
        )
    return rows


def fetch_gateio_quotes(coin_symbol: str | None = None) -> list[dict[str, Any]]:
    symbols = [coin_symbol.upper()] if coin_symbol else ["BTC", "ETH", "BNB", "XRP", "SOL"]
    rows = []
    for symbol in symbols:
        pair = GATEIO_SYMBOLS.get(symbol)
        if not pair:
            continue
        params = urllib.parse.urlencode({"currency_pair": pair})
        payload = read_json(f"{GATEIO_TICKER_URL}?{params}")
        if not payload:
            continue
        item = payload[0]
        rows.append(
            {
                "symbol": symbol,
                "name": SYMBOL_DISPLAY_NAMES.get(symbol, symbol),
                "provider": "Gate.io",
                "price": to_float(item.get("last")),
                "percent_change_24h": to_float(item.get("change_percentage")),
                "volume_24h": to_float(item.get("quote_volume")),
                "market_cap": None,
                "rank": None,
                "url": f"{GATEIO_TICKER_URL}?{params}",
            }
        )
    return rows


def fetch_gemini_quotes(coin_symbol: str | None = None) -> list[dict[str, Any]]:
    symbols = [coin_symbol.upper()] if coin_symbol else ["BTC", "ETH"]
    rows = []
    for symbol in symbols:
        pair = GEMINI_SYMBOLS.get(symbol)
        if not pair:
            continue
        payload = read_json(f"{GEMINI_TICKER_URL}/{pair}")
        rows.append(
            {
                "symbol": symbol,
                "name": SYMBOL_DISPLAY_NAMES.get(symbol, symbol),
                "provider": "Gemini",
                "price": to_float(payload.get("last")),
                "percent_change_24h": None,
                "volume_24h": to_float((payload.get("volume") or {}).get("USD")),
                "market_cap": None,
                "rank": None,
                "url": f"{GEMINI_TICKER_URL}/{pair}",
            }
        )
    return rows


def fetch_blockchain_stats() -> list[dict[str, Any]]:
    payload = read_json(BLOCKCHAIN_STATS_URL)
    return [
        build_result(
            kind="market-network",
            title="BTC network stats",
            summary=(
                f"Price {format_money(payload.get('market_price_usd'))} | "
                f"Hash rate {payload.get('hash_rate'):.0f} | "
                f"24h tx {payload.get('n_tx')} | "
                f"Trade volume {format_money(payload.get('trade_volume_usd'))}"
            ),
            source="Blockchain",
            provider="Blockchain",
            url=BLOCKCHAIN_STATS_URL,
        )
    ]


def aggregate_crypto_quotes(quotes: list[dict[str, Any]], top: int, market_style: str | None) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for quote in quotes:
        symbol = str(quote.get("symbol") or "").upper()
        if not symbol:
            continue
        grouped.setdefault(symbol, []).append(quote)

    scored = []
    for symbol, rows in grouped.items():
        prices = [to_float(row.get("price")) for row in rows]
        changes = [to_float(row.get("percent_change_24h")) for row in rows]
        volumes = [to_float(row.get("volume_24h")) for row in rows]
        market_caps = [to_float(row.get("market_cap")) for row in rows]
        ranks = [to_float(row.get("rank")) for row in rows]
        providers = sorted({str(row.get("provider")) for row in rows})
        avg_price = average(prices)
        avg_change = average(changes)
        avg_volume = average(volumes)
        avg_rank = average(ranks) or 999999
        title = f"{symbol} | {rows[0].get('name')}"
        summary = (
            f"Avg {format_money(avg_price)} | "
            f"Range {format_money(min(value for value in prices if value is not None))}-{format_money(max(value for value in prices if value is not None))}"
            if [value for value in prices if value is not None]
            else "Avg N/A | Range N/A"
        )
        if [value for value in changes if value is not None]:
            summary += f" | 24h {format_percent(avg_change)}"
        if [value for value in market_caps if value is not None]:
            summary += f" | MCap {format_money(max(value for value in market_caps if value is not None))}"
        summary += f" | {len(providers)} providers"

        result = build_result(
            kind="market-asset",
            title=title,
            summary=summary,
            source=", ".join(providers),
            provider=", ".join(providers),
            url=str(rows[0].get("url")),
            extra={
                "symbol": symbol,
                "providers": providers,
                "provider_count": len(providers),
                "average_price": avg_price,
                "average_change_24h": avg_change,
                "average_volume_24h": avg_volume,
                "average_rank": avg_rank,
            },
        )
        sort_value = avg_rank
        if market_style == "gainers":
            sort_value = -(avg_change or -999999)
        elif market_style == "losers":
            sort_value = avg_change or 999999
        elif market_style == "volume":
            sort_value = -(avg_volume or -1)
        scored.append((sort_value, result))

    scored.sort(key=lambda item: item[0])
    return [row for _, row in scored[:top]]


def fetch_crypto_market_pool(query: str, intent: dict[str, Any], top: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    named_coin = resolve_coin(query, intent)
    symbol = named_coin[2] if named_coin else None
    specs = [
        ("Coinpaprika", lambda: fetch_coinpaprika_assets(intent, top, symbol)),
        ("Coinlore", lambda: fetch_coinlore_assets(top, symbol)),
        ("CoinRanking", lambda: fetch_coinranking_assets(top, symbol)),
        ("Gate.io", lambda: fetch_gateio_quotes(symbol)),
        ("Gemini", lambda: fetch_gemini_quotes(symbol)),
    ]
    payloads, coverage = run_source_pool(specs)
    global_rows = []
    try:
        global_data = read_json(COINPAPRIKA_GLOBAL_URL)
        global_rows.append(
            build_result(
                kind="market-summary",
                title="Crypto market overview",
                summary=(
                    f"Market cap {format_money(global_data.get('market_cap_usd'))} | "
                    f"24h {format_percent(global_data.get('market_cap_change_24h'))} | "
                    f"24h volume {format_money(global_data.get('volume_24h_usd'))} | "
                    f"BTC dominance {global_data.get('bitcoin_dominance_percentage')}%"
                ),
                source="Coinpaprika",
                provider="Coinpaprika",
                url=COINPAPRIKA_GLOBAL_URL,
            )
        )
    except Exception:
        pass

    quotes: list[dict[str, Any]] = []
    for rows in payloads.values():
        quotes.extend(rows)

    results = list(global_rows)
    if not symbol or symbol == "BTC":
        try:
            results.extend(fetch_blockchain_stats())
            if "Blockchain" not in coverage["providers_attempted"]:
                coverage["providers_attempted"].append("Blockchain")
            if "Blockchain" not in coverage["providers_succeeded"]:
                coverage["providers_succeeded"].append("Blockchain")
                coverage["provider_count"] = len(coverage["providers_succeeded"])
        except Exception as exc:  # noqa: BLE001
            coverage["providers_failed"].append({"provider": "Blockchain", "error": str(exc)})

    results.extend(aggregate_crypto_quotes(quotes, max(1, top - len(results)), intent.get("market_style")))
    return results[:top], coverage


def fetch_valueray_symbol(symbol: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"symbol": symbol})
    payload = read_json(f"{VALUERAY_SYMBOL_DATA_URL}?{params}")
    if not payload:
        return []
    details = next(iter(payload.values()))
    technical = details.get("technical") or {}
    performance = details.get("performance") or {}
    risk = details.get("risk") or {}
    return [
        build_result(
            kind="market-asset",
            title=f"{details.get('code')} | {details.get('name')}",
            summary=(
                f"Last {format_money(technical.get('last_price'))} | "
                f"1d {format_percent(performance.get('perf_1d'))} | "
                f"1w {format_percent(performance.get('perf_1w'))} | "
                f"Sharpe {risk.get('sharpe_ratio')}"
            ),
            source="ValueRay",
            provider="ValueRay",
            url=f"{VALUERAY_SYMBOL_DATA_URL}?{params}",
            extra={
                "symbol": details.get("code"),
                "exchange": details.get("exchange"),
                "sector": details.get("sector"),
            },
        )
    ]


def fetch_stooq_symbol(symbol: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode({"s": f"{symbol.lower()}.us", "i": "d"})
    payload = read_text(f"{STOOQ_SYMBOL_URL}?{params}").strip()
    if not payload:
        return []
    fields = [field.strip() for field in payload.split(",")]
    if len(fields) < 8:
        return []
    ticker, date_value, time_value, open_value, high_value, low_value, close_value, volume_value = fields[:8]
    if not ticker or ticker.upper() == "N/D":
        return []
    display_name = SYMBOL_DISPLAY_NAMES.get(symbol.upper(), symbol.upper())
    summary = (
        f"收盘 {format_money(close_value)} | "
        f"开盘 {format_money(open_value)} | "
        f"日高 {format_money(high_value)} | "
        f"日低 {format_money(low_value)} | "
        f"成交量 {volume_value or 'N/A'}"
    )
    return [
        build_result(
            kind="market-asset",
            title=f"{symbol.upper()} | {display_name}",
            summary=summary,
            source="Stooq",
            provider="Stooq",
            url=f"{STOOQ_SYMBOL_URL}?{params}",
            extra={
                "symbol": symbol.upper(),
                "exchange": "US",
                "quote_date": date_value,
                "quote_time": time_value,
            },
        )
    ]


def fetch_stooq_market_overview() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for symbol in ("SPY", "QQQ", "DIA"):
        try:
            rows.extend(fetch_stooq_symbol(symbol))
        except Exception:  # noqa: BLE001
            continue
    return rows


def fetch_valueray_market_regime() -> list[dict[str, Any]]:
    payload = read_json(VALUERAY_MARKET_REGIME_URL)
    regime_values = payload.get("regime_values") or {}
    strongest = (payload.get("industry_rotation") or [])[:2]
    weakest = [row for row in (payload.get("industry_rotation") or []) if str(row.get("rel_delta") or "").startswith("-")][:2]
    rows = [
        build_result(
            kind="market-summary",
            title="US market regime",
            summary=(
                f"VIX {regime_values.get('VIX')} | MOVE {regime_values.get('MOVE')} | "
                f"SKEW {regime_values.get('SKEW')} | COR10D {regime_values.get('COR10D')}"
            ),
            source="ValueRay",
            provider="ValueRay",
            url=VALUERAY_MARKET_REGIME_URL,
        )
    ]
    if strongest:
        rows.append(
            build_result(
                kind="market-rotation",
                title="Strongest industry rotation",
                summary="; ".join(f"{row.get('industry')} {row.get('rel_delta')}" for row in strongest),
                source="ValueRay",
                provider="ValueRay",
                url=VALUERAY_MARKET_REGIME_URL,
            )
        )
    if weakest:
        rows.append(
            build_result(
                kind="market-rotation",
                title="Weakest industry rotation",
                summary="; ".join(f"{row.get('industry')} {row.get('rel_delta')}" for row in weakest),
                source="ValueRay",
                provider="ValueRay",
                url=VALUERAY_MARKET_REGIME_URL,
            )
        )
    return rows


def fetch_predscope_markets(query: str, top: int, strict: bool = False) -> list[dict[str, Any]]:
    payload = read_json(PREDSCOPE_MARKETS_URL)
    rows = []
    lowered = query.lower()
    allowed_categories = {"economy", "politics", "geopolitics", "crypto", "trump"}
    for market in payload.get("markets") or []:
        categories = [str(category) for category in market.get("categories") or []]
        category_set = {category.lower() for category in categories}
        if not category_set.intersection(allowed_categories):
            continue
        score = to_float(market.get("volume_24h")) or 0
        haystack = f"{market.get('title', '')} {' '.join(categories)}".lower()
        if "economy" in categories:
            score += 50
        if "crypto" in categories:
            score += 20
        if any(token in haystack for token in ["fed", "inflation", "rate", "economy", "crypto", "trump"]):
            score += 10
        if any(contains_alias(lowered, token) for token in ["\u7ecf\u6d4e", "\u5229\u7387", "\u901a\u80c0", "\u9884\u6d4b", "economy", "inflation", "rate"]):
            score += 10
        if strict and score < 20:
            continue
        rows.append(
            {
                "score": score,
                "result": build_result(
                    kind="event-odds",
                    title=str(market.get("title")),
                    summary=(
                        f"24h volume {format_money(market.get('volume_24h'))} | "
                        f"Liquidity {format_money(market.get('liquidity'))} | "
                        f"Categories: {', '.join(categories[:2])}"
                    ),
                    source="PredScope",
                    provider="PredScope",
                    url=f"https://predscope.com{market.get('url')}",
                    extra={"categories": categories},
                ),
            }
        )
    rows.sort(key=lambda item: (-item["score"], item["result"]["title"]))
    return [item["result"] for item in rows[:top]]


def fetch_statsworld_country(query: str, top: int) -> list[dict[str, Any]]:
    country = detect_country_code(query) or "USA"
    topics = detect_macro_topics(query)
    payload = read_json(f"{STATS_WORLD_COUNTRY_URL}/{country}")
    indicators = payload.get("indicators") or []
    filtered = []
    for indicator in indicators:
        label = str(indicator.get("label") or "")
        haystack = label.lower()
        score = 0
        if not topics:
            score = 1
        for topic in topics:
            for alias in MACRO_HINTS.get(topic, []):
                if contains_alias(haystack, alias):
                    score += 12
        if score:
            filtered.append((score, indicator))
    filtered.sort(key=lambda item: (-item[0], str(item[1].get("label"))))
    rows = []
    for _, indicator in filtered[:top]:
        rows.append(
            build_result(
                kind="macro-indicator",
                title=f"{payload.get('country', {}).get('name')} | {indicator.get('label')}",
                summary=f"Value {indicator.get('value')} | Year {indicator.get('year')} | Category {indicator.get('category')}",
                source="Statistics of the World",
                provider="Statistics of the World",
                url=f"{STATS_WORLD_COUNTRY_URL}/{country}",
                extra={"indicator_id": indicator.get("id")},
            )
        )
    return rows


def fetch_finance_context_news(query: str, intent: dict[str, Any], top: int) -> list[dict[str, Any]]:
    symbol = extract_stock_symbol(query)
    alias = SYMBOL_DISPLAY_NAMES.get(symbol or "", symbol or "")
    local_intent = dict(intent)
    local_intent["matched_sections"] = ["Business", "Technology"]
    rows = fetch_oksurf_news(query, local_intent, top * 2, sections=["Business", "Technology"])
    if not symbol:
        return aggregate_news_rows(rows[:top], top)
    filtered = []
    symbol_lower = symbol.lower()
    alias_lower = alias.lower()
    for row in rows:
        text = f"{row.get('title','')} {row.get('publisher','')}".lower()
        if symbol_lower in text or (alias_lower and alias_lower in text):
            filtered.append(row)
    return aggregate_news_rows(filtered[:top], top)


def fetch_finance_market_pool(query: str, intent: dict[str, Any], top: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    symbol = extract_stock_symbol(query)
    country = detect_country_code(query)
    macro_topics = detect_macro_topics(query)
    specs: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = []
    if symbol:
        specs.append(("ValueRay", lambda: fetch_valueray_symbol(symbol)))
        specs.append(("Stooq", lambda: fetch_stooq_symbol(symbol)))
        specs.append(("OkSurf", lambda: fetch_finance_context_news(query, intent, max(1, top - 1))))
    else:
        specs.append(("ValueRay", fetch_valueray_market_regime))
        specs.append(("Stooq", fetch_stooq_market_overview))
        specs.append(("PredScope", lambda: fetch_predscope_markets(query, 2, strict=False)))
        if country or macro_topics:
            specs.append(("Statistics of the World", lambda: fetch_statsworld_country(query, 2)))
        if looks_like_news_query(intent):
            specs.append(("OkSurf", lambda: fetch_finance_context_news(query, intent, 2)))

    payloads, coverage = run_source_pool(specs)
    results: list[dict[str, Any]] = []
    if symbol:
        primary_rows: list[dict[str, Any]] = []
        context_rows: list[dict[str, Any]] = []
        for provider, rows in payloads.items():
            if provider in {"ValueRay", "Stooq"}:
                primary_rows.extend(rows)
            else:
                context_rows.extend(rows)
        if primary_rows:
            provider_priority = {"ValueRay": 0, "Stooq": 1, "OkSurf": 2}
            for provider, rows in sorted(payloads.items(), key=lambda item: provider_priority.get(item[0], 99)):
                results.extend(rows)
            return results[:top], coverage
        return [], coverage

    provider_priority = {"ValueRay": 0, "Stooq": 1, "Statistics of the World": 2, "PredScope": 3, "OkSurf": 4}
    for provider, rows in sorted(payloads.items(), key=lambda item: provider_priority.get(item[0], 99)):
        results.extend(rows)
    return results[:top], coverage


def fetch_crypto_news_pool(query: str, intent: dict[str, Any], top: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    crypto_terms = domain_terms(["Cryptocurrency"])
    payloads, coverage = run_source_pool(
        [
            (
                "OkSurf",
                lambda: filter_news_rows_by_terms(
                    fetch_oksurf_news(query, intent, top * 3, sections=["Business", "Technology"]),
                    crypto_terms,
                ),
            ),
            ("Cointelegraph", lambda: fetch_rss_news(COINTELEGRAPH_RSS_URL, "Cointelegraph", query, intent, top * 2)),
            ("The Block", lambda: fetch_rss_news(THEBLOCK_RSS_URL, "The Block", query, intent, top * 2)),
            ("Decrypt", lambda: fetch_rss_news(DECRYPT_RSS_URL, "Decrypt", query, intent, top * 2)),
        ]
    )
    rows: list[dict[str, Any]] = []
    for provider_rows in payloads.values():
        rows.extend(provider_rows)
    return aggregate_news_rows(rows, top), coverage


def fetch_general_news_pool(query: str, intent: dict[str, Any], top: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payloads, coverage = run_source_pool(
        [
            ("OkSurf", lambda: fetch_oksurf_news(query, intent, top * 2)),
            ("BBC", lambda: fetch_rss_news(BBC_WORLD_RSS_URL, "BBC", query, intent, top * 2, section="World")),
            ("NPR", lambda: fetch_rss_news(NPR_TOP_RSS_URL, "NPR", query, intent, top * 2, section="US")),
            ("New York Times", lambda: fetch_rss_news(NYT_TOP_RSS_URL, "New York Times", query, intent, top * 2, section="World")),
        ]
    )
    rows = []
    for provider_rows in payloads.values():
        rows.extend(provider_rows)
    return aggregate_news_rows(rows, top), coverage


def fetch_finance_news_pool(query: str, intent: dict[str, Any], top: int) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payloads, coverage = run_source_pool(
        [
            ("OkSurf", lambda: fetch_oksurf_news(query, intent, top * 2, sections=["Business", "Technology"])),
            ("NPR Business", lambda: fetch_rss_news(NPR_BUSINESS_RSS_URL, "NPR Business", query, intent, top * 2, section="Business")),
            ("New York Times Business", lambda: fetch_rss_news(NYT_BUSINESS_RSS_URL, "New York Times Business", query, intent, top * 2, section="Business")),
        ]
    )
    rows = []
    for provider_rows in payloads.values():
        rows.extend(provider_rows)
    return aggregate_news_rows(rows, top), coverage


def choose_pool(query: str, intent: dict[str, Any]) -> str:
    domains = intent.get("domains") or []
    if intent.get("result_kind") == "news":
        if "Cryptocurrency" in domains:
            return "news.crypto"
        if "Finance" in domains:
            return "news.finance"
        return "news.general"
    if intent.get("result_kind") == "market":
        if "Cryptocurrency" in domains:
            return "market.crypto"
        return "market.finance"
    if "Finance" in domains:
        return "market.finance"
    if "Cryptocurrency" in domains:
        return "market.crypto"
    return "news.general"


def fetch_direct_results(query: str, intent: dict[str, Any], top: int) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    pool_key = choose_pool(query, intent)
    if pool_key == "news.crypto":
        results, coverage = fetch_crypto_news_pool(query, intent, top)
        return pool_key, results, coverage
    if pool_key == "news.finance":
        results, coverage = fetch_finance_news_pool(query, intent, top)
        return pool_key, results, coverage
    if pool_key == "market.crypto":
        results, coverage = fetch_crypto_market_pool(query, intent, top)
        return pool_key, results, coverage
    if pool_key == "market.finance":
        results, coverage = fetch_finance_market_pool(query, intent, top)
        return pool_key, results, coverage
    results, coverage = fetch_general_news_pool(query, intent, top)
    return pool_key, results, coverage


def main() -> None:
    args = parse_args()
    registry, registry_path = load_or_build_registry(args.refresh)
    intent = detect_intent(args.query)
    mode = intent["action"] if args.mode == "auto" else args.mode

    if mode == "discover":
        discovery = shortlist(args.query, registry, max(1, args.top))
        output = {
            "query": args.query,
            "mode": "discover",
            "intent": intent,
            "result_count": discovery.get("result_count"),
            "results": discovery.get("results"),
            "generated_at": registry.get("generated_at"),
            "registry_path": str(registry_path),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    pool_key = None
    direct_results: list[dict[str, Any]] = []
    coverage: dict[str, Any] = {"providers_attempted": [], "providers_succeeded": [], "providers_failed": [], "provider_count": 0}
    fetch_error = None
    try:
        pool_key, direct_results, coverage = fetch_direct_results(args.query, intent, max(1, args.top))
    except Exception as exc:  # noqa: BLE001
        fetch_error = str(exc)

    if direct_results:
        output = {
            "query": args.query,
            "mode": "fetch",
            "intent": intent,
            "pool": pool_key,
            "coverage": coverage,
            "selected_sources": coverage.get("providers_succeeded", []),
            "result_count": len(direct_results),
            "results": direct_results,
            "generated_at": registry.get("generated_at"),
            "registry_path": str(registry_path),
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    discovery = shortlist(args.query, registry, max(1, args.top))
    output = {
        "query": args.query,
        "mode": "discover-fallback",
        "intent": intent,
        "pool": pool_key,
        "coverage": coverage,
        "fetch_error": fetch_error,
        "result_count": discovery.get("result_count"),
        "results": discovery.get("results"),
        "generated_at": registry.get("generated_at"),
        "registry_path": str(registry_path),
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
