#!/usr/bin/env python3
"""Shared natural-language intent detection for the free API discovery skill."""

from __future__ import annotations

import re
from typing import Any


CATEGORY_ALIASES = {
    "News": [
        "news",
        "headline",
        "headlines",
        "article",
        "articles",
        "media",
        "rss",
        "newswire",
        "bulletin",
        "press",
        "coverage",
        "story",
        "stories",
        "资讯",
        "新闻",
        "快讯",
        "头条",
        "报道",
        "消息",
        "舆情",
        "动态",
        "热点",
        "热搜",
    ],
    "Finance": [
        "finance",
        "financial",
        "stock",
        "stocks",
        "equity",
        "equities",
        "market",
        "markets",
        "macro",
        "economy",
        "economic",
        "forex",
        "earnings",
        "fed",
        "fomc",
        "sec",
        "filings",
        "trading",
        "exchange",
        "bond",
        "bonds",
        "etf",
        "etfs",
        "commodities",
        "财经",
        "金融",
        "美股",
        "港股",
        "a股",
        "股市",
        "大盘",
        "宏观",
        "外汇",
        "期货",
        "债券",
        "财报",
        "利率",
        "美联储",
        "纳指",
        "标普",
    ],
    "Cryptocurrency": [
        "crypto",
        "cryptocurrency",
        "coin",
        "coins",
        "token",
        "tokens",
        "blockchain",
        "onchain",
        "defi",
        "nft",
        "web3",
        "meme coin",
        "stablecoin",
        "btc",
        "eth",
        "sol",
        "bnb",
        "xrp",
        "比特币",
        "以太坊",
        "加密",
        "币圈",
        "币市",
        "代币",
        "链上",
        "区块链",
        "山寨币",
        "公链",
        "meme币",
        "稳定币",
    ],
    "Weather": ["weather", "forecast", "temperature", "rain", "climate", "天气"],
    "Geocoding": [
        "geocode",
        "geocoding",
        "coordinates",
        "coordinate",
        "latitude",
        "longitude",
        "lat",
        "lon",
        "location",
        "map",
        "maps",
        "地理编码",
        "经纬度",
        "坐标",
        "位置",
        "地点",
        "城市在哪",
        "在哪里",
        "在哪",
    ],
    "Currency Exchange": [
        "currency",
        "currencies",
        "exchange rate",
        "fx",
        "forex",
        "convert",
        "conversion",
        "converter",
        "rate",
        "rates",
        "汇率",
        "兑换",
        "换汇",
        "外汇",
        "折算",
        "美元",
        "人民币",
        "欧元",
        "日元",
        "英镑",
        "港币",
    ],
    "Sports & Fitness": ["sports", "sport", "score", "scores", "match", "matches", "fitness", "体育"],
    "Social": ["social", "twitter", "reddit", "community", "mastodon", "社交", "社区"],
    "Government": ["government", "gov", "policy", "public records", "regulation", "政务", "监管"],
    "Open Data": [
        "open data",
        "dataset",
        "datasets",
        "country data",
        "population",
        "capital",
        "area",
        "language",
        "timezone",
        "country profile",
        "公开数据",
        "数据集",
        "国家信息",
        "国家数据",
        "人口",
        "首都",
        "面积",
        "语言",
        "时区",
    ],
    "Documents & Productivity": ["document", "documents", "pdf", "doc", "ocr", "productivity", "文档"],
    "Search": [
        "search",
        "serp",
        "google",
        "bing",
        "web search",
        "wiki",
        "wikipedia",
        "what is",
        "who is",
        "百科",
        "搜索",
        "检索",
        "是什么",
        "谁是",
        "介绍一下",
        "科普",
    ],
    "GraphQL": ["graphql", "gql", "schema", "introspection", "graph ql", "图查询"],
}

SECTION_ALIASES = {
    "US": ["us", "usa", "america", "american", "美国"],
    "World": ["world", "global", "international", "全球", "国际"],
    "Business": ["business", "finance", "financial", "market", "markets", "business news", "财经", "商业", "金融", "股市"],
    "Technology": ["tech", "technology", "ai", "software", "startup", "科技", "技术", "人工智能", "大模型"],
    "Entertainment": ["entertainment", "celebrity", "movie", "music", "tv", "showbiz", "娱乐", "影视"],
    "Sports": ["sports", "sport", "match", "nba", "soccer", "football", "体育"],
    "Science": ["science", "scientific", "space", "research", "科研", "科学", "航天"],
    "Health": ["health", "medical", "medicine", "hospital", "wellness", "健康", "医疗"],
}

DISCOVER_TERMS = [
    "api",
    "apis",
    "endpoint",
    "endpoints",
    "source",
    "sources",
    "provider",
    "providers",
    "graphql",
    "schema",
    "introspection",
    "docs",
    "documentation",
    "openapi",
    "swagger",
    "sdk",
    "integration",
    "接口",
    "接口源",
    "数据源",
    "源",
    "端点",
    "文档",
    "接入",
    "服务源",
]

FETCH_TERMS = [
    "fetch",
    "get me",
    "show me",
    "pull",
    "grab",
    "bring me",
    "give me",
    "find out",
    "summarize",
    "summary",
    "wrap up",
    "看看",
    "看下",
    "给我",
    "帮我",
    "抓",
    "拉",
    "查",
    "搜一下",
    "汇总",
    "总结",
    "整理",
    "输出",
    "直接出",
]

LATEST_TERMS = [
    "latest",
    "recent",
    "newest",
    "today",
    "now",
    "real time",
    "breaking",
    "fresh",
    "最新",
    "最近",
    "今天",
    "刚刚",
    "实时",
    "当下",
    "当前",
]

NEWS_TERMS = [
    "news",
    "headline",
    "headlines",
    "story",
    "stories",
    "article",
    "articles",
    "bulletin",
    "press",
    "资讯",
    "新闻",
    "快讯",
    "头条",
    "报道",
    "消息",
    "动态",
    "热点",
]

MARKET_TERMS = [
    "market",
    "markets",
    "market data",
    "price",
    "prices",
    "pricing",
    "quote",
    "quotes",
    "ticker",
    "tickers",
    "gainer",
    "gainers",
    "loser",
    "losers",
    "heatmap",
    "snapshot",
    "data",
    "stats",
    "signal",
    "signals",
    "行情",
    "盘面",
    "价格",
    "涨跌",
    "市值",
    "成交量",
    "数据",
    "报价",
    "指标",
    "k线",
    "市场",
    "市场数据",
    "行情数据",
    "大盘",
    "盘口",
    "走势",
]

NO_AUTH_TERMS = [
    "no auth",
    "no key",
    "without api key",
    "free no key",
    "免 key",
    "无需 key",
    "不用 key",
    "不要 key",
    "不要key",
    "别用 key",
    "别用key",
    "无 key",
    "无key",
    "免鉴权",
    "免密钥",
    "不需要密钥",
    "不带 key",
    "不带key",
]

STRONG_DISCOVER_PATTERNS = [
    r"(?:找|搜|查|推荐|列出|给我几个|有没有).{0,10}(?:api|接口|数据源|源|端点|graphql)",
    r"(?:用什么|哪个|哪种).{0,10}(?:api|接口|源|端点)",
    r"(?:free|public).{0,10}(?:api|apis|endpoint|graphql)",
]

STRONG_FETCH_PATTERNS = [
    r"(?:帮我|给我|直接|现在|马上).{0,12}(?:抓|拉|看|查|取|拿|汇总|总结|整理)",
    r"(?:最新|今天|刚刚|实时|最近).{0,12}(?:新闻|资讯|快讯|头条|行情|盘面|价格|市场)",
    r"(?:发生了什么|有什么新消息|看下最新|拉一下|抓一下)",
]

MARKET_STYLE_TERMS = {
    "gainers": ["gainer", "gainers", "top up", "涨幅", "领涨", "涨得最好"],
    "losers": ["loser", "losers", "top down", "跌幅", "领跌", "跌得最多"],
    "volume": ["volume", "turnover", "成交量", "交易量", "换手"],
}

GRAPHQL_TERMS = CATEGORY_ALIASES["GraphQL"]

STOP_TOKENS = {
    "a",
    "an",
    "and",
    "api",
    "apis",
    "data",
    "for",
    "free",
    "get",
    "give",
    "graphql",
    "latest",
    "look",
    "new",
    "news",
    "public",
    "ql",
    "show",
    "the",
    "today",
    "with",
}


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


def contains_alias(text: str, alias: str) -> bool:
    alias = str(alias or "").strip().lower()
    if not alias:
        return False
    text = str(text or "").lower()
    if re.fullmatch(r"[a-z0-9]+(?: [a-z0-9]+)*", alias):
        pattern = r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])"
        return re.search(pattern, text) is not None
    return alias in text


def tokenize(text: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", str(text or "").lower()) if token]


def significant_tokens(text: str) -> list[str]:
    return [token for token in tokenize(text) if len(token) >= 2 and token not in STOP_TOKENS]


def match_aliases(text: str, aliases: list[str]) -> list[str]:
    lowered = str(text or "").lower()
    return unique_list([alias for alias in aliases if contains_alias(lowered, alias)])


def match_patterns(text: str, patterns: list[str]) -> list[str]:
    return unique_list([pattern for pattern in patterns if re.search(pattern, str(text or "").lower())])


def detect_categories(query: str) -> list[str]:
    query_lower = str(query or "").lower()
    matched = []
    for category, aliases in CATEGORY_ALIASES.items():
        if any(contains_alias(query_lower, alias) for alias in aliases):
            matched.append(category)
    return matched


def detect_sections(query: str) -> list[str]:
    query_lower = str(query or "").lower()
    matched = []
    for section, aliases in SECTION_ALIASES.items():
        if any(contains_alias(query_lower, alias) for alias in aliases):
            matched.append(section)
    return matched


def domain_terms(domains: list[str]) -> list[str]:
    terms: list[str] = []
    for domain in domains:
        terms.extend(CATEGORY_ALIASES.get(domain, []))
    return unique_list(terms)


def detect_intent(query: str) -> dict[str, Any]:
    query_text = str(query or "")
    lowered = query_text.lower()

    category_hits = {category: match_aliases(lowered, aliases) for category, aliases in CATEGORY_ALIASES.items()}
    category_scores = {
        category: len(hits) * 6 + (4 if category in {"Finance", "Cryptocurrency", "News", "GraphQL"} and hits else 0)
        for category, hits in category_hits.items()
    }

    discover_hits = match_aliases(lowered, DISCOVER_TERMS)
    discover_patterns = match_patterns(query_text, STRONG_DISCOVER_PATTERNS)
    fetch_hits = match_aliases(lowered, FETCH_TERMS)
    fetch_patterns = match_patterns(query_text, STRONG_FETCH_PATTERNS)
    latest_hits = match_aliases(lowered, LATEST_TERMS)
    news_hits = match_aliases(lowered, NEWS_TERMS)
    market_hits = match_aliases(lowered, MARKET_TERMS)
    no_auth_hits = match_aliases(lowered, NO_AUTH_TERMS)
    graphql_hits = match_aliases(lowered, CATEGORY_ALIASES["GraphQL"])
    sections = detect_sections(query_text)

    discover_score = len(discover_hits) * 8 + len(discover_patterns) * 20
    fetch_score = len(fetch_hits) * 8 + len(fetch_patterns) * 18 + len(latest_hits) * 4

    if news_hits:
        fetch_score += 10 + len(news_hits) * 3
    if market_hits:
        fetch_score += 10 + len(market_hits) * 3
    if graphql_hits:
        discover_score += 18
    if any(category_hits.get(category) for category in ["Weather", "Geocoding", "Currency Exchange", "Open Data", "Search"]) and not discover_hits:
        fetch_score += 10
    if "api" in lowered and not news_hits and not market_hits:
        discover_score += 8
    if any(phrase in lowered for phrase in ["帮我", "给我", "直接", "现在", "马上"]):
        fetch_score += 6
    if any(phrase in lowered for phrase in ["有哪些", "有没有", "推荐几个", "列几个", "找几个"]):
        discover_score += 6

    action = "fetch"
    if discover_score > fetch_score + 2:
        action = "discover"
    elif graphql_hits and not news_hits and not market_hits:
        action = "discover"

    result_kind = "news"
    if market_hits and len(market_hits) >= len(news_hits):
        result_kind = "market"
    if action == "discover":
        result_kind = "api"

    domains = [category for category, score in sorted(category_scores.items(), key=lambda item: (-item[1], item[0])) if score > 0]
    if not domains and (news_hits or latest_hits):
        domains = ["News"]
    if action == "fetch" and "GraphQL" in domains and len(domains) == 1:
        domains = ["News"]

    if not sections:
        if "Cryptocurrency" in domains:
            sections = ["Business", "Technology"]
        elif "Finance" in domains:
            sections = ["Business"]
        elif result_kind == "news":
            sections = ["World", "US", "Business", "Technology"]

    market_style = None
    for style, aliases in MARKET_STYLE_TERMS.items():
        if match_aliases(lowered, aliases):
            market_style = style
            break

    reasons = unique_list(
        [f"action:{action}"]
        + [f"discover:{hit}" for hit in discover_hits[:4]]
        + [f"fetch:{hit}" for hit in fetch_hits[:4]]
        + [f"latest:{hit}" for hit in latest_hits[:4]]
        + [f"domain:{domain}" for domain in domains[:4]]
        + [f"section:{section}" for section in sections[:4]]
    )

    return {
        "query": query_text,
        "action": action,
        "result_kind": result_kind,
        "domains": domains,
        "category_scores": category_scores,
        "matched_categories": [category for category, hits in category_hits.items() if hits],
        "matched_sections": sections,
        "market_style": market_style,
        "prefer_graphql": bool(graphql_hits),
        "prefer_no_auth": bool(no_auth_hits),
        "wants_latest": bool(latest_hits),
        "query_tokens": significant_tokens(query_text),
        "reasons": reasons,
        "signals": {
            "discover_terms": discover_hits,
            "discover_patterns": discover_patterns,
            "fetch_terms": fetch_hits,
            "fetch_patterns": fetch_patterns,
            "latest_terms": latest_hits,
            "news_terms": news_hits,
            "market_terms": market_hits,
            "no_auth_terms": no_auth_hits,
            "graphql_terms": graphql_hits,
        },
        "scores": {
            "discover": discover_score,
            "fetch": fetch_score,
        },
    }
