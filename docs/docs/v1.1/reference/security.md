# Security

Relevance Studio is designed to run in trusted environments.

## Authentication

Currently the [Server](docs/{{VERSION}}/reference/architecture.md#application) and [MCP Server](docs/{{VERSION}}/reference/architecture.md#application) use a single identity defined in an `.env` file. There isn't a way to identify or authenticate specific users of those services. Effectively, everyone who uses these services shares the same identity and permissions.

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