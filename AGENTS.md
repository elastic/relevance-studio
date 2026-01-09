## Working Mode

- Do NOT modify existing source code in this repository.
- Use the `relevance-studio` MCP server tools to perform work (workspaces, scenarios, strategies, benchmarks, evaluations, etc.)
- **Prefer MCP Resources for read operations** - see [MCP_RESOURCES.md](MCP_RESOURCES.md) for URI patterns and usage

## Evaluation Handling

- **Evaluations can take 2-5 minutes to run** - do NOT wait synchronously
- After calling `evaluations_run`, the MCP call may timeout but the evaluation continues on the server
- Use `evaluation_status` to check if complete (returns ~500 bytes)
- Use `evaluation_summary` to get metrics (returns ~2KB)
- Only use `evaluations_get` if you need the full results (can be MBs)
- For per-strategy details, use `evaluation_results_for_strategy`

## Fast Data Access

**Claude Code:** Use MCP Resources (fastest) via `ReadMcpResourceTool`:
- `workspaces://list` (only static resource - others require workspace_id)
- `scenarios://{workspace_id}/list`, `evaluations://{workspace_id}/list`, etc.
- `evaluations://{_id}/status`, `evaluations://{_id}/summary`
- See [MCP_RESOURCES.md](MCP_RESOURCES.md) for all URI patterns

**Cursor / All Clients:** Use lightweight tools (Resources not supported in Cursor):

| Tool | Use Instead Of | Size Reduction |
|------|----------------|----------------|
| `workspaces_list` | `workspaces_search` | ~10x smaller |
| `scenarios_list` | `scenarios_search` | ~10x smaller |
| `strategies_list` | `strategies_search` | ~10x smaller |
| `benchmarks_list` | `benchmarks_search` | ~10x smaller |
| `evaluations_list` | `evaluations_search` | ~10x smaller |
| `evaluation_status` | `evaluations_get` | ~1000x smaller |
| `evaluation_summary` | `evaluations_get` | ~50x smaller |

## Workspace Handling

- store IDs of workspace, scenarios, judgements, strategies, benchmarks, evaluations in `local/current_ids.txt` as you work
- local rules are stored in `local/rules.md`