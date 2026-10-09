# MCP tools

Source of truth: `src/server/fastmcp.py`, `docs/docs/v1.2/reference/mcp-tools.md`. Tool
input/output generally mirrors the REST API and the data model in `data-model.md`. Refer to
tools by bare name in backticks (e.g. `` `scenarios_search` ``) — never with a client-specific
prefix, since that prefix differs between the Claude Code plugin connection and the Desktop
connector.

## Conversations (global, not workspace-scoped)

`conversations_search`, `conversations_get`, `conversations_create(doc, _id=None)`,
`conversations_update(_id, doc_partial)`, `conversations_delete`

## Workspaces

`workspaces_search`, `workspaces_get`, `workspaces_create(doc, _id=None)`,
`workspaces_update`, `workspaces_delete`

## Displays

`displays_search(workspace_id, ...)`, `displays_get`, `displays_create`, `displays_update`,
`displays_delete`

## Scenarios

`scenarios_search(workspace_id, ...)`, `scenarios_tags`, `scenarios_get`,
`scenarios_create(doc)` — **no `_id` parameter**, `scenarios_update`, `scenarios_delete`

## Judgements

- `judgements_search(workspace_id, scenario_id, index_pattern, query={}, query_string="*", filter=None, sort=None, _source=None)`
  - `filter` ∈ `"rated"`, `"rated-ai"`, `"rated-human"`, `"unrated"`, `"all"`.
  - `query` is a full Elasticsearch query DSL object. If provided, it **overrides**
    `query_string` entirely (the server does `body.update(query)`).
  - `sort` ∈ `"match"`, `"rating-newest"`, `"rating-oldest"`.
  - `_source` supports `includes`/`excludes` — set `includes` from a display's `fields`.
- `judgements_set(workspace_id, scenario_id, index, doc_id, rating)` — upserts a judgement.
- `judgements_unset(_id)` — deletes a judgement.

## Strategies

`strategies_search`, `strategies_tags`, `strategies_get`, `strategies_create`,
`strategies_update`, `strategies_delete`

## Benchmarks

`benchmarks_search`, `benchmarks_tags`,
`benchmarks_make_candidate_pool(workspace_id, task)` — preview which strategies/scenarios a
task would include, `benchmarks_get`, `benchmarks_create`, `benchmarks_update`,
`benchmarks_delete`

## Evaluations

- `evaluations_search`, `evaluations_get`, `evaluations_delete`
- `evaluations_create(workspace_id, benchmark_id, task)` — creates a **pending** evaluation.
  A background worker claims and runs it; poll `evaluations_get`.
- `evaluations_run(evaluation, store_results=False)` — synchronous. `evaluation` requires
  `workspace_id` and `task`; `benchmark_id` is optional. Defaults to a dry run
  (`store_results=False` — nothing is persisted unless you pass `True`).

## Content

- `content_search(index_patterns, body)` — passes `body` straight to Elasticsearch. No
  server-side `_source` filtering — you must include it yourself.
- `content_aliases`
- `content_mappings_browse` — flattened field→type map (multi-fields collapsed).

## Setup

`setup_check` — returns `version` (the server's `src/server/VERSION`), `deployment` info,
index-template/upgrade state. `setup_run` — applies index templates/migrations.

## Utilities

- `get_base64_image_from_url(url, max_size=50)` — fetches and downsizes an image to save
  tokens.
- `healthz_mcp` — health check, exempt from auth (along with the `/healthz` HTTP route).

## HTTP-only (no MCP tool)

- Agent API (`/api/chat*`) — streaming, client-specific.
- Upgrade API (`POST /api/upgrade`) — never attempt this through MCP; tell the user to run
  it from the UI or via a direct HTTP call.
