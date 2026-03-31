# MCP client auth configuration

When `AUTH_ENABLED=true`, MCP clients must send credentials when connecting to the Relevance Studio MCP Server. This guide shows how to configure common MCP clients.

## Supported schemes

- **Basic**: `Authorization: Basic <base64(username:password)>` — Elasticsearch username and password.
- **ApiKey**: `Authorization: ApiKey <base64(id:api_key)>` — [Elasticsearch API key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys). The value is the base64-encoded `id:api_key` string.
- **Bearer**: `Authorization: Bearer <base64(id:api_key)>` — Same as ApiKey.

## Claude Desktop

Add `headers` to your MCP server config in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "relevance-studio": {
      "url": "https://localhost:4200/mcp",
      "headers": {
        "Authorization": "Basic <base64(username:password)>"
      }
    }
  }
}
```

For API key auth:

```json
{
  "headers": {
    "Authorization": "ApiKey <base64(id:api_key)>"
  }
}
```

## Cursor

In Cursor's MCP settings, add the server with custom headers. Example for Basic auth:

- **URL**: `https://localhost:4200/mcp`
- **Headers**: `Authorization: Basic <base64(username:password)>`

## Custom clients

Include the `Authorization` header on every HTTP request to the MCP endpoint (e.g. `POST /mcp/`).
