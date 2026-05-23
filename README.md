# Free API Discovery

> 一个本地优先的 Codex Skill：把自然语言请求自动路由成“直接抓结果”或“发现免费 API / GraphQL 端点”。

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111111)](#)
[![Local First](https://img.shields.io/badge/Local--First-Registry-0A7E3F)](#)
[![Multi Source](https://img.shields.io/badge/Multi--Source-Aggregation-6C47FF)](#)
[![Chinese News](https://img.shields.io/badge/News-%E4%B8%AD%E6%96%87%E5%8F%AF%E8%AF%BB-FF6B35)](#)

## 核心优势

`Free API Discovery` 的重点不是“让 AI 知道更多 API 名字”，而是把搜索和抓取变成一个稳定、低成本、可复用的工具层。

- **稳定**：固定走本地索引、固定路由规则、固定输出结构，适合反复调用。
- **省 token**：几百个 API 目录保存在本地，查询时只把少量候选或结果交给模型。
- **可自动化**：适合接入定时任务、日报、监控、内容发布和 agent 工作流。

一句话说透：

> **直接问 AI 适合临时回答；这个 skill 适合高频、稳定、省 token 地查数据和找 API。**

## 两类功能

### 1. 直接抓取数据

当用户要的是“结果”时，skill 会自动进入抓取池，直接返回结构化数据，而不是先给一堆 API 名字。

典型请求：

- `帮我抓最新新闻`
- `帮我抓最新加密新闻`
- `帮我看下最新加密行情`
- `帮我看下苹果最新美股数据`
- `帮我看下上海天气`
- `100 usd to cny`
- `比特币是什么`

当前已接好的直抓池：

| 池名 | 作用 | 当前来源 |
| --- | --- | --- |
| `news.general` | 通用新闻 | OkSurf、BBC、NPR、New York Times |
| `news.crypto` | 加密新闻 | Cointelegraph、The Block、Decrypt、过滤后的 OkSurf |
| `news.finance` | 财经新闻 | New York Times Business、NPR Business、OkSurf |
| `weather.current` | 当前天气与短期预报 | Open-Meteo Geocoding、Open-Meteo Forecast |
| `geo.lookup` | 坐标与地点查询 | Open-Meteo Geocoding |
| `country.profile` | 国家基础资料与宏观指标 | RestCountries、Statistics of the World |
| `currency.fx` | 汇率与简单换算 | ExchangeRate-API |
| `search.instant` | 百科型知识快查 | Wikipedia Search、Wikipedia Summary |
| `market.crypto` | 加密市场快照 | Coinpaprika、Coinlore、CoinRanking、Gate.io、Gemini、Blockchain |
| `market.finance` | 个股与大盘上下文 | ValueRay、Stooq、PredScope、Statistics of the World、可选 OkSurf |

新闻类输出会尽量给出中文标题、中文摘要、原始标题、来源链接和 `coverage`，方便判断这次到底覆盖了几个源。

### 2. 提供 API 检索

当用户要的是“源”时，skill 会查询本地 API 索引，返回免费 API / GraphQL endpoint shortlist。

典型请求：

- `找几个免费的GraphQL市场数据API`
- `给我免 key 的财经资讯源`
- `找 free crypto api with no key`
- `列一下可用分类`

索引数据来自：

- `public-api-lists/public-api-lists`
- `APIs-guru/graphql-apis`

它会按分类、auth、GraphQL 标记、no-key 偏好、关键词相关度做筛选，避免把完整大目录塞进上下文。

## 整体结构

```text
自然语言请求
      |
      v
intent_router.py
      |
      +--> fetch_live_results.py ----> 多源抓取池 ----> 标准化结果
      |
      +--> search_registry.py -------> 本地索引 -------> API shortlist

public-api-lists + graphql-apis
      |
      v
refresh_index.py
      |
      v
assets/registry.json + snapshots/
```

## 本地优先的数据层

这个 skill 当前整合了两个上游目录源：

- `public-api-lists/public-api-lists`
- `APIs-guru/graphql-apis`

本地会保留：

- 统一后的 `registry.json`
- 原始快照 `snapshots/*`
- 标准化分类、auth、docs、GraphQL 标记

这意味着：

- 大目录不需要反复进模型上下文
- 查询时先走本地索引
- 真正对外暴露给模型的只有少量候选或最终结果

## 快速开始

### 直接抓结果

```bash
python scripts/fetch_live_results.py --query "帮我抓最新加密新闻"
python scripts/fetch_live_results.py --query "帮我看下最新加密行情"
python scripts/fetch_live_results.py --query "帮我看下苹果最新美股数据"
python scripts/fetch_live_results.py --query "帮我看下上海天气"
python scripts/fetch_live_results.py --query "查一下北京坐标"
python scripts/fetch_live_results.py --query "100 usd to cny"
python scripts/fetch_live_results.py --query "比特币是什么"
```

### 查找免费 API / GraphQL 源

```bash
python scripts/search_registry.py --query "free crypto api with no key"
python scripts/search_registry.py --query "graphql market data api"
python scripts/search_registry.py --list-categories
```

### 刷新本地索引

```bash
python scripts/refresh_index.py
```

## 效果示例

### 加密新闻

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

### GraphQL 发现

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

### 天气直出

```json
{
  "mode": "fetch",
  "pool": "weather.current",
  "coverage": {
    "provider_count": 2
  },
  "results": [
    {
      "title": "上海 | 上海市 | 中国",
      "summary": "晴 | 当前 24.1°C | 体感 24.6°C | 湿度 72% | 风速 11.4 km/h"
    }
  ]
}
```

### 国家资料直出

```json
{
  "mode": "fetch",
  "pool": "country.profile",
  "coverage": {
    "provider_count": 2
  },
  "results": [
    {
      "title": "France",
      "summary": "首都 Paris | 地区 Europe / Western Europe | 人口 68,373,433 | 面积 551,695 km²"
    }
  ]
}
```

## 目录结构

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

## 设计取向

### 本地索引，不走巨型提示词

大目录存在本地，检索也先在本地做，只有 shortlist 或结果集才会上浮。

### 多源聚合，不搞单源伪客观

抓取层会明确输出 `coverage`，告诉你这次到底成功抓到了几个源，而不是假装结果天然可靠。

### 有兜底，不追求脆弱纯洁

免费源天然有抖动、限流、空返回，所以这里更偏工程实用主义：

- 新闻源可多源并发
- 行情源有 fallback
- 股票数据增加了 `Stooq` 兜底
- 大盘上下文也有 ETF 快照兜底

## 适合什么场景

这个项目比较适合你拿来做：

- 本地优先的 API 路由层
- 免费 / 公共源发现工具
- 轻量资讯聚合器
- 生活与知识类直查入口
- REST + GraphQL 混合检索入口
- 面向中文用户的资讯抓取 skill

## 不适合期待它做什么

它目前并不是：

- 一个通用生产级数据平台
- 一个全文新闻爬虫
- 一个完整市场终端
- 对目录里每一个 API 都做了统一封装的全量 SDK

## 已知边界

- 这是一个 Codex Skill，不是托管 SaaS
- 上游免费源仍然可能出现 SSL 抖动、空返回、限流
- 新闻输出基于 feed preview，不是全文正文抽取
- 中文摘要是轻量翻译 + 清洗，不是人工改写
- 金融类结果现在已经更稳，但上游免费源波动依然存在

## 上游来源

- `public-api-lists/public-api-lists`
- `APIs-guru/graphql-apis`

## License

当前仓库还没有补 `LICENSE`。如果你准备长期公开分发，建议下一步补上。
