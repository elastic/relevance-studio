Look at `AGENTS.md` for the instructions to the agent.

## MCP Server Design

The `fastmcp_resources.py` server is designed to **absorb large data loads server-side** so that MCP clients have a better experience without blowing out their context windows.

### Design Rationale

- **Lightweight tools** (e.g., `evaluation_summary`, `evaluation_status`, `*_list`) intentionally fetch full documents from Elasticsearch internally, then filter/project the response before returning to the client
- This means the **server** may handle MB-sized documents, but the **client** only receives KB-sized responses
- This tradeoff is intentional: server memory is cheaper than LLM context tokens
- The "lightweight" label refers to the response size seen by the MCP client, not the internal ES query

### When reviewing this code

Do not flag the following as bugs:
- Lightweight tools calling `api.*.get()` which fetches full documents - this is by design
- Server-side memory usage from large ES responses - the filtering happens after fetch

Actual bugs to look for:
- Missing `workspace_id` validation (cross-workspace data exposure)
- SSRF or other security issues in URL fetching
- Inconsistencies between documentation and actual behavior
