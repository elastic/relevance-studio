# Deep links

Source of truth: the "Hyperlinks" section of `SYSTEM_PROMPT` in `src/server/api/agent.py`.

## Getting the base URL

Ask the user once per conversation for the Studio UI base URL if you plan to hyperlink
anything. The quickstart default is `http://localhost:4096` (use `https://` when
`TLS_ENABLED=true`). If the user doesn't know or the base is unavailable, omit it and use
the base-less `/#/path` form.

## URL patterns

All internal links use the hash-based format: `{base}/#{path}`.

| Page | URL |
|---|---|
| Home | `{base}/#/` |
| Workspaces | `{base}/#/workspaces` |
| Workspace Overview | `{base}/#/workspaces/{workspace_id}` |
| Displays | `{base}/#/workspaces/{workspace_id}/displays` |
| Display Editor | `{base}/#/workspaces/{workspace_id}/displays/{display_id}` |
| Scenarios | `{base}/#/workspaces/{workspace_id}/scenarios` |
| Judgements | `{base}/#/workspaces/{workspace_id}/judgements` |
| Strategies | `{base}/#/workspaces/{workspace_id}/strategies` |
| Strategy Editor | `{base}/#/workspaces/{workspace_id}/strategies/{strategy_id}` |
| Benchmarks | `{base}/#/workspaces/{workspace_id}/benchmarks` |
| Benchmark | `{base}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}` |
| Evaluation | `{base}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}/evaluations/{evaluation_id}` |

## Query-param deep links

| Page | Query params | Purpose |
|---|---|---|
| Judgements | `?scenario_id={scenario_id}` | Open judgements for a specific scenario |
| Judgements | `?scenario_id={scenario_id}&filter=unrated` | Show only unrated docs |
| Judgements | `?scenario_id={scenario_id}&filter=rated-ai` | Show only AI-rated docs |
| Judgements | `?scenario_id={scenario_id}&sort=match` | Sort by query match, not rating recency |
| Strategy Editor | `?scenario_id={scenario_id}` | Pre-select a scenario for testing |

## Formatting rules

- Hyperlink the asset's **name**, not generic text or a raw URL.
  - Good: `the [Products](...) workspace`
  - Good: `Here are the [evaluation results]({base}/#/workspaces/123/benchmarks/456/evaluations/789).`
  - Bad: `[Click here](https://localhost:4096/#/workspaces/123/...)`
  - Bad: `Click here: https://localhost:4096/#/workspaces/123/...`
- Never show a raw `_id` in prose if a name is available.
- For images, use URL references, not base64 data URIs, in Markdown output:
  `![alt](https://example.com/image.png)` — not `![alt](data:image/png;base64,...)`.
