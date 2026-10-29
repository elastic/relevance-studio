# Workflows

...

## Create a workspace

...

## Create a display

...

## Create scenarios

...

## Create judgements

...

## Create strategies

...

## Create benchmarks

...

## Optimize hyperparameters

To check a strategy without creating a benchmark, use the **Benchmark** tab of the strategy editor. It compares the draft against the saved strategy across scenarios, and can search the draft's hyperparameters. Apply a winning variant to the draft, check its results in the **Search** tab, then save. See [Test a strategy in the editor](docs/{{VERSION}}/guide/concepts.md#test-a-strategy-in-the-editor).

1. Define [hyperparameters](docs/{{VERSION}}/guide/concepts.md#hyperparameter) on a strategy. Reference them in the template as `{{hp.name}}`, then define each one with a type, a promoted value and valid testable values in the strategy editor. Use **Copy production template** to get the template with the promoted values applied.
2. Create a benchmark and turn on **Optimize hyperparameters**. Choose grid or random search, narrow the values to test if you want to, then choose the objective, an optional latency constraint and a holdout. Check the estimate of variants and searches, and use **Estimate duration** if the run is large.
3. Run the benchmark. The run summary shows the winner of each strategy. Read the winner against the baseline on the holdout.
4. Expand a strategy to see its variants and the sensitivity of its hyperparameters. Open a variant and promote it to update the promoted values of the strategy or to fork the strategy.
5. Judge the unrated documents of the winners, then run again. Narrow the values to test around the new promoted values to refine the result.

### Optimize with an agent

An agent follows the same loop with the MCP tools:

1. `strategies_update` defines hyperparameters on a strategy. `strategies_render` previews the template with values applied.
2. `runs_create` with `dry_run: true` returns the estimate of a run (variants, searches, limits and warnings) without queueing it. Use `benchmarks_estimate` with `probe: true` to estimate the duration.
3. `runs_create` queues the run with `task.optimization`.
4. `runs_get_optimization_summary` returns a compact summary per strategy: the winner, the baseline, the top variants, the sensitivity of each hyperparameter and warnings. Use `runs_get_variants` to page through the variants of one strategy and to re-rank them under another objective.
5. `strategies_promote` applies a variant, either by updating the promoted values or by forking.
6. `runs_get_unrated_docs` with `winners_only: true` lists the documents that are worth judging first.

## Analyze runs

...