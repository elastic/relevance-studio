# REST API

The Relevance Studio [server](docs/{{VERSION}}/reference/architecture.md#server) provides a REST API to manage workspace assets in the studio deployment, search data in the content deployment, and run benchmarks in the content deployment.

All REST API endpoints accept payloads as JSON and return payloads as JSON (`application/json`).

<span style="font-size: 18px;">**[Studio API](#studio-api)**</span>

- [Bulk operations](#bulk-operations)
- [Agent API](#agent-api)
- [Conversations API](#conversations-api)
- [Workspaces API](#workspaces-api)
- [Displays API](#displays-api)
- [Scenarios API](#scenarios-api)
- [Judgements API](#judgements-api)
- [Strategies API](#strategies-api)
- [Benchmarks API](#benchmarks-api)
- [Runs API](#runs-api)

<span style="font-size: 18px;">**[Content API](#content-api)**</span>

- [Search API](#search-api)
- [Aliases API](#aliases-api)
- [Mappings API](#mappings-api)

<span style="font-size: 18px;">**[Auth API](#auth-api)**</span>

- [Login](#login)
- [Logout](#logout)
- [Session](#session)

<span style="font-size: 18px;">**[System API](#system-api)**</span>

- [Setup API](#setup-api)
- [Upgrade API](#upgrade-api)
- [Health API](#health-api)

---

## Studio API

The Studio API manages data assets in the [studio deployment](docs/{{VERSION}}/reference/architecture.md#studio-deployment).

### Bulk operations

Most Studio API write endpoints (create, update, delete) accept either a single JSON object, for the current one-item-at-a-time behavior, or a JSON array of objects, to apply the same operation to many items in a single request. Bulk requests reuse the exact same route and HTTP method as the single-item form — no separate bulk endpoints exist.

- **Single-object request** (unchanged): the request body is a JSON object, and the response is the existing single-document shape, e.g. `{"_id": "...", "result": "created", ...}` on success, or a single `{"error": "...", "message": "..."}` body on failure. This keeps every existing single-item caller, including the UI, working exactly as before.
- **Array request**: the request body is a JSON array of objects. The response is a bulk-shaped envelope that mirrors Elasticsearch's `_bulk` API:

    ```json
    {
      "took": 12,
      "errors": false,
      "items": [
        { "index": { "_id": "...", "status": 201, "result": "created" } },
        { "index": { "_id": "...", "status": 400, "error": { "type": "validation_error", "reason": "..." } } }
      ]
    }
    ```

    - `items` is always ordered the same as the submitted array.
    - Each item succeeds or fails independently — one invalid item does not reject the rest of the batch.
    - The HTTP status is `200` if `errors` is `false`, or `207 Multi-Status` if any item failed.
    - `refresh=true` is issued once for the whole request, not once per item.
    - There is no cross-item atomicity: a failed item does not roll back or block the others.

- **Batch size limit**: requests are limited to 500 items. Exceeding it returns `400 Bad Request`.
- **Bulk delete requests**: for delete endpoints, the array form is a list of objects containing `_id`, e.g. `[{"_id": "..."}, {"_id": "..."}]`.
- **Cascading deletes** (workspaces, scenarios, benchmarks): deleting one of these asset types also deletes everything that depends on it (see each endpoint below). Because this cascade runs as a single Elasticsearch `delete_by_query` regardless of how many ids are submitted, its response is **not** the bulk envelope above — it's the standard `delete_by_query` response shape, the same for one id or many.
- **Conversations delete**: a conversation id that doesn't belong to the caller is reported as access-denied without distinguishing whether it exists and belongs to someone else, or doesn't exist at all — this is deliberate, to avoid leaking the existence of other users' conversations through a bulk request. The single-item route retains its original, more specific `404`-vs-`403` behavior.

### Agent API

The Agent API provides streaming chat operations used by the built-in chat experience.

#### Start chat stream

Starts a streaming chat response using server-sent events (SSE).

**`POST /api/chat`**

Example payload:

```json
{
  "text": "How can I improve recall for tail queries?",
  "conversation_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54",
  "session_id": "chat-session-1",
  "rounds": []
}
```

#### List chat endpoints

Returns the chat endpoint metadata used by clients and tools.

**`GET /api/chat/endpoints`**

#### Cancel chat stream

Requests cancellation of an in-flight chat stream.

**`POST /api/chat/cancel/<session_id>`**

---

### Conversations API

The Conversations API manages stored chat conversations in the [studio deployment](docs/{{VERSION}}/reference/architecture.md#studio-deployment).

When authentication is enabled, conversation access is scoped to the authenticated user: list/search returns only conversations created by that user, and get/update/delete are allowed only for the owner.

#### Search conversations

Search for conversations.

**`POST /api/conversations/_search`**

Example payload that searches all conversations:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "upgrade planning",
  "filters": [
    {
      "term": {
        "title": "Upgrade planning"
      }
    }
  ],
  "sort": {
    "@meta.updated_at": "desc"
  },
  "size": 25,
  "page": 1
}
```

#### Get conversation

Retrieve a conversation by its `_id`.

**`GET /api/conversations/<_id>`**

#### Create conversation

Create a conversation. Accepts optional `_id`.

**`POST /api/conversations`**

Example payload with common fields from the [Conversations data model](docs/{{VERSION}}/reference/data-model.md#conversations):

```json
{
  "conversation_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54",
  "title": "Relevance tuning notes",
  "rounds": [
    {
      "id": "round-1",
      "input": {
        "message": "How can I reduce regressions?"
      },
      "response": {
        "message": "Start by segmenting scenarios and running targeted benchmarks."
      }
    }
  ]
}
```

#### Update conversation

Update a conversation by its `_id`.

**`PUT /api/conversations/<_id>`**

Example payload:

```json
{
  "title": "Relevance tuning notes (updated)",
  "rounds": []
}
```

#### Delete conversation

Delete a conversation by its `_id`.

**`DELETE /api/conversations/<_id>`**

#### Delete conversations (bulk)

Delete multiple conversations in one request. See [Bulk operations](#bulk-operations), including the note on how this endpoint avoids leaking the existence of conversations the caller doesn't own.

**`DELETE /api/conversations`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

### Workspaces API

#### Search workspaces

Search for workspaces.

**`POST /api/workspaces/_search`**

Example payload that searches all workspaces:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

#### Get workspace

Retrieve a workspace by its `_id`.

**`GET /api/workspaces/<_id>`**

#### Create workspace

Create a workspace. Also accepts a JSON array to create multiple workspaces in one request. See [Bulk operations](#bulk-operations). Each item may include an optional `_id` for idempotence.

**`POST /api/workspaces`**

Example payload with all required and optional fields from the [Workspace data model](docs/{{VERSION}}/reference/data-model.md#workspaces):

```json
{
  "name": "Demo Workspace",
  "description": "Relevance workflows for product search",
  "index_pattern": "demo*",
  "rating_scale": {
    "min": 0,
    "max": 4
  },
  "tags": [ "demo", "created" ],
  "params": [ "text" ]
}
```

#### Update workspace

Update a workspace by its `_id`.

**`PUT /api/workspaces/<_id>`**

Example payload with all required and optional fields from the [Workspace data model](docs/{{VERSION}}/reference/data-model.md#workspaces):

```json
{
  "name": "Demo Workspace",
  "description": "Updated scope for launch-season catalog",
  "index_pattern": "demo*",
  "tags": [ "demo", "updated" ],
  "params": [ "text" ]
}
```

#### Update workspaces (bulk)

Update multiple workspaces in one request. Each item must include `_id`. See [Bulk operations](#bulk-operations).

**`PUT /api/workspaces`**

#### Delete workspace

Delete a workspace by its `_id`. Deleting a workspace cascades to delete all of its dependent displays, scenarios, judgements, strategies, benchmarks, and benchmark runs/results.

**`DELETE /api/workspaces/<_id>`**

#### Delete workspaces (bulk)

Delete multiple workspaces, and their dependents, in one request. See [Bulk operations](#bulk-operations) regarding the `delete_by_query`-based response shape for this endpoint.

**`DELETE /api/workspaces`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```


---

### Displays API

#### Search displays

Search for displays in a given workspace.

**`POST /api/workspaces/<workspace_id>/displays/_search`**

Example payload that searches all displays in the workspace:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Get display

Retrieve a display by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/displays/<_id>`**

#### Create display

Create a display in a given workspace. Accepts optional `_id`. Also accepts a JSON array to create multiple displays in one request. See [Bulk operations](#bulk-operations).

**`POST /api/workspaces/<workspace_id>/displays`**

Example payload with all required and optional fields from the [Display data model](docs/{{VERSION}}/reference/data-model.md#displays):

```json
{
  "index_pattern": "demo*",
  "template": {
    "body": "# {{ name.text }}\n\n{{ description.text }}",
    "image": {
      "position": "top-right",
      "url": "http://localhost:8000/{{ _id }}.png"
    }
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update display

Update a display by its `_id` in a given workspace.

**`PUT /api/workspaces/<workspace_id>/displays/<_id>`**

Example payload with all required and optional fields from the [Display data model](docs/{{VERSION}}/reference/data-model.md#displays):

```json
{
  "index_pattern": "demo*",
  "template": {
    "body": "# {{ name.keyword }}\n\n{{ description.text }}",
    "image": {
      "position": "top-left",
      "url": "http://localhost:8001/{{ _id }}.png"
    }
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update displays (bulk)

Update multiple displays in a given workspace in one request. Each item must include `_id`. See [Bulk operations](#bulk-operations).

**`PUT /api/workspaces/<workspace_id>/displays`**

#### Delete display

Delete a display by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/displays/<_id>`**

#### Delete displays (bulk)

Delete multiple displays in a given workspace in one request. See [Bulk operations](#bulk-operations).

**`DELETE /api/workspaces/<workspace_id>/displays`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

---

### Scenarios API

#### Search scenarios

Search for scenarios in a given workspace.

**`POST /api/workspaces/<workspace_id>/scenarios/_search`**

Example payload that searches all scenarios in the workspace:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### List scenario tags

Retrieve all scenario tags (up to 10,000) in a given workspace.

**`GET /api/workspaces/<workspace_id>/scenarios/_tags`**

#### Get scenario

Retrieve a scenario by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/scenarios/<_id>`**

#### Create scenario

Create a scenario in a given workspace. Also accepts a JSON array to create multiple scenarios in one request. See [Bulk operations](#bulk-operations). Unlike other asset types, scenarios never accept a caller-supplied `_id` — it's always deterministically derived from `workspace_id` and `values`, so identical `values` dedupe to the same scenario.

**`POST /api/workspaces/<workspace_id>/scenarios`**

Example payload with all required and optional fields from the [Scenario data model](docs/{{VERSION}}/reference/data-model.md#scenarios):

```json
{
  "name": "Demo Scenario",
  "tags": [ "demo", "created" ],
  "values": {
    "text": "demo"
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update scenario

Update a scenario by its `_id` in a given workspace.

**`PUT /api/workspaces/<workspace_id>/scenarios/<_id>`**

Example payload with all required and optional fields from the [Scenario data model](docs/{{VERSION}}/reference/data-model.md#scenarios):

```json
{
  "name": "Demo Scenario",
  "tags": [ "demo", "updated" ]
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update scenarios (bulk)

Update multiple scenarios in a given workspace in one request. Each item must include `_id`. See [Bulk operations](#bulk-operations).

**`PUT /api/workspaces/<workspace_id>/scenarios`**

#### Delete scenario

Delete a scenario by its `_id` in a given workspace. Deleting a scenario cascades to delete its judgements.

**`DELETE /api/workspaces/<workspace_id>/scenarios/<_id>`**

#### Delete scenarios (bulk)

Delete multiple scenarios, and their judgements, in a given workspace in one request. See [Bulk operations](#bulk-operations) regarding the `delete_by_query`-based response shape for this endpoint.

**`DELETE /api/workspaces/<workspace_id>/scenarios`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

---

### Judgements API

#### Search judgements

Search for documents in the content deployment and join judgement metadata and ratings for a given scenario.

**`POST /api/workspaces/<workspace_id>/judgements/_search`**

Example payload that searches all documents and joins any matching judgements:

```json
{
  "scenario_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b",
  "index_pattern": "demo*",
  "query_string": "*"
}
```

Example payload with all optional fields:

```json
{
  "scenario_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b",
  "index_pattern": "demo*",
  "query": {
    "query": {
      "match_all": {}
    }
  },
  "query_string": "demo",
  "filter": "rated-human",
  "sort": "rating-newest",
  "_source": {
    "includes": [
      "name",
      "description"
    ],
    "excludes": [
      "large_vector_field"
    ]
  }
}
```

*Notes:*
- `scenario_id` and `index_pattern` are required.
- If `query` is provided, it overrides `query_string`.
- `filter` supports `all`, `rated`, `rated-ai`, `rated-human`, and `unrated`.
- `sort` supports `match`, `rating-newest`, and `rating-oldest`.
- You do not need to provide `workspace_id` in the payload because it is taken from the URL path.

#### Set judgement

Set a judgement (as an upsert) in a given workspace. Also accepts a JSON array to set multiple judgements in one request. See [Bulk operations](#bulk-operations). Each judgement's `_id` is always deterministically derived from `workspace_id`, `scenario_id`, `index`, and `doc_id` — if the same `{scenario_id, index, doc_id}` appears more than once in a single array request, every occurrence resolves to the same `_id` (the last one submitted wins).

**`PUT /api/workspaces/<workspace_id>/judgements`**

Example payload with all required and optional fields from the [Judgement data model](docs/{{VERSION}}/reference/data-model.md#judgements):

```json
{
  "scenario_id": "67d554e2-8622-4c6c-9601-bf0e0a06128d",
  "index": "demo",
  "doc_id": "123",
  "rating": 3
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Delete judgement

Delete a judgement by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/judgements/<_id>`**

#### Delete judgements (bulk)

Delete multiple judgements in a given workspace in one request. See [Bulk operations](#bulk-operations).

**`DELETE /api/workspaces/<workspace_id>/judgements`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

---

### Strategies API

#### Search strategies

Search for strategies in a given workspace.

**`POST /api/workspaces/<workspace_id>/strategies/_search`**

Example payload that searches all strategies in the workspace:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### List strategy tags

Retrieve all strategy tags (up to 10,000) in a given workspace.

**`GET /api/workspaces/<workspace_id>/strategies/_tags`**

#### Get strategy

Retrieve a strategy by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/strategies/<_id>`**

#### Create strategy

Create a strategy in a given workspace. Accepts optional `_id`. Also accepts a JSON array to create multiple strategies in one request. See [Bulk operations](#bulk-operations).

**`POST /api/workspaces/<workspace_id>/strategies`**

Example payload with all required and optional fields from the [Strategy data model](docs/{{VERSION}}/reference/data-model.md#strategies):

```json
{
  "name": "Demo Strategy",
  "tags": [ "demo", "created" ],
  "template": {
    "lang": "mustache",
    "source": "{ \"query\": { \"match\": { \"name.text\": \"{{ text }}\" }}}"
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update strategy

Update a strategy by its `_id` in a given workspace.

**`PUT /api/workspaces/<workspace_id>/strategies/<_id>`**

Example payload with all required and optional fields from the [Strategy data model](docs/{{VERSION}}/reference/data-model.md#strategies):

```json
{
  "name": "Demo Strategy",
  "tags": [ "demo", "updated" ],
  "template": {
    "lang": "mustache",
    "source": "{ \"query\": { \"match\": { \"description.text\": \"{{ text }}\" }}}"
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update strategies (bulk)

Update multiple strategies in a given workspace in one request. Each item must include `_id`. See [Bulk operations](#bulk-operations).

**`PUT /api/workspaces/<workspace_id>/strategies`**

#### Delete strategy

Delete a strategy by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/strategies/<_id>`**

#### Delete strategies (bulk)

Delete multiple strategies in a given workspace in one request. See [Bulk operations](#bulk-operations).

**`DELETE /api/workspaces/<workspace_id>/strategies`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

---

### Benchmarks API

#### Search benchmarks

Search for benchmarks in a given workspace.

**`POST /api/workspaces/<workspace_id>/benchmarks/_search`**

Example payload that searches all benchmarks in the workspace:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### List benchmark tags

Retrieve all benchmark tags (up to 10,000) in a given workspace.

**`GET /api/workspaces/<workspace_id>/benchmarks/_tags`**

#### Generate candidate pool

Generate a candidate pool in a given workspace.

**`POST /api/workspaces/<workspace_id>/benchmarks/_candidates`**

#### Get benchmark

Retrieve a benchmark by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/benchmarks/<_id>`**

#### Create benchmark

Create a benchmark in a given workspace.. Accepts optional `_id`. Also accepts a JSON array to create multiple benchmarks in one request. See [Bulk operations](#bulk-operations).

**`POST /api/workspaces/<workspace_id>/benchmarks`**

Example payload with all required and optional fields from the [Benchmark data model](docs/{{VERSION}}/reference/data-model.md#benchmarks):

```json
{
  "name": "Demo Benchmark",
  "description": "This is a demo",
  "tags": [ "demo", "created" ],
  "task": {
    "k": 10,
    "metrics": [
      "ndcg",
      "precision",
      "recall"
    ],
    "scenarios": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "sample_size": 1000,
      "sample_seed": "abc123"
    },
    "strategies": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "docs": []
    }
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update benchmark

Update a benchmark by its `_id` in a given workspace.

**`PUT /api/workspaces/<workspace_id>/benchmarks/<_id>`**

```json
{
  "name": "Demo Benchmark",
  "description": "This is a demo",
  "tags": [ "demo", "updated" ],
  "task": {
    "metrics": [
      "ndcg",
      "precision",
      "recall"
    ],
    "scenarios": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "sample_size": 1000,
      "sample_seed": "abc123"
    },
    "strategies": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "docs": []
    }
  }
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Update benchmarks (bulk)

Update multiple benchmarks in a given workspace in one request. Each item must include `_id`. See [Bulk operations](#bulk-operations).

**`PUT /api/workspaces/<workspace_id>/benchmarks`**

#### Delete benchmark

Delete a benchmark by its `_id` in a given workspace. Deleting a benchmark cascades to delete its runs and all associated run data (results, runtime indices/strategies/scenarios/judgements, unrated docs, and failures).

**`DELETE /api/workspaces/<workspace_id>/benchmarks/<_id>`**

#### Delete benchmarks (bulk)

Delete multiple benchmarks, and their runs and run data, in a given workspace in one request. See [Bulk operations](#bulk-operations) regarding the `delete_by_query`-based response shape for this endpoint.

**`DELETE /api/workspaces/<workspace_id>/benchmarks`**

Example payload:

```json
[
  { "_id": "9f131f89-1c7f-454e-a04c-f3d4494fde54" },
  { "_id": "b6c4f886-e367-4a84-98c6-b8dc31e20a7b" }
]
```

---

### Runs API

A run is one execution of a [benchmark](docs/{{VERSION}}/reference/data-model.md#benchmarks).

#### Search runs

Search for runs of a given benchmark in a given workspace.

**`POST /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/_search`**

Example payload that searches all runs of the benchmark:

```json
{
  "text": "*"
}
```

Example payload with all optional fields:

```json
{
  "text": "demo",
  "filters": [
    {
      "term": {
        "tags": "demo"
      }
    }
  ],
  "sort": {
    "name": "asc"
  },
  "size": 25,
  "page": 1
}
```

*Note: You don't have to include `"workspace_id"` or `"benchmark_id"` in the payload because they already exist in the URL. If you include them, they must match the values in the URL.*

#### Get run

Retrieve a run by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>`**

#### Get run runtime strategies

Retrieve all runtime strategies for a run by its `_id` in a given workspace. See the [esrs-benchmark-runtime-strategies data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-runtime-strategies). This endpoint is **not paginated**: the number of strategies is bounded by the run's `task`, so it always returns them all. Response: `{run_id, total, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/runtime/strategies`**

#### Get run runtime indices

Retrieve the runtime indices for a run by its `_id` in a given workspace. See the [esrs-benchmark-runtime-indices data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-runtime-indices). Paginated with the optional `size` (default `25`) and `page` (default `1`) query parameters. Response: `{run_id, total, size, page, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/runtime/indices?size=&page=`**

#### Get run runtime scenarios

Retrieve the runtime scenarios for a run by its `_id` in a given workspace. See the [esrs-benchmark-runtime-scenarios data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-runtime-scenarios). Paginated with the optional `size` (default `25`) and `page` (default `1`) query parameters. Response: `{run_id, total, size, page, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/runtime/scenarios?size=&page=`**

#### Get run runtime judgements

Retrieve the runtime judgements for a run by its `_id` in a given workspace. See the [esrs-benchmark-runtime-judgements data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-runtime-judgements). This stream scales with the number of rated documents, so it is always paginated with the optional `size` (default `25`) and `page` (default `1`) query parameters. Pass an optional `scenario_id` query parameter to return only the judgements for a single scenario. Response: `{run_id, total, size, page, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/runtime/judgements?size=&page=&scenario_id=`**

#### Get run unrated docs

Retrieve the documents that appeared in a run's results but had no judgement, by the run's `_id` in a given workspace. See the [esrs-benchmark-unrated-docs data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-unrated-docs). Paginated with the optional `size` (default `25`) and `page` (default `1`) query parameters, sorted by `count` descending. Response: `{run_id, total, size, page, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/unrated_docs?size=&page=`**

#### Get run failures

Retrieve the per-strategy failures for a run by its `_id` in a given workspace. See the [esrs-benchmark-failures data model](docs/{{VERSION}}/reference/data-model.md#esrs-benchmark-failures). Paginated with the optional `size` (default `25`) and `page` (default `1`) query parameters. Response: `{run_id, total, size, page, items: [...]}`.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>/failures?size=&page=`**

#### Create run

Create and enqueue an asynchronous run of a given benchmark in a given workspace. Queues the run for a [worker](docs/{{VERSION}}/reference/architecture.md#worker) to claim and execute.

**`POST /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs`**

Example payload with all required and optional fields from the [Benchmark data model](docs/{{VERSION}}/reference/data-model.md#benchmarks):

```json
{
  "task": {
    "k": 10,
    "metrics": [
      "ndcg",
      "precision",
      "recall"
    ],
    "scenarios": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "sample_size": 1000,
      "sample_seed": "abc123"
    },
    "strategies": {
      "_ids": [],
      "tags": [
        "demo"
      ],
      "docs": []
    }
  }
}
```

*Note: You don't have to include `"workspace_id"` or `"benchmark_id"` in the payload because they already exist in the URL. If you include them, they must match the values in the URL.*

#### Run

Execute a run synchronously as a dry-run and return its results without persisting them. Used by [workers](docs/{{VERSION}}/reference/architecture.md#worker) and by the strategy/benchmark testing components of the UI.

**`POST /api/workspaces/<workspace_id>/runs/_run`**

*Note: This endpoint is workspace-scoped and is intentionally **not** nested under `/benchmarks/<benchmark_id>/`. A synchronous dry-run can be executed from an ad-hoc `task` payload without first persisting a benchmark, so it is not tied to a specific benchmark `_id`.*

#### Delete run

Delete a run by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/runs/<_id>`**

---

## Content API

The Content API retrieves documents and other data from the [content deployment](docs/{{VERSION}}/reference/architecture.md#content-deployment).

### Search API

Search documents in the [content deployment](docs/{{VERSION}}/reference/architecture.md#content-deployment) by a given set of index patterns. Accepts any [Elasticsearch Query DSL](https://www.elastic.co/docs/explore-analyze/query-filter/languages/querydsl) in the request payload.

**`POST /api/content/_search/<index_patterns>`**

Example payload:

```json
{
  "query": {
    "match_all": {}
  },
  "size": 100,
  "_source": {
    "includes": [
      "name",
      "description"
    ]
  }
}
```

### Aliases API

Retrieve the [aliases](https://www.elastic.co/docs/manage-data/data-store/aliases) of each index in the [content deployment](docs/{{VERSION}}/reference/architecture.md#content-deployment) that matches a given set of index patterns. Documents report the concrete index they live in, so this lets Relevance Studio match a document to a [display](docs/{{VERSION}}/reference/data-model.md#displays) whose index pattern names an alias of that index.

**`GET /api/content/aliases/<index_patterns>`**

Example response:

```json
{
  "products-000001": [ "products" ],
  "products-000002": [ "current", "products" ]
}
```

### Mappings API

Retrieve all [mappings](https://www.elastic.co/docs/manage-data/data-store/mapping) from the [content deployment](docs/{{VERSION}}/reference/architecture.md#content-deployment) that match a given set of index patterns.

**`GET /api/content/mappings/<index_patterns>`**

---

## Auth API

The Auth API manages user authentication and sessions. When `AUTH_ENABLED=true` (default), users must authenticate before accessing other API endpoints. See [Security](docs/{{VERSION}}/reference/security.md) for configuration details.

### Login

Authenticate with Elasticsearch credentials and create a session. Accepts either username/password or an API key. On success, returns user metadata and sets an HTTP-only session cookie (JWT).

**`POST /api/auth/login`**

Example payload (username/password):

```json
{
  "username": "alice",
  "password": "secret"
}
```

Example payload (API key):

```json
{
  "api_key": "<base64-encoded Elasticsearch API key>"
}
```

Example response:

```json
{
  "user": {
    "username": "alice",
    "roles": ["admin"],
    "full_name": "Alice Smith",
    "email": "alice@example.com"
  }
}
```

Returns `401` with `{"error": "Unauthorized", "message": "Invalid credentials"}` if credentials are invalid. Returns `400` if neither `api_key` nor `username`/`password` are provided.

When `AUTH_ENABLED=false`, returns a system user without validating credentials.

### Logout

Clear the session cookie.

**`POST /api/auth/logout`**

Example response:

```json
{
  "acknowledged": true
}
```

### Session

Return the current user's metadata from the session cookie. Returns `401` if no valid session exists (when `AUTH_ENABLED=true`).

**`GET /api/auth/session`**

Example response:

```json
{
  "user": {
    "username": "alice",
    "roles": ["admin"],
    "full_name": "Alice Smith",
    "email": "alice@example.com"
  }
}
```

When `AUTH_ENABLED=false`, returns the system user.

---

## System API

The System API manages the Relevance Studio application.

### Setup API

#### Run setup

Create the index templates and indices in the [studio deployment](docs/{{VERSION}}/reference/architecture.md#studio-deployment).

**`POST /api/setup`**

#### Check setup

Check deployment, setup, and upgrade status for the [studio deployment](docs/{{VERSION}}/reference/architecture.md#studio-deployment). This includes setup health and whether an index-template upgrade is pending.

**`GET /api/setup`**

### Upgrade API

#### Run upgrade

Apply additive index-template upgrade steps from the migration manifest.

**`POST /api/upgrade`**

### Health API

#### Healthz

Perform a standard healthz check to see if the server is running. Useful as a [liveness endpoint](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-a-liveness-http-request) when running Relevance Studio in Kubernetes.

**`GET /healthz`**

Example response:

```json
{
  "acknowledged": true
}
```