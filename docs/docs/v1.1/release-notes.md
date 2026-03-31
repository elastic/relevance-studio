# Release notes

## v1.1.1

### Features

- Added evaluation throttling controls to limit and pace `_rank_eval` requests, with global environment defaults and per-benchmark overrides via `task.rank_eval_batch_size` and `task.rank_eval_batch_delay`. Also added `task.requests` to track request volume. ([Data model](docs/{{VERSION}}/reference/data-model.md#benchmarks)) ([3b376e9](https://github.com/elastic/relevance-studio/commit/3b376e9), [90bd96e](https://github.com/elastic/relevance-studio/commit/90bd96e), [5ee45ea](https://github.com/elastic/relevance-studio/commit/5ee45ea), [61be00a](https://github.com/elastic/relevance-studio/commit/61be00a))

### Improvements

- Expanded security guidance for the studio deployment role by documenting required cluster privileges (`manage_index_templates`, `monitor`) in addition to `monitor_inference`. ([Security](docs/{{VERSION}}/reference/security.md#studio-deployment-role-configuration)) ([657d3ff](https://github.com/elastic/relevance-studio/commit/657d3ff))
- Updated documentation screenshots and benchmark/reference docs to reflect the v1.1 UI and data model updates. ([Welcome](docs/{{VERSION}}/guide/welcome.md), [Data model](docs/{{VERSION}}/reference/data-model.md#benchmarks)) ([983963c](https://github.com/elastic/relevance-studio/commit/983963c), [0fadb4b](https://github.com/elastic/relevance-studio/commit/0fadb4b))

### Bug fixes

- Fixed quickstart command usage in docs to use explicit `--version` flags and corrected minor docs/linking issues. ([Quickstart](docs/{{VERSION}}/guide/quickstart.md)) ([80ab4f7](https://github.com/elastic/relevance-studio/commit/80ab4f7), [c3a695a](https://github.com/elastic/relevance-studio/commit/c3a695a))

## v1.1.0

### Features

- Added a new [Agent API](docs/{{VERSION}}/reference/rest-api.md#agent-api) for streaming chat responses, endpoint discovery, and cancellation, plus a chat experience in the UI with persisted [Conversations](docs/{{VERSION}}/reference/data-model.md#conversations). ([bffcdbc](https://github.com/elastic/relevance-studio/commit/bffcdbc), [7557c52](https://github.com/elastic/relevance-studio/commit/7557c52))
- Added additive upgrade support with a dedicated [`POST /api/upgrade`](docs/{{VERSION}}/reference/rest-api.md#upgrade-api) endpoint and richer [Setup API checks](docs/{{VERSION}}/reference/rest-api.md#setup-api) that report upgrade state. ([4300643](https://github.com/elastic/relevance-studio/commit/4300643))
- Extended the [Workspaces data model](docs/{{VERSION}}/reference/data-model.md#workspaces) with `description` and surfaced it in the UI for better project context. ([298daf1](https://github.com/elastic/relevance-studio/commit/298daf1))

### Improvements

- Persisted and restored scenarios in URL state for the Judgements page and Strategy editor to improve navigation/shareability. ([e59488a](https://github.com/elastic/relevance-studio/commit/e59488a))
- Added UI context sharing from the app into chat requests so the agent can use current resource context more effectively and with fewer MCP tool calls. ([174eba9](https://github.com/elastic/relevance-studio/commit/174eba9))
- Improved chat context handling by including resource context in `ui_context`, reducing unnecessary MCP tool calls. ([174eba9](https://github.com/elastic/relevance-studio/commit/174eba9))
- Improved system prompt quality and navigation ergonomics across the updated chat/user flows. ([e9eacdd](https://github.com/elastic/relevance-studio/commit/e9eacdd))

### Bug fixes

- Fixed agent reliability with stronger error handling and loop refactoring; improved chat safety with message sanitization. ([96783d6](https://github.com/elastic/relevance-studio/commit/96783d6), [3649e91](https://github.com/elastic/relevance-studio/commit/3649e91))
- Fixed quickstart execution and docs guidance, including interactive-input handling and the move to `bash <(curl -fsSL https://ela.st/relevance-studio-quickstart)`. ([c374797](https://github.com/elastic/relevance-studio/commit/c374797), [e949bec](https://github.com/elastic/relevance-studio/commit/e949bec), [4b8c630](https://github.com/elastic/relevance-studio/commit/4b8c630), [b74c7f0](https://github.com/elastic/relevance-studio/commit/b74c7f0))
- Fixed upgrade-path regressions by restoring MCP tool docstring behavior and adding setup/upgrade integration test coverage in CI. ([c2c0399](https://github.com/elastic/relevance-studio/commit/c2c0399), [bb8d1b2](https://github.com/elastic/relevance-studio/commit/bb8d1b2))
- Improved handling for missing inference endpoints, reachability checks, and license requirements in home/chat workflows. ([32431ed](https://github.com/elastic/relevance-studio/commit/32431ed), [d01740d](https://github.com/elastic/relevance-studio/commit/d01740d), [cefeafe](https://github.com/elastic/relevance-studio/commit/cefeafe), [3793d5c](https://github.com/elastic/relevance-studio/commit/3793d5c))

### Removed

- Removed the scatterplot and replaced categorical red/yellow/green scoring visuals with monochromatic scales to prevent misleading interpretations in the evaluation overview page. ([f2bb6a0](https://github.com/elastic/relevance-studio/commit/f2bb6a0))
