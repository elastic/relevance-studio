# Data model

Source of truth: `docs/docs/v1.2/reference/data-model.md` and `src/server/models/*.py`.
When writing or updating any asset, check this file first for which fields are
server-computed or immutable — sending them anyway will fail validation (the models use
`extra: forbid`).

## Common fields (all assets except evaluations)

- `@meta.created_at` / `@meta.created_by` / `@meta.updated_at` / `@meta.updated_by` —
  auto-generated. Forbidden on create/update requests.
- `@meta.created_via` / `@meta.updated_via` — the channel: `"server"` (REST/UI), `"mcp"`
  (MCP Server — this is what external agents write), or `"api"` (Python API/worker).
  Auto-generated.
- `_search` — full-text representation of the document's searchable fields. Auto-generated.

## Workspaces

- `name` (required on create, optional on update)
- `index_pattern` (required, optional on update) — the content index pattern. Supports
  wildcards, commas, and cross-cluster syntax.
- `rating_scale.min` / `rating_scale.max` (required on create, **immutable** — forbidden on
  update)
- `params` (required on create, optional on update) — list of search-input names (e.g.
  `["text"]`) shared by scenarios and strategies.
- `description` (optional) — markdown; use it to capture use case, audience, constraints,
  rating rubric, and content profile (see `workspace-bootstrap`, `judgement-rubric`,
  `content-profiling` skills).
- `tags` (optional)

Deleting a workspace removes **all** assets in it (displays, scenarios, judgements,
strategies, benchmarks, evaluations).

## Displays

- `workspace_id` (required)
- `index_pattern` (required, optional on update) — must be a subset of the workspace's
  pattern. The most specific matching pattern wins when displays overlap.
- `fields` — **server-computed**, forbidden as input. Derived from Mustache variables in
  `template.body` and `template.image.url`.
- `template.body` (optional) — Markdown with Mustache field references.
- `template.image.url` / `template.image.position` (optional) — `position` is
  `"top-left"` or `"top-right"`.

## Scenarios

- `workspace_id` (required)
- `name` (required on create, optional on update)
- `values` (required on create, **immutable** — forbidden on update) — object keyed by
  workspace `params`.
- `params` — **server-computed** from `values.keys()`. Forbidden as input.
- `tags` (optional)

The MCP tool `scenarios_create` takes **no `_id`** parameter. The document `_id` is
deterministically derived from `[workspace_id, values]` — see `gotchas.md`.

Deleting a scenario removes its judgements.

## Judgements

- `workspace_id`, `scenario_id`, `index`, `doc_id`, `rating` — all required. `rating` must
  fall within the workspace's `rating_scale`.
- No separate create/update split at the model level: `judgements_set` upserts.

## Strategies

- `workspace_id` (required)
- `name` (required on create, optional on update)
- `template.lang` (optional, default `"mustache"`, only value currently supported)
- `template.source` (optional) — a **JSON string** (not an object) holding an Elasticsearch
  Search API body (`query` or `retriever`), with Mustache placeholders for scenario params.
- `params` — **server-computed** from the Mustache variables in `template.source`. Never set
  it manually.
- `tags` (optional)

## Benchmarks

- `workspace_id` (required)
- `name` (required on create, optional on update)
- `description`, `tags` (optional)
- `task.k` (required on create, **immutable** — forbidden on update) — evaluation depth,
  default `10`.
- `task.metrics` (required on create, optional on update) — any of `"ndcg"`, `"precision"`,
  `"recall"`, `"mrr"`.
- `task.strategies._ids` / `task.strategies.tags` (optional) — selection filters.
- `task.scenarios._ids` / `task.scenarios.tags` (optional) — selection filters.
- `task.scenarios.sample_size` (optional, default `1000`, max `10000`) — random sample size
  when more scenarios match than this.
- `task.scenarios.sample_seed` (optional) — set for reproducible sampling across runs.

Deleting a benchmark removes its evaluations.

## Evaluations

No update API — a worker owns all post-create mutation.

- `@meta.status` — `"pending"` → `"running"` → `"completed"` | `"failed"` | `"skipped"`.
- `workspace_id`, `benchmark_id` (required on create)
- `task` — snapshot of the benchmark's task definition at creation time.
- `scenario_id` / `strategy_id` — **server-computed** lists of what was actually included.
- `summary` — **server-computed** metrics grouped by `strategy_id`/`strategy_tag` and
  `scenario_id`/`scenario_tag`.
- `results` — **server-computed** raw rank-eval results.
- `runtime` — **server-computed** snapshot of the scenarios/strategies/judgements/index
  state used at run time. Useful for diffing confounds between two evaluations.
- `unrated_docs` — **server-computed** list of documents returned by rank-eval that had no
  judgement, sorted by frequency.
- `took` — duration in milliseconds while status was `"running"`.
