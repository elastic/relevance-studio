# Security

Relevance Studio is designed to run in trusted environments.

## Authentication

### MCP Server authentication

When `AUTH_ENABLED=true` (default), the [MCP Server](docs/{{VERSION}}/reference/architecture.md#application) requires authentication for all tool calls and custom routes except `/healthz` and the `healthz_mcp` tool. MCP clients must send credentials via the `Authorization` header on each request.

**Supported schemes:**

- **Basic**: `Authorization: Basic <base64(username:password)>` — Use Elasticsearch username and password.
- **ApiKey**: `Authorization: ApiKey <base64(id:api_key)>` — Use an [Elasticsearch API key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys). The value is the base64-encoded `id:api_key` string.
- **Bearer**: `Authorization: Bearer <base64(id:api_key)>` — Same as ApiKey; accepts the base64-encoded API key.

**MCP client configuration:**

Configure your MCP client to send credentials when connecting to Relevance Studio. Examples:

- **Claude Desktop / Cursor**: Add `headers` with `Authorization` to the MCP server config. For Basic auth, use `Authorization: Basic <base64(username:password)>`. For API key, use `Authorization: ApiKey <encoded>` where `encoded` is the base64 of `id:api_key`.
- **Custom clients**: Include the `Authorization` header on every HTTP request to the MCP endpoint (e.g. `POST /mcp/`).

When `AUTH_ENABLED=false`, the MCP server uses the service account from `.env` (no per-request auth).

### Flask Server authentication

The [Server](docs/{{VERSION}}/reference/architecture.md#application) uses session-based auth when `AUTH_ENABLED=true`. See `/api/auth/login` and `/api/auth/session`.

When `AUTH_ENABLED=false`, the server uses a single identity from `.env` and does not require login.

Authentication to the [studio deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch) is configured by these environment variables defined in `.env`:

**Option 1: [API Key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys)**

- `ELASTICSEARCH_API_KEY`

**Option 2: Basic Auth**

- `ELASTICSEARCH_USERNAME`
- `ELASTICSEARCH_PASSWORD`

Authentication to the [content deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch) is configured by these environment variables defined in `.env`:

**Option 1: [API Key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys)**

- `CONTENT_ELASTICSEARCH_API_KEY`

**Option 2: Basic Auth**

- `CONTENT_ELASTICSEARCH_USERNAME`
- `CONTENT_ELASTICSEARCH_PASSWORD`


## Roles and permissions

You can use [role-based access control (RBAC) in Elasticsearch](https://www.elastic.co/docs/deploy-manage/users-roles/cluster-or-deployment-auth/user-roles) scope the permissions of Relevance Studio.

Below are the recommended role configurations for the studio deployment and the content deployment.

### Studio deployment role configuration

The recommended role for the [studio deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch) (below) grants **read and write** privileges to all indices prefixed with `esrs-`, grants `manage_index_templates` to create and read composable index templates during [setup](docs/{{VERSION}}/guide/quickstart.md), grants `monitor` to check the Elasticsearch license, and grants privilege to [call Elasticsearch Inference API endpoints](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-inference-chat-completion-unified), which is required when using the [Agent](docs/{{VERSION}}/guide/concepts.md#agent).

```json
{
  "cluster": [
    "manage_index_templates",
    "monitor",
    "monitor_inference"
  ],
  "indices": [
    {
      "names": [
        "esrs-*"
      ],
      "privileges": [
        "all"
      ],
      "field_security": {
        "grant": [
          "*"
        ],
        "except": []
      }
    }
  ]
}
```

### Content deployment role configuration

The recommended role for the [content deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch) (below) grants **read** privileges for any index. You can limit the scope of indices by giving specific index names or index patterns in `"indices.names"`. Cluster monitoring is required for [workers](docs/{{VERSION}}/reference/architecture.md#application) to use the [Rank Eval API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval).

```json
{
  "cluster": [
    "monitor"
  ],
  "indices": [
    {
      "names": [
        "*"
      ],
      "privileges": [
        "read",
        "view_index_metadata",
        "monitor"
      ],
      "field_security": {
        "grant": [
          "*"
        ],
        "except": []
      },
      "allow_restricted_indices": false
    }
  ]
}
```

## TLS

**⚠️ The [Server](docs/{{VERSION}}/reference/architecture.md#application) and [MCP Server](docs/{{VERSION}}/reference/architecture.md#application) lack native support for TLS. You must place the Server and MCP Server behind a proxy that implements TLS to secure data in transit to those services.**

Communications with [Elasticsearch](docs/{{VERSION}}/reference/architecture.md#elasticsearch) are encrypted using the TLS configurations of your chosen Elasticsearch deployments. On Elastic Cloud Hosted (ECH) and Elastic Cloud Serverless (ECS), TLS is enabled and enforced by default. If you are self-managing Elasticsearch, review the [Elasticsearch security documentation](https://www.elastic.co/docs/deploy-manage/security) to implement TLS for Elasticsearch.