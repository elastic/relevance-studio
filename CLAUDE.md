Look at `AGENTS.md` for the instructions to the agent.

## MCP Server Design

The `fastmcp_resources.py` server is designed to **absorb large data loads server-side** so that MCP clients have a better experience without blowing out their context windows.

### Design Rationale

- **Lightweight tools** (e.g., `evaluation_summary`, `evaluation_status`, `*_list`) intentionally fetch full documents from Elasticsearch internally, then filter/project the response before returning to the client
- This means the **server** may handle MB-sized documents, but the **client** only receives KB-sized responses
- This tradeoff is intentional: server memory is cheaper than LLM context tokens
- The "lightweight" label refers to the response size seen by the MCP client, not the internal ES query

### Access Model

- **`_id`-only access is by design**: Tools/resources that take only an `_id` (e.g., `strategies_get`, `evaluation_status`) do not verify workspace ownership. If you know an `_id`, you can access it. This is intentional - the MCP server operates in a trusted environment where callers are authorized users.
- **`workspace_id` is required for listing/searching**: All list and search tools require a valid `workspace_id` to prevent accidentally querying across workspaces.

### When reviewing this code

Do not flag the following as bugs:
- Lightweight tools calling `api.*.get()` which fetches full documents - this is by design
- Server-side memory usage from large ES responses - the filtering happens after fetch
- `_id`-only endpoints not checking workspace ownership - this is the intended trust model

Actual bugs to look for:
- Missing `workspace_id` validation in list/search tools (cross-workspace data exposure)
- SSRF or other security issues in URL fetching
- Inconsistencies between documentation and actual behavior
