# Free API Discovery

> 一个本地优先的 Codex Skill：把自然语言请求自动路由成“直接抓结果”或“发现免费 API / GraphQL 端点”。

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Codex Skill](https://img.shields.io/badge/Codex-Skill-111111)](#)
[![Local First](https://img.shields.io/badge/Local--First-Registry-0A7E3F)](#)
[![Multi Source](https://img.shields.io/badge/Multi--Source-Aggregation-6C47FF)](#)
[![Chinese News](https://img.shields.io/badge/News-%E4%B8%AD%E6%96%87%E5%8F%AF%E8%AF%BB-FF6B35)](#)

## 这是什么

`Free API Discovery` 不是一个单纯的 API 清单，也不是把几百个仓库条目硬塞进上下文的提示词包。

它更像一个轻量的“数据路由器”与“免费源发现器”：

- 你说人话，它先判断你是要**结果**还是要**源**
- 要结果，就走多源抓取池
- 要源，就查本地索引并返回 API shortlist
- 尽量本地优先，避免把大目录反复塞进模型上下文

一句话说透：

> **它把“找免费 API”和“直接拿结果”这两件事，收进了同一个自然语言入口。**

## 它解决什么问题

公开 API 目录其实很多，但真要用时常常有几个痛点：

- 目录很大，不适合每次整包进上下文
- REST、GraphQL、RSS、市场源的格式完全不统一
- 用户有时要的是“给我结果”，有时要的是“给我源”，很多系统分不清
- 就算抓到了新闻，也常常只剩标题和链接，不像成品

这个 skill 的目标就是把这些断层补上。

## 核心能力

### 1. 自然语言意图识别

它不会只靠几个死关键词，而是尝试识别整句意图。

例如：

- `帮我抓最新新闻`
- `帮我抓最新加密新闻`
- `帮我看下最新加密行情`
- `帮我看下苹果最新美股数据`
- `找几个免费的GraphQL市场数据API`
- `给我免 key 的财经资讯源`

系统会先判断：

- 这是 `fetch` 还是 `discover`
- 更像 `news`、`market`、`finance`、`crypto` 还是 `graphql`
- 是否偏向 `latest / real-time / no key / GraphQL`

### 2. 直接结果模式

如果用户要的是结果，skill 会自动进入抓取池，而不是先丢给你一堆 API 名字。

当前已接好的结果池：

| 池名 | 作用 | 当前来源 |
| --- | --- | --- |
| `news.general` | 通用新闻 | OkSurf、BBC、NPR、New York Times |
| `news.crypto` | 加密新闻 | Cointelegraph、The Block、Decrypt、过滤后的 OkSurf |
| `news.finance` | 财经新闻 | New York Times Business、NPR Business、OkSurf |
| `market.crypto` | 加密市场快照 | Coinpaprika、Coinlore、CoinRanking、Gate.io、Gemini、Blockchain |
| `market.finance` | 个股与大盘上下文 | ValueRay、Stooq、PredScope、Statistics of the World、可选 OkSurf |

### 3. 发现模式

如果用户问的是“有哪些免费 API 可用”，就会退回本地索引层。

比如：

- 免费 API shortlist
- GraphQL 端点发现
- 免 key 源筛选
- 分类列表查询

### 4. 中文可读新闻输出

这版不是只给 `title + url`。

新闻输出现在会尽量带上：

- 中文标题
- 原始标题
- 中文摘要
- 原始预览
- 中文预览
- 来源 / 抓取源 / 分区信息

也就是说，它已经更接近“中文资讯流”，而不是半成品抓取器。

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