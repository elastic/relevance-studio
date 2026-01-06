## Working Mode

- Do NOT modify existing source code in this repository.
- Use only the Relevance Studio MCP tools to perform work (workspaces, scenarios, strategies, benchmarks, evaluations, etc.)

## Evaluation Handling

- **Evaluations can take 2-5 minutes to run** - do NOT wait synchronously
- After calling `evaluations_run`, the MCP call may timeout but the evaluation continues on the server
- Check back with `evaluations_get` to see if the evaluation is complete
- Save evaluation results to disk (JSON files) - do NOT process large results in memory
- Store results in `local/` for later analysis

## Workspace Handling

- store workspace IDs in `local/workspace_ids.txt` as you work
