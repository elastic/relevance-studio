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

The recommended role for the [studio deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch) (below) grants **read and write** privileges to all indices prefixed with `esrs-`, and grants privilege to [call Elasticsearch Inference API endpoints](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-inference-chat-completion-unified), which is required when using the [Agent](docs/{{VERSION}}/guide/concepts.md#agent).

```json
{
  "cluster": [
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