# Data model

## Common fields

The following fields are used by all documents (except [evaluations](#evaluations) which have their own implementation of `@meta`).

**Fields**

- **`@meta`** - An object containing metadata about the document.
- **`@meta.created_at`** - The ISO 8601 (UTC) date and time at which the document was created.
- **`@meta.created_by`** - The name of the user that created the document.
- **`@meta.updated_at`** - The ISO 8601 (UTC) date and time at which the document was last updated.
- **`@meta.updated_by`** - The name of the user that last updated the document.
- **`_search`** - An object whose fields are the full text representations of their respective fields in the document.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta.created_at`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.created_by`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.updated_at`**|String|Forbidden|Forbidden|Auto-generated|
|**`@meta.updated_by`**|String|Forbidden|Forbidden|Auto-generated|
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

Elasticsearch index template: [esrs-benchmarks](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/benchmarks.json)

**Fields**

- **`@meta`** - Implements the [common field](#common-fields) for `@meta`.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the benchmark belongs to.
- **`name`** - A human-readable name for the benchmark.
- **`description`** - A human-readable description of the benchmark.
- **`tags`** - Arbitrary tags for organizing benchmarks.
- **`task.k`** - The value of `k` used for metrics like NDCG.
- **`task.metrics`** - The names of the metrics to include. Supports `"ndcg"`, `"precision"`, `"recall"`, and `"mrr"`.
- **`task.strategies._ids`** - The `_id` fields of [strategy](#strategies) documents to include in [evaluations](#evaluations).
- **`task.strategies.tags`** - The `tags` of [strategies](#strategies) to include in [evaluations](#evaluations).
- **`task.strategies.docs`** - The `_source` of [strategy](#strategies) documents to include in [evaluations](#evaluations). Primarily intended to be used by the strategy testing components of the [UI](docs/{{VERSION}}/reference/architecture.md#application).
- **`task.scenarios._ids`** - The `_id` fields of [scenario](#scenarios) documents to include in [evaluations](#evaluations).
- **`task.scenarios.tags`** - The `tags` of [scenarios](#scenarios) to include in [evaluations](#evaluations).
- **`task.scenarios.sample_size`** - The sample size of scenarios to use for large evaluations. Defaults to `1000`. Allows a maximum of `10000`.
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

## Evaluations

Elasticsearch index template: [esrs-evaluations](https://github.com/elastic/relevance-studio/blob/main/src/server/elastic/index_templates/evaluations.json)

**Fields**

- **`@meta.status`** - The status of the evaluation.
    - `"pending"` - Evaluation is waiting to be claimed by a worker.
    - `"running"` - Evaluation has been claimed by a worker.
    - `"completed"` - Evaluation has finished successfully.
    - `"failed"` - Evaluation has stopped due to an error.
    - `"skipped"` - Evaluation has stopped because there are no compatible strategies and scenarios that meet the `task` definition.
- **`@meta.created_at`** - The ISO 8601 (UTC) date and time at which the evaluation was created with a `status` of `"pending"`.
- **`@meta.created_by`** - The name of the user that created the document.
- **`@meta.started_at`** - The ISO 8601 (UTC) date and time at which the evaluation was started.
- **`@meta.started_by`** - The name of the worker that claimed the evaluation.
- **`@meta.stopped_at`** - The ISO 8601 (UTC) date and time at which the evaluation was stopped.
- **`workspace_id`** - The `_id` of the [workspace](#workspaces) that the evaluation belongs to.
- **`benchmark_id`** - The `_id` of the [benchmark](#benchmarks) that the evaluation belongs to.
- **`scenario_id`** - The `_id` fields of [scenarios](#scenarios) that were included in the evaluation.
- **`strategy_id`** - The `_id` fields of [strategies](#strategies) that were included in the evaluation.
- **`task`** - The contents of the `task` field of the [benchmark](#benchmarks) when the evaluation was created.
- **`summary`** - A summary of the metrics from the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests. Grouped by `strategy_ids` and `strategy_tags` and grouped again by `scenario_ids` and `scenario_tags`.
- **`results`** - The results of the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests.
- **`runtime`** - The contents of the indices, scenarios, judgements, and strategies used at runtime for the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests.
- **`unrated_docs`** - The documents from the results of the [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) requests that had no judgements.
- **`took`** - The duration in milliseconds in which the evaluation had a status of `"running"` status.
- **`_search`** - Implements the [common field](#common-fields) for `_search`.

**Constraints**

|Field|Type|Create|Update|Notes|
|-----|----|------|------|-----|
|**`@meta`**|Object|Forbidden|-|Auto-generated|
|**`workspace_id`**|String|Required|-||
|**`benchmark_id`**|String|Required|-||
|**`scenario_id`**|List of strings|Forbidden|-|Auto-generated|
|**`strategy_id`**|List of strings|Forbidden|-|Auto-generated|
|**`summary`**|Object|Forbidden|-|Auto-generated|
|**`task`**|Object|Required|-||
|**`results`**|List of objects|Forbidden|-|Auto-generated|
|**`runtime`**|Object|Forbidden|-|Auto-generated|
|**`unrated_docs`**|List of objects|Forbidden|-|Auto-generated|
|**`took`**|-|Forbidden|-|Auto-generated|
|**`_search`**|Object|Forbidden|-|Auto-generated|

*Note: Evaluations don't have an Update API. [Workers](docs/{{VERSION}}/reference/architecture.md#application) handle the updates automatically.*