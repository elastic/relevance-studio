## Working Mode

- Do NOT modify existing source code in this repository.
- Use only the Relevance Studio MCP tools to perform work (workspaces, scenarios, strategies, benchmarks, evaluations, etc.)

## MCP Response Handling

**IMPORTANT:** Do not try to consume MCP responses inline - they are often too large. When a response is saved to a temp file (due to size), use `jq` or other tools to extract the specific fields you need. Never assume an MCP response will be small.

## Evaluation Handling

- **Evaluations can take 2-5 minutes to run** - do NOT wait synchronously
- After calling `evaluations_run`, the MCP call may timeout but the evaluation continues on the server
- Check back with `evaluations_get` to see if the evaluation is complete

## Workspace Handling

- store IDs of workspace, scenarios, judgements, strategies, benchmarks, evaluations in `local/current_ids.txt` as you work
- local rules are stored in `local/rules.md`