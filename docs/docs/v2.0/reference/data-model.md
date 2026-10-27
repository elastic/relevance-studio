# Data model

## Common fields

The following fields are used by all documents (except [runs](#runs) which have their own implementation of `@meta`).

**Fields**

- **`@meta`** - An object containing metadata about the document.
- **`@meta.created_at`** - The ISO 8601 (UTC) date and time at which the document was created.
- **`@meta.created_by`** - The name of the user that created the document.
- **`@meta.updated_at`** - The ISO 8601 (UTC) date and time at which the document was last updated.
- **`@meta.updated_by`** - The name of the user that last updated the document.
- **`@meta.created_via`** - The channel through which the document was created: `"server"` (REST API/UI), `"mcp"` (MCP Server), or `"api"` (Python API/worker).
- **`@meta.updated_via`** - The channel through which the document was last updated (same values as `created_via`).
- **`_search`** - An object whose fields are the full text representations of their respective fields in the document.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta.created_at`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.created_by`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.updated_at`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.updated_by`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.created_via`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.updated_via`**|String|Forbidden|Forbidden|Auto-generated|
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

## Workspaces

Elasticsearch index template: [esrs-workspaces](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/workspaces.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`name`** - A human-readable name for the workspace.
- **`index_pattern`** - The corpus for the workspace, expressed as an Elasticsearch [index pattern](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices), which limits the scope of searches to the content deployment to any index within that pattern. Supports the full syntax of index patterns, including wildcards to match patterns of indices, commas to include multiple indices, and colons for cross-cluster search indices.
- **`rating_scale.min`** - The lower bound of the rating scale used by all [judgements](#judgements) in the workspace.
- **`rating_scale.max`** - The upper bound of the rating scale used by all [judgements](#judgements) in the workspace.
- **`params`** - The names of search inputs that can be implemented by [scenarios](#scenarios) and [strategies](#strategies). Essentially, these are the input fields for the search form of your application.
- **`description`** - A human-readable description of the workspace.
- **`tags`** - Arbitrary tags for organizing workspaces.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object|Forbidden|Forbidden|Auto-generated|
|**`name`**|String|Required|Optional||
|**`index_pattern`**|String|Required|Optional||
|**`rating_scale.min`**|Integer|Required|Forbidden|Immutable|
|**`rating_scale.max`**|Integer|Required|Forbidden|Immutable|
|**`tags`**|List of strings|Optional|Optional||
|**`params`**|List of strings|Required|Optional||
|**`description`**|String|Optional|Optional||
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

---

## Conversations

Elasticsearch index template: [esrs-conversations](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/conversations.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`conversation_id`** - A stable identifier for the conversation. This is typically the same as the document `_id`.
- **`title`** - An optional human-readable title for the conversation.
- **`rounds`** - The ordered list of conversational turns.
- **`rounds.id`** - A unique identifier for the round.
- **`rounds.status`** - Optional execution status for the round.
- **`rounds.input.message`** - The user message for the round.
- **`rounds.steps`** - Optional trace steps, including reasoning and tool call/result entries.
- **`rounds.started_at`** - Optional ISO 8601 timestamp for when generation started.
- **`rounds.time_to_first_token`** - Optional latency in milliseconds to first token.
- **`rounds.time_to_last_token`** - Optional latency in milliseconds to completion.
- **`rounds.model_usage`** - Optional model usage metadata (inference id, call count, token counts).
- **`rounds.response.message`** - The assistant response message for the round.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object|Forbidden|Forbidden|Auto-generated|
|**`conversation_id`**|String|Required|Forbidden|Immutable|
|**`title`**|String|Optional|Optional||
|**`rounds`**|List of objects|Optional|Optional||
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

---

## Displays

Elasticsearch index template: [esrs-displays](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/displays.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The UUID of the [workspace](#workspaces) that the display belongs to.
- **`index_pattern`** - The [index pattern](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-multiple-data-streams-indices) that the display handles. Must be a subset of the `index_pattern` of the workspace. When a document from the content deployment matches the index patterns of multiple displays, the display with the more specific pattern will be chosen to render the document.
- **`fields`** - The fields referenced by the Mustache variables in `template.body`. Controls the fields that are included in `_source` when retrieving documents from the content deployment.
- **`template.body`** - The content of the display in Markdown syntax. Use [Mustache variables](https://mustache.github.io/mustache.5.html) with the names of fields from the index pattern to include values from documents. For example, `{{ name.keyword }}` would render the value of the `name.keyword` field in the document.
- **`template.image.position`** - The placement of an optional image for the document. Can be `"top-left"` or `"top-right"`.
- **`template.image.url`** - An optional URL to display an image for the document. Must be reachable from the web browsers of users. Use [Mustache variables](https://mustache.github.io/mustache.5.html) with the names of fields from the index pattern to include values from documents.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object||Forbidden|Forbidden|Auto-generated|
|**`workspace_id`**|String|Required|Required||
|**`index_pattern`**|String|Required|Optional||
|**`fields`**|List of strings|Forbidden|Forbidden|Auto-generated|
|**`template.body`**|String|Optional|Optional||
|**`template.image.position`**|String|Optional|Optional||
|**`template.image.url`**|String|Optional|Optional|Options: `"top-left"`, `"top-right"`|
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

---

## Scenarios

Elasticsearch index template: [esrs-scenarios](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/scenarios.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the scenario belongs to.
- **`name`** - A human-readable name for the scenario.
- **`params`** - The names of search inputs that can be implemented by [strategies](#strategies). Each value must exist in the `params` of the [workspace](#workspaces). Automatically derived from the keys of the `values` field.
- **`tags`** - Arbitrary tags for organizing scenarios.
- **`values`** - An object whose keys are the names of any `params` from the workspace, and the values are the contents of those params for the search scenario.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object||Forbidden|Forbidden|Auto-generated|
|**`workspace_id`**|String|Required|Required||
|**`name`**|String|Required|Optional||
|**`params`**|List of strings|Forbidden|Forbidden|Auto-generated|
|**`tags`**|List of strings|Optional|Optional||
|**`values`**|Object|Required|Forbidden|Immutable|
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

---

## Judgements

Elasticsearch index template: [esrs-judgements](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/judgements.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the judgement belongs to.
- **`scenario_id`** - The `_id` of the [scenario](#scenarios) that the judgement belongs to.
- **`index`** - The name of the index that the judged document belongs to.
- **`doc_id`** - The `_id` of the judged document.
- **`rating`** - The rating of the judgement. Must be within the range of the `rating_scale` of the [workspace](#workspaces).
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object||Forbidden|Forbidden|Auto-generated|
|**`workspace_id`**|String||Required|Required||
|**`scenario_id`**|String||Required|Required||
|**`index`**|String|Required|Required||
|**`doc_id`**|String|Required|Required||
|**`rating`**|Integer|Required|Required||
|**`_search`**|Object||Forbidden|Forbidden|Auto-generated|

---

## Strategies

Elasticsearch index template: [esrs-strategies](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/strategies.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the strategy belongs to.
- **`name`** - A human-readable name for the strategy.
- **`params`** - The names of search inputs that are populated by [scenarios](#scenarios). Each value must exist in the `params` of the [workspace](#workspaces). Automatically derived from the Mustache variables in the `template.body` field.
- **`tags`** - Arbitrary tags for organizing strategies.
- **`template.lang`** - The `"lang"` field of the [search template](https://www.elastic.co/docs/solutions/search/search-templates) of the strategy. Currently only supports `"mustache"`. 
- **`template.body`** - The `"source"` field of the [search template](https://www.elastic.co/docs/solutions/search/search-templates) of the strategy. Use [Mustache variables](https://mustache.github.io/mustache.5.html) with the names of `params` from [scenarios](#scenarios) to indicate where search inputs will be populated. For example, `{{ text }}` would be populated by the `text` param of a scenario.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object||Forbidden|Forbidden|Auto-generated|
|**`workspace_id`**|String||Required|Required||
|**`name`**|String|Required|Optional||
|**`params`**|List of strings|Forbidden|Forbidden|Auto-generated|
|**`tags`**|List of strings|Optional|Optional||
|**`template.lang`**|String|Optional|Optional|Options: `"mustache"`|
|**`template.body`**|String|Optional|Optional||
|**`_search`**|Object||Forbidden|Forbidden|Auto-generated|

---

## Benchmarks

Elasticsearch index template: [esrs-benchmark-configs](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-configs.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the benchmark belongs to.
- **`name`** - A human-readable name for the benchmark.
- **`description`** - A human-readable description of the benchmark.
- **`tags`** - Arbitrary tags for organizing benchmarks.
- **`task.k`** - The value of `k` used for metrics like NDCG.
- **`task.metrics`** - The names of the metrics to include. Supports `"ndcg"`, `"precision"`, `"recall"`, and `"mrr"`.
- **`task.strategies._ids`** - The `_id` fields of [strategy](#strategies) documents to include in [runs](#runs).
- **`task.strategies.tags`** - The `tags` of [strategies](#strategies) to include in [runs](#runs).
- **`task.strategies.docs`** - The `_source` of [strategy](#strategies) documents to include in [runs](#runs). Primarily intended to be used by the strategy testing components of the [UI](docs/{{VERSION}}/reference/architecture.md#ui).
- **`task.scenarios._ids`** - The `_id` fields of [scenario](#scenarios) documents to include in [runs](#runs).
- **`task.scenarios.tags`** - The `tags` of [scenarios](#scenarios) to include in [runs](#runs).
- **`task.scenarios.sample_size`** - The sample size of scenarios to use for large runs. Defaults to `1000`. Allows a maximum of `10000`.
- **`task.scenarios.sample_seed`** - 
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object|Forbidden|Forbidden|Auto-generated|
|**`workspace_id`**|String||Required|Required||
|**`name`**|String|Required|Optional||
|**`description`**|String|Optional|Optional||
|**`tags`**|List of strings|Optional|Optional||
|**`task.k`**|Integer|Required|Forbidden|Immutable|
|**`task.metrics`**|List of strings|Required|Optional|Options: `"ndcg"`, `"precision"`, `"recall"`, `"mrr"`|
|**`task.strategies._ids`**|List of strings|Optional|Optional||
|**`task.strategies.tags`**|List of strings|Optional|Optional||
|**`task.strategies.docs`**|List of objects|Optional|Optional||
|**`task.scenarios._ids`**|List of strings|Optional|Optional||
|**`task.scenarios.tags`**|List of strings|Optional|Optional||
|**`task.scenarios.sample_size`**|Integer|Optional|Optional|Options: `1` to `10000`|
|**`task.scenarios.sample_seed`**|String|Optional|Optional||
|**`_search`**|Object|Forbidden|Forbidden|Auto-generated|

---

## Runs

A run is one execution of a [benchmark](#benchmarks). In v2.0, the storage for a run is split across multiple stores so that the run document stays small and fast to list, while the heavier per-search results and the runtime audit trail live in their own stores:

- **`esrs-benchmark-runs`** (plain index) - One small document per run. Holds the run's status/lifecycle `@meta`, its identifiers, the frozen `task`, a precomputed `summary` of metrics, any `error`, and `took`. This is what list and status views read.
- **`esrs-benchmark-results`** (data stream) - One immutable document per (run × strategy × scenario) search, holding the per-search relevance metrics and hits. This is the queryable detail behind the summary.
- **`esrs-benchmark-runtime-indices`** (data stream) - One immutable document per index used at runtime, holding that index's relevance fingerprint snapshot.
- **`esrs-benchmark-runtime-strategies`** (data stream) - One immutable document per strategy used at runtime, holding the full strategy snapshot.
- **`esrs-benchmark-runtime-scenarios`** (data stream) - One immutable document per scenario used at runtime, holding the full scenario snapshot.
- **`esrs-benchmark-runtime-judgements`** (data stream) - One immutable document per judgement used at runtime, holding the full judgement snapshot. This is the stream that scales with the number of rated documents.
- **`esrs-benchmark-unrated-docs`** (data stream) - One immutable document per document that appeared in the results but had no judgement.
- **`esrs-benchmark-failures`** (data stream) - One immutable document per strategy that had failures during the run.

The runtime audit trail is fanned out into these six per-item data streams — one document per item — rather than a single document per run, so that each collection can be paginated and queried server-side independently. In particular, `esrs-benchmark-runtime-judgements` scales with the number of rated documents and is never loaded whole. Every document is tagged with `run_id`, `workspace_id`, `benchmark_id`, and `@timestamp`, and uses a deterministic `_id` so that migration and retry are idempotent.

A *data stream* is an append-only, time-series oriented abstraction over a set of backing indices. Documents are written with `op_type: create` (never updated in place), and each stream's retention is governed by Data Stream Lifecycle (DLM).

### esrs-benchmark-runs

Elasticsearch index template: [esrs-benchmark-runs](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-runs.json)

**Fields**

- **`@meta.status`** - The status of the run.
    - `"pending"` - Run is waiting to be claimed by a worker.
    - `"running"` - Run has been claimed by a worker.
    - `"completed"` - Run has finished successfully.
    - `"failed"` - Run has stopped due to an error.
    - `"skipped"` - Run has stopped because there are no compatible strategies and scenarios that meet the `task` definition.
- **`@meta.created_at`** - The ISO 8601 (UTC) date and time at which the run was created with a `status` of `"pending"`.
- **`@meta.created_by`** - The name of the user that created the document.
- **`@meta.started_at`** - The ISO 8601 (UTC) date and time at which the run was started.
- **`@meta.started_by`** - The name of the worker that claimed the run.
- **`@meta.stopped_at`** - The ISO 8601 (UTC) date and time at which the run was stopped.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`scenario_id`** - The `_id` fields of [scenarios](#scenarios) that were included in the run.
- **`strategy_id`** - The `_id` fields of [strategies](#strategies) that were included in the run.
- **`task`** - A frozen copy of the `task` field of the [benchmark](#benchmarks) at the time the run was created.
- **`summary`** - A precomputed, aggregated summary of the metrics from the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests. Grouped by `strategy_ids` and `strategy_tags` and grouped again by `scenario_ids` and `scenario_tags`. Stored but not indexed.
- **`error`** - The error that stopped the run, if its status is `"failed"`.
- **`took`** - The duration in milliseconds in which the run had a status of `"running"`.
- **`progress.requests_total`** - The total number of [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests this run will submit: one per (metric × strategy × scenario-with-judgements) combination. Computed once candidates and judgements are resolved, before the first request is submitted.
- **`progress.requests_completed`** - The number of requests submitted so far (`requests_succeeded` + `requests_failed`). Updated incrementally by the worker as batches complete while `@meta.status` is `"running"`, and equal to `requests_total` once the run reaches a terminal status.
- **`progress.requests_succeeded`** - The number of requests that returned a score.
- **`progress.requests_failed`** - The number of requests that errored. A run can still have a status of `"completed"` with a nonzero `requests_failed`, since individual request errors don't abort the run — only an unhandled exception does (which sets `@meta.status` to `"failed"`).
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object|Forbidden|-|Auto-generated|
|**`workspace_id`**|String|Required|-||
|**`benchmark_id`**|String|Required|-||
|**`scenario_id`**|List of strings|Forbidden|-|Auto-generated|
|**`strategy_id`**|List of strings|Forbidden|-|Auto-generated|
|**`task`**|Object|Required|-||
|**`summary`**|Object|Forbidden|-|Auto-generated|
|**`error`**|Object|Forbidden|-|Auto-generated|
|**`took`**|-|Forbidden|-|Auto-generated|
|**`progress`**|Object|Forbidden|-|Auto-generated|
|**`_search`**|Object|Forbidden|-|Auto-generated|

*Note: Runs don't have an Update API. [Workers](docs/{{VERSION}}/reference/architecture.md#worker) handle the updates automatically.*

### esrs-benchmark-results

Elasticsearch index template: [esrs-benchmark-results](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-results.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per (run × strategy × scenario) search, so the aggregated `summary` on the run document can be traced back to the underlying per-search results.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that produced this result.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`strategy_id`** - The `_id` of the [strategy](#strategies) used for this search.
- **`scenario_id`** - The `_id` of the [scenario](#scenarios) used for this search.
- **`metrics.dcg`** - The Discounted Cumulative Gain for this search.
- **`metrics.err`** - The Expected Reciprocal Rank for this search.
- **`metrics.mrr`** - The Mean Reciprocal Rank for this search.
- **`metrics.ndcg`** - The Normalized Discounted Cumulative Gain for this search.
- **`metrics.precision`** - The precision for this search.
- **`metrics.recall`** - The recall for this search.
- **`hits`** - The ranked hits returned for this search.
- **`hits.hit._id`** - The `_id` of the hit document.
- **`hits.hit._index`** - The index that the hit document belongs to.
- **`hits.hit._score`** - The relevance score assigned to the hit by the strategy.
- **`hits.hit._ignored`** - The fields of the hit document that were ignored at index time, if any.
- **`hits.rating`** - The judged rating for the hit, if a judgement exists.
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the result was written.

### esrs-benchmark-runtime-indices

Elasticsearch index template: [esrs-benchmark-runtime-indices](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-runtime-indices.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per index used at runtime for the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`index`** - The name of the index used at runtime.
- **`item`** - The index's relevance fingerprint snapshot.
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.

### esrs-benchmark-runtime-strategies

Elasticsearch index template: [esrs-benchmark-runtime-strategies](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-runtime-strategies.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per [strategy](#strategies) used at runtime.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`strategy_id`** - The `_id` of the [strategy](#strategies) that this document captures.
- **`item`** - The full strategy snapshot (`name`, `tags`, `template`, `_fingerprint`, `@meta`, …).
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.

### esrs-benchmark-runtime-scenarios

Elasticsearch index template: [esrs-benchmark-runtime-scenarios](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-runtime-scenarios.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per [scenario](#scenarios) used at runtime.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`scenario_id`** - The `_id` of the [scenario](#scenarios) that this document captures.
- **`item`** - The full scenario snapshot (`values`, `_fingerprint`, …).
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.

### esrs-benchmark-runtime-judgements

Elasticsearch index template: [esrs-benchmark-runtime-judgements](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-runtime-judgements.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per [judgement](#judgements) used at runtime. This is the stream that scales with the number of rated documents.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`judgement_id`** - The `_id` of the [judgement](#judgements) that this document captures.
- **`scenario_id`** - The `_id` of the [scenario](#scenarios) that the judgement belongs to, used for filtered pagination.
- **`item`** - The full judgement snapshot (`rating`, `index`, `doc_id`, `_fingerprint`, …).
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.

### esrs-benchmark-unrated-docs

Elasticsearch index template: [esrs-benchmark-unrated-docs](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-unrated-docs.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per document that appeared in the results but had no judgement.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`doc_id`** - The `_id` of the unrated document.
- **`doc_index`** - The index that the unrated document belongs to.
- **`count`** - The number of times the unrated document appeared across the run's searches.
- **`strategies`** - The `_id` fields of the [strategies](#strategies) whose searches returned the unrated document.
- **`scenarios`** - The `_id` fields of the [scenarios](#scenarios) whose searches returned the unrated document.
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.

### esrs-benchmark-failures

Elasticsearch index template: [esrs-benchmark-failures](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmark-failures.json)

An immutable [data stream](https://www.elastic.co/docs/manage-data/data-store/data-streams). It holds one document per [strategy](#strategies) that had failures during the run.

**Fields**

- **`run_id`** - The `_id` of the [run](#esrs-benchmark-runs) that this document belongs to.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the run belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the run belongs to.
- **`strategy_id`** - The `_id` of the [strategy](#strategies) that had failures.
- **`failures`** - The per-strategy failure blob for that strategy.
- **`@timestamp`** - The ISO 8601 (UTC) date and time at which the document was written.