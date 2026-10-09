# Gotchas

Traps verified against the server code (`src/server/`). Read this before any non-trivial
operation — these are the mistakes that produce confusing or silently wrong results.

- **`evaluations_run` defaults to a dry run.** `store_results` defaults to `False`
  (`src/server/api/evaluations.py`). Nothing is persisted unless you explicitly pass
  `store_results=True`. Never imply to the user that a dry-run result was saved.
- **`evaluations_create` only creates a pending evaluation.** A background worker
  (`src/server/worker.py`) polls for pending evaluations and runs them asynchronously —
  it may take seconds or minutes. Poll `evaluations_get` to check completion; don't assume
  it's done immediately.
- **A benchmark's `task.k` can't be changed after creation.** It's immutable on update —
  the server rejects the field outright. Confirm `k` explicitly before creating a benchmark.
- **Scenarios with no judgements rated above 0 are silently excluded from benchmarks.**
  Check judgement coverage before expecting a scenario to show up in results (see
  `judgement-audit` skill).
- **A strategy only pairs with a scenario if every strategy param exists in the scenario's
  params.** Mismatched params mean silent exclusion, not an error.
- **Strategy `params` is computed automatically from `template.source`.** Never set it
  manually — it's derived server-side from the Mustache variables in the template.
  `template.source` must be a JSON **string** (not an object) with Mustache placeholders,
  and it must use at least one workspace param.
- **Benchmarks with more than 1,000 scenarios sample randomly** (`sample_size`, default
  1000, max 10000). Set `sample_seed` for comparable runs across evaluations.
- **`task.rank_eval_batch_size` / `task.rank_eval_batch_delay`** (milliseconds) throttle load
  against the content cluster's `_rank_eval` endpoint during evaluation.
- **`content_search` passes `body` straight to Elasticsearch** with no server-side `_source`
  filtering. Omitting `_source.includes` can return huge vector or metadata fields.
- **Cascading deletes:** `workspaces_delete` removes every asset in the workspace;
  `scenarios_delete` removes its judgements; `benchmarks_delete` removes its evaluations.
  Always confirm before deleting, and tell the user what will cascade.
- **The Upgrade API (`POST /api/upgrade`) and Agent API are HTTP-only** — there is no MCP
  tool for either. Don't attempt the upgrade through MCP tools; tell the user to run it from
  the UI or via a direct HTTP call.
- **Writes made through MCP are stamped `@meta.created_via` / `updated_via = "mcp"`.** The
  `judgements_search` `rated-ai` filter matches documents where `@meta.updated_via == "mcp"`
  **or** `@meta.updated_by == "ai"` (`src/server/api/judgements.py`) — either condition
  qualifies, it's not a single simple equality.
- **`get_base64_image_from_url` downsizes images** to `max_size` (default 50px) to save
  tokens — don't expect full resolution.
- **`scenarios_create` takes no `_id`**, unlike `workspaces_create`, `displays_create`,
  `strategies_create`, and `benchmarks_create`. Its document `_id` is deterministically
  derived from `[workspace_id, values]` (`src/server/api/scenarios.py`), so re-creating a
  scenario with the same workspace and values **overwrites** the existing document rather
  than erroring or duplicating. Judgements use the same deterministic-ID approach, keyed on
  `[workspace_id, scenario_id, index, doc_id]`.
- **`AUTH_ENABLED=false` ignores the `Authorization` header entirely** — it isn't validated,
  just never inspected (`src/server/mcp_auth_middleware.py`). The plugin's `auth_header`
  config can be left blank for an auth-disabled deployment; the server never looks at it.
- **The plugin's `auth_header` config holds a full header value, not just a key.** It
  accepts whatever scheme the deployment uses — `ApiKey <base64 id:api_key>`,
  `Basic <base64 username:password>`, or `Bearer <base64 id:api_key>` — because the MCP
  auth middleware (`src/server/mcp_auth.py`) parses all three from one `Authorization`
  header. Don't assume ApiKey is the only supported scheme.
- **Minimum server version for this plugin is `1.2.4`.** Earlier versions ship a broken
  `workspaces_update` JSON schema for partial updates (fixed by the server commit that
  shipped in v1.2.4). `connect-and-verify` checks `setup_check`'s `version` field against
  this floor.
