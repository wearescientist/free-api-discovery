---
name: free-api-discovery
description: Use when the user wants free or public APIs, GraphQL endpoints, or live results from those sources through natural-language requests. Trigger on requests such as "find a free news API", "look for a crypto data API", "search GraphQL APIs", "help me grab the latest news", "show crypto market movers", or "find a no-key finance API". This skill uses a local combined index plus a direct-result router so large upstream catalogs do not need to be loaded into context.
---

# Free API Discovery

## Overview

Use this skill when the user gives a natural-language request and wants one of two outcomes:

1. Direct results first:
   - latest news
   - crypto market snapshot
   - finance market snapshot
   - a specific stock or coin readout
   - weather and short forecast
   - geocoding and coordinate lookup
   - country profile and basic open data
   - exchange rates and currency conversion
   - quick knowledge lookup
2. API discovery fallback:
   - free API shortlist
   - GraphQL endpoint discovery
   - no-key source discovery

The skill stays local-first:

- `public-api-lists` keeps its original categories such as `News`, `Finance`, `Cryptocurrency`, and `Open Data`
- `graphql-apis` is treated as its own primary category: `GraphQL`
- local raw snapshots and the merged registry live under `assets/`

## Default Entry

Default to the unified router:

```bash
python scripts/fetch_live_results.py --query "<user request>"
```

This router does the following:

- detects broad intent from natural language, including Chinese phrasing handled inside the scripts
- defaults to direct fetch when the user wants live results
- routes the request into a source pool instead of a single source whenever that pool exists
- fetches multiple providers in parallel, then reports source coverage in the JSON output
- turns news results into a Chinese-readable output when possible, keeping the original headline plus a translated title and preview
- falls back to registry discovery when the query is really asking for APIs or GraphQL endpoints
- keeps the response small and source-aware

## Routing Rules

Use `fetch_live_results.py` when the user says things like:

- `help me grab the latest news`
- `show the latest crypto market snapshot`
- `give me Apple stock data`
- `find a free GraphQL market data API`
- `find a free finance news API without a key`

The router is intentionally broad. It should catch intent from:

- action phrasing such as `help me`, `show me`, `grab`, `pull`, `summarize`
- freshness phrasing such as `latest`, `today`, `recent`, `real time`
- news phrasing such as `news`, `headlines`, `stories`, `articles`
- market phrasing such as `market`, `price`, `quote`, `ticker`, `snapshot`, `data`, `signals`
- discovery phrasing such as `api`, `endpoint`, `source`, `provider`, `graphql`, `docs`
- constraints such as `no key`, `no auth`, `without api key`

## What It Fetches Directly

Current direct-result source pools:

- `news.general`
  - aggregates multiple public headline feeds plus `OkSurf`
- `news.crypto`
  - uses multiple public crypto news feeds plus filtered `OkSurf` business and technology headlines when relevant
- `news.finance`
  - aggregates business-oriented public feeds plus `OkSurf` business headlines when relevant
- `weather.current`
  - uses `Open-Meteo` geocoding and forecast APIs
- `geo.lookup`
  - uses `Open-Meteo` geocoding for coordinate and place lookup
- `country.profile`
  - combines `RestCountries` with `Statistics of the World` where relevant
- `currency.fx`
  - uses `ExchangeRate-API` for exchange rates and simple conversions
- `search.instant`
  - uses `Wikipedia` search plus page summaries
- `market.crypto`
  - aggregates `Coinpaprika`, `Coinlore`, `CoinRanking`, `Gate.io`, `Gemini`, and `Blockchain` where applicable
- `market.finance`
  - combines `ValueRay`
  - uses `Stooq` as an additional no-key fallback for stock symbols and broad US market ETF snapshots
  - adds `PredScope` for broader market and event context when relevant
  - adds `Statistics of the World` for macro and country indicator queries when relevant

When there is no good direct match, the router falls back to registry discovery instead of returning empty output.
When a pool is sparse, the JSON output still includes `coverage` so the caller can see how many providers actually succeeded.

## News Output Shape

For news pools, the output keeps the original source fields and adds a more readable Chinese layer:

- `title`
  - translated Chinese headline when translation succeeds
- `title_original`
  - original upstream headline
- `summary`
  - Chinese summary text or Chinese fallback digest
- `content_preview`
  - cleaned upstream preview text when the feed provides one
- `content_preview_zh`
  - translated Chinese preview text when available
- `meta_summary`
  - source, provider, and section summary

This means news queries should no longer look like `title + url only` unless the upstream feed itself is extremely sparse.

## Expanded Examples

- `show me the weather in Shanghai`
- `look up Tokyo coordinates`
- `show USD to CNY exchange rates`
- `give me France population and capital`
- `search what Bitcoin is`

## Discovery-Only Utilities

Use `search_registry.py` when you explicitly want API candidates instead of live results:

```bash
python scripts/search_registry.py --query "free crypto api with no key"
python scripts/search_registry.py --query "graphql market data api"
python scripts/search_registry.py --list-categories
```

## Refresh

Refresh only when needed:

```bash
python scripts/fetch_live_results.py --query "<user request>" --refresh
python scripts/refresh_index.py
```

That updates:

- `assets/registry.json`
- `assets/snapshots/public-api-lists-all.json`
- `assets/snapshots/graphql-apis-apis.json`
- `assets/snapshots/graphql-apis-demos.json`
- `assets/snapshots/graphql-apis-proxies.json`

## References

- Source field notes: `references/sources.md`
