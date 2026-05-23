# Free API Discovery

> A local-first Codex skill that turns natural-language requests into live results or free API discovery.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Skill](https://img.shields.io/badge/Codex-Skill-111111)](#)
[![Local First](https://img.shields.io/badge/Local--First-Registry-0A7E3F)](#)
[![Multi Source](https://img.shields.io/badge/Multi--Source-Aggregation-6C47FF)](#)
[![Chinese Output](https://img.shields.io/badge/News-Chinese%20Readable-FF6B35)](#)

Free API Discovery is a practical skill for people who want two things from the same natural-language prompt:

1. Direct answers, such as latest news, crypto market snapshots, finance market snapshots, or stock readouts
2. Free API discovery, such as no-key API shortlists and GraphQL endpoint lookup

It is built to stay lightweight in context:

- the large API catalogs live in a local registry
- the router decides whether to fetch results or discover sources
- direct-result pools aggregate multiple providers instead of relying on a single source
- news output is transformed into Chinese-readable headlines and previews when possible

## Why This Exists

Most public API lists are good for browsing, but awkward to use in real work:

- too many entries to load into model context every time
- mixed formats across REST and GraphQL sources
- weak routing between "I need data now" and "I need an API to build with"
- poor user experience when the final output is just raw titles or URLs

This skill closes that gap.

## What It Does

### 1. Natural-language routing

The router tries to understand intent instead of waiting for rigid commands.

Examples:

- `help me grab the latest news`
- `show me the latest crypto market snapshot`
- `give me Apple stock data`
- `find a free GraphQL market data API`
- `find a finance API without a key`
- `帮我抓最新加密新闻`
- `帮我看下苹果最新美股数据`
- `找几个免费的GraphQL市场数据API`

### 2. Direct result mode

When the query is asking for results, the skill routes into a fetch pool:

| Pool | What it returns | Current providers |
| --- | --- | --- |
| `news.general` | general headlines | OkSurf, BBC, NPR, New York Times |
| `news.crypto` | crypto news | Cointelegraph, The Block, Decrypt, filtered OkSurf |
| `news.finance` | finance and business news | New York Times Business, NPR Business, OkSurf |
| `market.crypto` | crypto market snapshot | Coinpaprika, Coinlore, CoinRanking, Gate.io, Gemini, Blockchain |
| `market.finance` | stock snapshots and broad market context | ValueRay, Stooq, PredScope, Statistics of the World, optional OkSurf context |

### 3. Discovery mode

When the query is really asking for sources, the skill falls back to the local API registry:

- free API shortlist
- GraphQL endpoint discovery
- no-key source discovery
- category listing

### 4. Chinese-readable news output

For news pools, the output is no longer just `title + url`.

Each result can include:

- translated Chinese title
- original title
- translated summary
- original preview
- Chinese preview
- source and provider metadata

## Architecture

```text
Natural-language query
        |
        v
 intent_router.py
        |
        +--> fetch_live_results.py ----> source pools ----> normalized results
        |
        +--> search_registry.py -------> local registry ----> API shortlist

public-api-lists + graphql-apis
        |
        v
  refresh_index.py
        |
        v
 assets/registry.json + local snapshots
```

## Local-first Data Model

This skill combines two upstream catalogs into one local registry:

- `public-api-lists/public-api-lists`
- `APIs-guru/graphql-apis`

Current local shape:

- merged registry
- raw source snapshots
- normalized category and auth fields
- GraphQL treated as its own primary category

This avoids stuffing large upstream datasets into prompt context every time.

## Quick Start

### Direct results

```bash
python scripts/fetch_live_results.py --query "帮我抓最新加密新闻"
python scripts/fetch_live_results.py --query "帮我看下最新加密行情"
python scripts/fetch_live_results.py --query "帮我看下苹果最新美股数据"
```

### API discovery

```bash
python scripts/search_registry.py --query "free crypto api with no key"
python scripts/search_registry.py --query "graphql market data api"
python scripts/search_registry.py --list-categories
```

### Refresh the local registry

```bash
python scripts/refresh_index.py
```

## Example Output

### Crypto news

```json
{
  "mode": "fetch",
  "pool": "news.crypto",
  "coverage": {
    "provider_count": 3
  },
  "results": [
    {
      "title": "价格预测 5/22：BTC、ETH、BNB、XRP、SOL、DOGE、HYPE、ADA、ZEC、BCH",
      "summary": "比特币被抛售至 76,000 美元，给了空头重新控制加密货币市场的机会。与此同时，HYPE 等山寨币创下新高。",
      "title_original": "Price predictions 5/22: BTC, ETH, BNB, XRP, SOL, DOGE, HYPE, ADA, ZEC, BCH"
    }
  ]
}
```

### GraphQL discovery

```json
{
  "mode": "discover",
  "results": [
    {
      "name": "Bitquery",
      "primary_category": "GraphQL",
      "categories": ["GraphQL", "Cryptocurrency"],
      "url": "https://graphql.bitquery.io"
    }
  ]
}
```

## Repository Layout

```text
free-api-discovery/
├── README.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── assets/
│   ├── registry.json
│   └── snapshots/
├── references/
│   └── sources.md
└── scripts/
    ├── fetch_live_results.py
    ├── intent_router.py
    ├── refresh_index.py
    └── search_registry.py
```

## Design Choices

### Local registry instead of giant prompt payloads

The catalogs are stored locally, searched locally, and only the useful shortlist or result set is surfaced.

### Multi-source aggregation instead of single-source pretending

The fetch layer reports provider coverage explicitly, so the caller can see whether a result came from one source or many.

### Fallbacks over fragile purity

Some free providers are noisy or rate-limited. The skill uses fallback providers and retry logic to avoid collapsing when one source has a bad moment.

## Known Boundaries

- This is a Codex skill, not a standalone hosted API service
- some upstream sources can still return SSL errors, empty payloads, or rate limits
- finance market output is more stable now because `Stooq` is used as a no-key fallback, but upstream variation still exists
- news output uses feed previews, not full article body extraction
- Chinese news summaries are lightweight machine translation plus cleanup, not editorial rewriting

## Good Fit

This project is a good fit if you want:

- a local-first API directory router
- free and public source discovery
- lightweight live result fetching
- natural-language search over REST and GraphQL sources
- a better user experience than raw API catalog browsing

## Not the Goal

This project is not trying to be:

- a universal production data platform
- a full article crawler
- a perfect market terminal
- an exhaustive wrapper for every API in the registry

## Credits

Upstream source catalogs:

- `public-api-lists/public-api-lists`
- `APIs-guru/graphql-apis`

## License

No license has been added yet. If you want to open this for reuse, add one before wider distribution.
