# REST API

The Relevance Studio [server](docs/reference/architecture.md#server) provides a REST API to manage workspace assets in the studio deployment, search data in the content deployment, and run evaluations in the content deployment.

All REST API endpoints accept payloads as JSON and return payloads as JSON (`application/json`).

<span style="font-size: 18px;">**[Studio API](#studio-api)**</span>

- [Workspaces API](#workspaces-api)
- [Displays API](#displays-api)
- [Scenarios API](#scenarios-api)
- [Judgements API](#judgements-api)
- [Strategies API](#strategies-api)
- [Benchmarks API](#benchmarks-api)
- [Evaluations API](#evaluations-api)

<span style="font-size: 18px;">**[Content API](#content-api)**</span>

- [Search API](#search-api)
- [Mappings API](#mappings-api)

<span style="font-size: 18px;">**[System API](#system-api)**</span>

- [Setup API](#setup-api)
- [Health API](#health-api)

---

## Studio API

The Studio API manages data assets in the [studio deployment](docs/reference/architecture.md#elasticsearch).

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

Create a workspace.

**`POST /api/workspaces`**

Example payload with all required and optional fields from the [Workspace data model](docs/reference/data-model.md#workspaces):

```json
{
  "name": "Demo Workspace",
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

Example payload with all required and optional fields from the [Workspace data model](docs/reference/data-model.md#workspaces):

```json
{
  "name": "Demo Workspace",
  "index_pattern": "demo*",
  "tags": [ "demo", "updated" ],
  "params": [ "text" ]
}
```

#### Delete workspace

Delete a workspace by its `_id`.

**`DELETE /api/workspaces/<_id>`**


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

Create a display in a given workspace. Accepts optional `_id`.

**`POST /api/workspaces/<workspace_id>/displays`**

Example payload with all required and optional fields from the [Display data model](docs/reference/data-model.md#displays):

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

Example payload with all required and optional fields from the [Display data model](docs/reference/data-model.md#displays):

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

#### Delete display

Delete a display by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/displays/<_id>`**

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

Create a scenario in a given workspace.

**`POST /api/workspaces/<workspace_id>/scenarios`**

Example payload with all required and optional fields from the [Scenario data model](docs/reference/data-model.md#scenarios):

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

Example payload with all required and optional fields from the [Scenario data model](docs/reference/data-model.md#scenarios):

```json
{
  "name": "Demo Scenario",
  "tags": [ "demo", "updated" ]
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Delete scenario

Delete a scenario by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/scenarios/<_id>`**

---

### Judgements API

#### Search judgements

Search for judgements in a given workspace.

**`POST /api/workspaces/<workspace_id>/judgements/_search`**

Example payload that searches all judgements in the workspace:

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

#### Set judgement

Set a judgement (as an upsert) in a given workspace.

**`PUT /api/workspaces/<workspace_id>/judgements`**

Example payload with all required and optional fields from the [Judgement data model](docs/reference/data-model.md#judgements):

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

Create a strategy in a given workspace. Accepts optional `_id`.

**`POST /api/workspaces/<workspace_id>/strategies`**

Example payload with all required and optional fields from the [Strategy data model](docs/reference/data-model.md#strategies):

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

Example payload with all required and optional fields from the [Strategy data model](docs/reference/data-model.md#strategies):

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

#### Delete strategy

Delete a strategy by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/strategies/<_id>`**

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

Create a benchmark in a given workspace.. Accepts optional `_id`.

**`POST /api/workspaces/<workspace_id>/benchmarks`**

Example payload with all required and optional fields from the [Benchmark data model](docs/reference/data-model.md#benchmarks):

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
  },
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
  },
}
```

*Note: You don't have to include `"workspace_id"` in the payload because it already exists in the URL. If you include it, it must match the value in the URL.*

#### Delete benchmark

Delete a benchmark by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/benchmarks/<_id>`**

---

### Evaluations API

#### Search evaluations

Search for evaluations in a given workspace.

**`POST /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/evaluations/_search`**

Example payload that searches all evaluations in the workspace:

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

#### Get evaluation

Retrieve an evaluation by its `_id` in a given workspace.

**`GET /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/evaluations/<_id>`**

#### Create evaluation

Create and enqueue an evaluation in a given workspace.

**`POST /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/evaluations`**

Example payload with all required and optional fields from the [Benchmark data model](docs/reference/data-model.md#benchmarks):

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
  },
}
```

*Note: You don't have to include `"workspace_id"` or `"benchmark_id"` in the payload because they already exist in the URL. If you include them, they must match the values in the URL.*

#### Run evaluation

Run an evaluation. Used by [workers](docs/reference/architecture.md#application).

**`POST /api/workspaces/<workspace_id>/evaluations/_run`**

#### Delete evaluation

Delete an evaluation by its `_id` in a given workspace.

**`DELETE /api/workspaces/<workspace_id>/benchmarks/<benchmark_id>/evaluations/<_id>`**

---

## Content API

The Content API retrieves documents and other data from the [content deployment](docs/reference/architecture.md#elasticsearch).

### Search API

Search documents in the [content deployment](docs/reference/architecture.md#elasticsearch) by a given index pattern. Accepts any [Elasticsearch Query DSL](https://www.elastic.co/docs/explore-analyze/query-filter/languages/querydsl) in the request payload.

**`POST /api/content/<index_pattern>/_search`**

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

### Mappings API

Retrieve all [mappings](https://www.elastic.co/docs/manage-data/data-store/mapping) from the [content deployment](docs/reference/architecture.md#elasticsearch) that match a given index pattern.

**`GET /api/content/<index_pattern>/_mappings`**

---

## System API

The System API manages the Relevance Studio application.

### Setup API

#### Run setup

Create the index templates and indices in the [studio deployment](docs/reference/architecture.md#elasticsearch).

**`POST /api/setup`**

#### Check setup

Check if the index templates and indices have been created in the [studio deployment](docs/reference/architecture.md#elasticsearch).

**`GET /api/setup`**

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