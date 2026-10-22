# MCP client auth configuration

When `AUTH_ENABLED=true`, MCP clients must send credentials when connecting to the Relevance Studio MCP Server. This guide shows how to configure common MCP clients.

## Supported schemes

- **Basic**: `Authorization: Basic <base64(username:password)>` — Elasticsearch username and password.
- **ApiKey**: `Authorization: ApiKey <base64(id:api_key)>` — [Elasticsearch API key](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys). The value is the base64-encoded `id:api_key` string.
- **Bearer**: `Authorization: Bearer <base64(id:api_key)>` — Same as ApiKey.

## Claude Desktop

Claude Desktop supports two connection modes depending on your plan.

### Remote server (Claude Pro / Max / Team / Enterprise)

Add a `url` entry to `claude_desktop_config.json`. Include `headers` when
`AUTH_ENABLED=true`:

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

Use `http://` instead of `https://` when `TLS_ENABLED=false`.

For API key auth:

```json
{
  "headers": {
    "Authorization": "ApiKey <base64(id:api_key)>"
  }
}
```

### stdio proxy (all plans)

Claude Desktop can connect via a local proxy process that bridges stdio to the
MCP Server over HTTP. This works on all Claude plans.

The MCP Server must be running before Claude Desktop can connect.

From the project root, run:

```bash
python scripts/integrate_claude_desktop.py
```

This reads your `.env` file and writes the correct Claude Desktop configuration
automatically. Then restart Claude Desktop completely (Cmd+Q, then reopen).

Re-run the command and restart Claude Desktop whenever `.env` changes — for
example, after toggling `TLS_ENABLED` or `AUTH_ENABLED`, or rotating credentials.

When `AUTH_ENABLED=true` on the MCP Server, set `ELASTICSEARCH_API_KEY` (or
`ELASTICSEARCH_USERNAME` + `ELASTICSEARCH_PASSWORD`) in `.env`. The proxy
injects them as the `Authorization` header on every upstream request.
When `TLS_ENABLED=true`, also set `TLS_CERT_FILE` and `TLS_KEY_FILE` in `.env`.

> **⚠️ Security: Credentials are stored in plaintext**
>
> `integrate_claude_desktop.py` writes the credentials from your `.env` directly
> into Claude Desktop's config file in plaintext:
>
> - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
> - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
>
> The file is protected only by your OS user account's filesystem permissions —
> not encrypted. Treat it like any other file containing secrets:
>
> - **Don't share or commit** the config file or screenshots that include it.
> - **Use a scoped Elasticsearch API key** (least-privilege, short-lived,
>   revocable) rather than a username/password — see [Elasticsearch API keys](https://www.elastic.co/docs/deploy-manage/api-keys/elasticsearch-api-keys).
> - **Rotate the key** if the file is ever exposed (e.g. shared screen, backup
>   upload, malware scan finding).
> - **Re-run** `python scripts/integrate_claude_desktop.py` after rotation so the
>   new key is written into Claude Desktop's config.

## Cursor

In Cursor's MCP settings, add the server with custom headers. Example for Basic auth:

- **URL**: `https://localhost:4200/mcp`
- **Headers**: `Authorization: Basic <base64(username:password)>`

## Custom clients

Include the `Authorization` header on every HTTP request to the MCP endpoint (e.g. `POST /mcp/`).
