# MCP Tools

The [MCP Server](docs/{{VERSION}}/reference/architecture.md#application) for Relevance Studio implements the core [REST API](docs/{{VERSION}}/reference/rest-api.md) resource operations as MCP tools. Tool input/output generally mirrors the corresponding REST operation and data model. For schema details and full payload examples, see the linked [REST API](docs/{{VERSION}}/reference/rest-api.md) sections.

## Tool Groups

### Conversations

Maps to [Conversations API](docs/{{VERSION}}/reference/rest-api.md#conversations-api).

|MCP tool|REST API|
|---|---|
|`conversations_search`|[Search conversations](docs/{{VERSION}}/reference/rest-api.md#search-conversations)|
|`conversations_get`|[Get conversation](docs/{{VERSION}}/reference/rest-api.md#get-conversation)|
|`conversations_create`|[Create conversation](docs/{{VERSION}}/reference/rest-api.md#create-conversation)|
|`conversations_update`|[Update conversation](docs/{{VERSION}}/reference/rest-api.md#update-conversation)|
|`conversations_delete`|[Delete conversation](docs/{{VERSION}}/reference/rest-api.md#delete-conversation)|

### Workspaces

Maps to [Workspaces API](docs/{{VERSION}}/reference/rest-api.md#workspaces-api).

|MCP tool|REST API|
|---|---|
|`workspaces_search`|[Search workspaces](docs/{{VERSION}}/reference/rest-api.md#search-workspaces)|
|`workspaces_get`|[Get workspace](docs/{{VERSION}}/reference/rest-api.md#get-workspace)|
|`workspaces_create`|[Create workspace](docs/{{VERSION}}/reference/rest-api.md#create-workspace)|
|`workspaces_update`|[Update workspace](docs/{{VERSION}}/reference/rest-api.md#update-workspace)|
|`workspaces_delete`|[Delete workspace](docs/{{VERSION}}/reference/rest-api.md#delete-workspace)|

### Displays

Maps to [Displays API](docs/{{VERSION}}/reference/rest-api.md#displays-api).

|MCP tool|REST API|
|---|---|
|`displays_search`|[Search displays](docs/{{VERSION}}/reference/rest-api.md#search-displays)|
|`displays_get`|[Get display](docs/{{VERSION}}/reference/rest-api.md#get-display)|
|`displays_create`|[Create display](docs/{{VERSION}}/reference/rest-api.md#create-display)|
|`displays_update`|[Update display](docs/{{VERSION}}/reference/rest-api.md#update-display)|
|`displays_delete`|[Delete display](docs/{{VERSION}}/reference/rest-api.md#delete-display)|

### Scenarios

Maps to [Scenarios API](docs/{{VERSION}}/reference/rest-api.md#scenarios-api).

|MCP tool|REST API|
|---|---|
|`scenarios_search`|[Search scenarios](docs/{{VERSION}}/reference/rest-api.md#search-scenarios)|
|`scenarios_tags`|[List scenario tags](docs/{{VERSION}}/reference/rest-api.md#list-scenario-tags)|
|`scenarios_get`|[Get scenario](docs/{{VERSION}}/reference/rest-api.md#get-scenario)|
|`scenarios_create`|[Create scenario](docs/{{VERSION}}/reference/rest-api.md#create-scenario)|
|`scenarios_update`|[Update scenario](docs/{{VERSION}}/reference/rest-api.md#update-scenario)|
|`scenarios_delete`|[Delete scenario](docs/{{VERSION}}/reference/rest-api.md#delete-scenario)|

### Judgements

Maps to [Judgements API](docs/{{VERSION}}/reference/rest-api.md#judgements-api).

|MCP tool|REST API|
|---|---|
|`judgements_search`|[Search judgements](docs/{{VERSION}}/reference/rest-api.md#search-judgements)|
|`judgements_set`|[Set judgement](docs/{{VERSION}}/reference/rest-api.md#set-judgement)|
|`judgements_unset`|[Delete judgement](docs/{{VERSION}}/reference/rest-api.md#delete-judgement)|

### Strategies

Maps to [Strategies API](docs/{{VERSION}}/reference/rest-api.md#strategies-api).

|MCP tool|REST API|
|---|---|
|`strategies_search`|[Search strategies](docs/{{VERSION}}/reference/rest-api.md#search-strategies)|
|`strategies_tags`|[List strategy tags](docs/{{VERSION}}/reference/rest-api.md#list-strategy-tags)|
|`strategies_get`|[Get strategy](docs/{{VERSION}}/reference/rest-api.md#get-strategy)|
|`strategies_create`|[Create strategy](docs/{{VERSION}}/reference/rest-api.md#create-strategy)|
|`strategies_update`|[Update strategy](docs/{{VERSION}}/reference/rest-api.md#update-strategy)|
|`strategies_delete`|[Delete strategy](docs/{{VERSION}}/reference/rest-api.md#delete-strategy)|

### Benchmarks

Maps to [Benchmarks API](docs/{{VERSION}}/reference/rest-api.md#benchmarks-api).

|MCP tool|REST API|
|---|---|
|`benchmarks_search`|[Search benchmarks](docs/{{VERSION}}/reference/rest-api.md#search-benchmarks)|
|`benchmarks_tags`|[List benchmark tags](docs/{{VERSION}}/reference/rest-api.md#list-benchmark-tags)|
|`benchmarks_make_candidate_pool`|[Generate candidate pool](docs/{{VERSION}}/reference/rest-api.md#generate-candidate-pool)|
|`benchmarks_get`|[Get benchmark](docs/{{VERSION}}/reference/rest-api.md#get-benchmark)|
|`benchmarks_create`|[Create benchmark](docs/{{VERSION}}/reference/rest-api.md#create-benchmark)|
|`benchmarks_update`|[Update benchmark](docs/{{VERSION}}/reference/rest-api.md#update-benchmark)|
|`benchmarks_delete`|[Delete benchmark](docs/{{VERSION}}/reference/rest-api.md#delete-benchmark)|

### Evaluations

Maps to [Evaluations API](docs/{{VERSION}}/reference/rest-api.md#evaluations-api).

|MCP tool|REST API|
|---|---|
|`evaluations_search`|[Search evaluations](docs/{{VERSION}}/reference/rest-api.md#search-evaluations)|
|`evaluations_get`|[Get evaluation](docs/{{VERSION}}/reference/rest-api.md#get-evaluation)|
|`evaluations_create`|[Create evaluation](docs/{{VERSION}}/reference/rest-api.md#create-evaluation)|
|`evaluations_run`|[Run evaluation](docs/{{VERSION}}/reference/rest-api.md#run-evaluation)|
|`evaluations_delete`|[Delete evaluation](docs/{{VERSION}}/reference/rest-api.md#delete-evaluation)|

### Content

Maps to [Content API](docs/{{VERSION}}/reference/rest-api.md#content-api).

|MCP tool|REST API|
|---|---|
|`content_search`|[Search API](docs/{{VERSION}}/reference/rest-api.md#search-api)|
|`content_mappings_browse`|[Mappings API](docs/{{VERSION}}/reference/rest-api.md#mappings-api)|

### Setup

Maps to [Setup API](docs/{{VERSION}}/reference/rest-api.md#setup-api).

|MCP tool|REST API|
|---|---|
|`setup_check`|[Check setup](docs/{{VERSION}}/reference/rest-api.md#check-setup)|
|`setup_run`|[Run setup](docs/{{VERSION}}/reference/rest-api.md#run-setup)|

### Utilities

|MCP tool|REST API / purpose|
|---|---|
|`get_base64_image_from_url`|Utility for fetching an image URL, downsizing it to save on tokens, and returning a base64 data URL.|
|`healthz_mcp`|MCP-side health check utility, similar in intent to [Health API](docs/{{VERSION}}/reference/rest-api.md#health-api).|

## HTTP-only endpoints

Some REST APIs are transport-specific and are not exposed as MCP tools:

- [Agent API](docs/{{VERSION}}/reference/rest-api.md#agent-api) (`/api/chat`, `/api/chat/endpoints`, `/api/chat/cancel/<session_id>`) uses streaming HTTP behavior.
- [Upgrade API](docs/{{VERSION}}/reference/rest-api.md#upgrade-api) (`POST /api/upgrade`) is currently HTTP-only.