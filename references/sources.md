# Source Notes

This skill combines two upstream sources into one local registry.

## public-api-lists

- Repo: `https://github.com/public-api-lists/public-api-lists`
- Primary feed: `https://public-api-lists.github.io/public-api-lists/api/all.json`
- Useful fields: `name`, `url`, `description`, `auth`, `https`, `cors`, `category`
- Strength: broad category coverage and stable machine-readable JSON
- Weakness: many entries still require an API key even when the service is free-tier

## APIs-guru/graphql-apis

- Repo: `https://github.com/APIs-guru/graphql-apis`
- Feeds:
  - `https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/apis.json`
  - `https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/demos.json`
  - `https://raw.githubusercontent.com/APIs-guru/graphql-apis/master/proxies.json`
- Useful fields: `url`, `info.title`, `info.description`, `security`, `externalDocs`
- Strength: explicit GraphQL endpoint discovery with auth hints and docs links
- Weakness: narrow coverage compared with public-api-lists

## Normalization Notes

- Public API entries are normalized as `type = "rest"` and `graphql = false`
- GraphQL entries are normalized as `type = "graphql"` and `graphql = true`
- Security requirements from GraphQL entries are joined into a compact auth summary
- Docs URLs are stored as a list so search can boost entries with inspectable docs
- The registry is intentionally lightweight and is not a crawler or live availability checker

