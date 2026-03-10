# Security

Relevance Studio is designed to run in trusted environments.

## Authentication

Authentication controls access to the [Server](docs/{{VERSION}}/reference/architecture.md#application) and [MCP Server](docs/{{VERSION}}/reference/architecture.md#application). See [Getting started: Authentication](docs/{{VERSION}}/guide/getting-started-auth.md) for setup steps.

### Auth configuration

| Variable | Default | Description |
|----------|---------|--------------|
| `AUTH_ENABLED` | `true` | Set to `false` to disable auth and use service-account (singleton) mode. |
| `JWT_SECRET` | — | Secret for signing session JWTs. Required when `AUTH_ENABLED` is true. Generate with `openssl rand -hex 32`. |
| `SESSION_EXPIRY` | `24h` | Session expiry for JWT cookies (e.g. `24h`, `7d`, `30m`). |

When `AUTH_ENABLED=false`, the credentials in `.env` (`ELASTICSEARCH_*` / `CONTENT_*`) define a single service account used for all requests. See [Migration guide](docs/{{VERSION}}/guide/auth-tls-migration.md) for moving from auth-disabled to auth-enabled.

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

The [Server](docs/{{VERSION}}/reference/architecture.md#application) and [MCP Server](docs/{{VERSION}}/reference/architecture.md#application) support native TLS. TLS is enabled by default. When enabled, you must provide valid PEM certificate and key files via environment variables.

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TLS_ENABLED` | `true` | Set to `false` to run over HTTP (e.g. behind a TLS-terminating proxy). |
| `TLS_CERT_FILE` | — | Path to PEM certificate file (required when TLS enabled). |
| `TLS_KEY_FILE` | — | Path to PEM private key file (required when TLS enabled). |

When `TLS_ENABLED` is true, both `TLS_CERT_FILE` and `TLS_KEY_FILE` must be set and the files must exist. Otherwise the server exits at startup with a clear error message.

### Self-signed certificates for local development

For local development, you can generate a self-signed certificate:

**Using quickstart:**

```bash
quickstart --generate-tls-cert
```

This creates `certs/cert.pem` and `certs/key.pem` in your installation directory and configures the servers to use them. Access the app at `https://localhost:4096` and accept the browser warning for the self-signed cert.

**Manual generation with OpenSSL:**

```bash
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/key.pem -out certs/cert.pem \
  -subj "/CN=localhost/O=Relevance Studio Local Dev"
```

Then set in `.env`:

```
TLS_ENABLED=true
TLS_CERT_FILE=/certs/cert.pem
TLS_KEY_FILE=/certs/key.pem
```

For Docker, mount the certs directory and ensure the paths match (e.g. `-v ./certs:/certs`).

### Production

For production, use certificates from a trusted CA (e.g. Let's Encrypt) or your organization's PKI. Place the Server and MCP Server behind a reverse proxy that terminates TLS if you prefer to manage certificates centrally.

Communications with [Elasticsearch](docs/{{VERSION}}/reference/architecture.md#elasticsearch) are encrypted using the TLS configurations of your chosen Elasticsearch deployments. On Elastic Cloud Hosted (ECH) and Elastic Cloud Serverless (ECS), TLS is enabled and enforced by default. If you are self-managing Elasticsearch, review the [Elasticsearch security documentation](https://www.elastic.co/docs/deploy-manage/security) to implement TLS for Elasticsearch.