# Claude plugin

Elasticsearch Relevance Studio ships a Claude plugin, `relevance-studio`, from this
repository's root. It teaches Claude Code and Claude Desktop the full search relevance
engineering lifecycle — workspaces, displays, scenarios, judgements, strategies,
benchmarks, and evaluations — as a set of skills that call the
[MCP tools](docs/{{VERSION}}/reference/mcp-tools.md).

The marketplace manifest lives at `.claude-plugin/marketplace.json`; the skills live at
`src/skills/`.

## Install and configure

### Claude Code

```sh
claude plugin marketplace add elastic/relevance-studio
claude plugin install relevance-studio
```

Configure the MCP URL and, if auth is enabled, the Authorization header:

```
/plugin configure relevance-studio@elastic-relevance-studio
```

or at install time:

```sh
claude plugin install relevance-studio \
  --config mcp_url=https://localhost:4200/mcp \
  --config auth_header="ApiKey <base64 id:api_key>"
```

If `AUTH_ENABLED=false` on the MCP Server, **omit `--config auth_header` entirely** rather
than passing an empty value — the CLI rejects `--config auth_header=` (empty string) as
invalid:

```sh
claude plugin install relevance-studio --config mcp_url=http://localhost:4200/mcp
```

Test with:

```
/relevance-studio:connect-and-verify
```

Uninstall with:

```sh
claude plugin uninstall relevance-studio
claude plugin marketplace remove elastic-relevance-studio
```

### Claude Desktop

Install the plugin via Customize → Plugins → Add → Add marketplace → "Add from a
repository" → `elastic/relevance-studio`.

Configure the connector with the stdio proxy (`python scripts/integrate_claude_desktop.py`,
all plans) or a remote `url` entry (paid plans) — see
[MCP client auth configuration](docs/{{VERSION}}/guide/mcp-client-auth.md) for both.

## Credentials

The plugin's `userConfig` accepts:

- `mcp_url` — the MCP Server URL including the `/mcp` path, e.g.
  `https://localhost:4200/mcp` (use `http://` when `TLS_ENABLED=false`).
- `auth_header` — the full `Authorization` header value: `ApiKey <base64 id:api_key>`,
  `Basic <base64 username:password>`, or `Bearer <base64 id:api_key>`. Leave it unset when
  `AUTH_ENABLED=false` — in the interactive `/plugin configure` dialog, submit it blank; from
  the CLI, omit `--config auth_header` entirely rather than passing an empty value.

This single field supports every auth scheme the MCP Server accepts — see
[MCP client auth configuration](docs/{{VERSION}}/guide/mcp-client-auth.md) for the schemes
themselves.

## Minimum server version

The plugin requires server version **1.2.4** or later — earlier versions shipped a broken
`workspaces_update` JSON schema for partial updates. The `connect-and-verify` skill checks
the connected server's version (from `setup_check`) against this floor.

## Skills

The plugin ships skills across these areas: platform setup and operations, workspace and
content discovery, ground truth (scenarios and judgements), strategy engineering,
benchmarks and evaluations, orchestration and automation, and reporting/provenance/hygiene.
Two skills (`assets-as-code`, `ci-gate`) require Claude Code's shell and filesystem access
and don't work in Claude Desktop.

See [`src/skills/AGENTS.md`](https://github.com/elastic/relevance-studio/blob/main/src/skills/AGENTS.md)
in the repository for the full catalog and conventions.
