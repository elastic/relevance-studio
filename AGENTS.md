## Working Mode

- Do NOT modify existing source code in this repository.
- Use only the Relevance Studio MCP tools to perform work (workspaces, scenarios, strategies, benchmarks, evaluations, etc.)

## Evaluation Handling

- **Evaluations can take 2-5 minutes to run** - do NOT wait synchronously
- After calling `evaluations_run`, the MCP call may timeout but the evaluation continues on the server
- Check back with `evaluations_get` to see if the evaluation is complete
- Save all MCP responses to disk to process, results are large and complex.
- Store results in `local/` for later analysis

## Workspace Handling

- store IDs of workspace, scenarios, judgements, strategies, benchmarks, evaluations in `local/current_ids.txt` as you work
- local rules are stored in `local/rules.md`