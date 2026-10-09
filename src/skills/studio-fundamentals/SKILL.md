---
name: "studio-fundamentals"
description: "Use whenever a task touches Elasticsearch Relevance Studio or its MCP tools (workspaces, displays, scenarios, judgements, strategies, benchmarks, evaluations, content search, conversations). Explains the data model, mandatory conventions (workspace scoping, never fabricating IDs, display-driven _source filtering, confirming bulk or destructive changes), known tool behaviors and traps, and how to link to pages in the Studio UI. Load it once per conversation whenever the user is doing search relevance work such as judging results, measuring NDCG, comparing search strategies, building test queries, or tuning Elasticsearch ranking, even if they don't name Relevance Studio by name."
---

## When this applies

Load this skill once at the start of any conversation that works with Elasticsearch
Relevance Studio: creating or editing workspaces, displays, scenarios, judgements,
strategies, benchmarks, or evaluations; running searches against content indices through
`content_search`; or analyzing relevance metrics. Every other skill in this plugin assumes
you've already loaded it.

## Concepts

Relevance Studio is an opinionated framework for search relevance engineering, built around
eight asset types:

- **conversations** — chat history between a user and an agent. The only asset that is
  **global**, not workspace-scoped.
- **workspaces** — a namespace for every other asset. Scopes content searches to one
  `index_pattern`, enforces one `rating_scale` for judgements, and defines the `params`
  (search inputs like `text`) that scenarios and strategies share.
- **displays** — a Markdown template controlling how documents from a given `index_pattern`
  are rendered and which fields are fetched (`fields`, computed from Mustache variables in
  `template.body` and `template.image.url`).
- **scenarios** — a search input (e.g. `"brown oxfords"`) with `values` for one or more
  workspace `params`.
- **judgements** — a relevance rating for one document (`index` + `doc_id`) against one
  scenario, within the workspace's `rating_scale`.
- **strategies** — an Elasticsearch Search API body (`query` or `retriever`) as a search
  template, with Mustache placeholders populated by scenario values.
- **benchmarks** — a reusable task definition: which scenarios, strategies, and metrics to
  evaluate together.
- **evaluations** — the result of running a benchmark: per-strategy, per-scenario relevance
  metrics plus raw rank-eval results.

The lifecycle is: **workspace → displays → scenarios → judgements → strategies →
benchmarks → evaluations → iterate.** For routing a user's request to the right skill, see
"Which skill do I need?" below. For field-level detail, metrics, gotchas, and deep links, see
`references/`.

## Behavioral rules (every skill inherits these)

These are non-negotiable across every skill in this plugin:

1. **Scope every operation to a `workspace_id`.** Conversations are the only global asset.
   See "Resolving the active workspace" below for how to determine it.
2. **Never fabricate `_id` or `doc_id` values.** Always look them up with a `*_search` or
   `*_get` tool first.
3. **Always use display-driven `_source` filtering** on `content_search` and
   `judgements_search`. Content documents can carry large vector or metadata fields that
   waste tokens and bandwidth if fetched in full.
4. **Confirm before bulk operations.** "Bulk" means more than 10 creates or updates in a
   single plan, or any delete.
5. **Confirm before modifying a workspace other than the active one.**
6. **Refer to assets by name, not ID**, in responses. Hyperlink names to Studio pages when a
   base URL is known (see `references/deep-links.md`).
7. **Never dump raw JSON** from tool results. Summarize in tables or bullet points.
8. **Explain tool errors in plain language.** Never silently swallow them.

## Resolving the active workspace

Unlike the built-in agent (which reads a UI Context block), external clients have no page
context. Resolve the workspace in this order:

1. Use a workspace already established earlier in this conversation, if any.
2. Otherwise, ask the user. If they give a name instead of an ID, resolve it with
   `workspaces_search`.
3. If there's no good match, say so and stop — don't guess or proceed without a workspace.

## Which skill do I need?

| User intent | Skill |
|---|---|
| Tools missing, auth/TLS errors, first-time setup | `connect-and-verify` |
| Upgrade needed, stuck/failed evaluations | `upgrade-and-maintenance` |
| Start a new use case, create/edit a workspace | `workspace-bootstrap` |
| Define what each rating level means | `judgement-rubric` |
| Understand the index's fields before building displays/strategies | `content-profiling` |
| Documents render as raw JSON while judging | `display-authoring` |
| Need test queries / scenarios | `scenario-generation` |
| Decide which docs to judge | `judgement-pooling` |
| Have Claude rate documents | `llm-judging` |
| Check judgement quality/coverage | `judgement-audit` |
| Reduce an evaluation's unrated % | `judgement-gap-fill` |
| Write or fix a search template | `strategy-authoring` |
| No strategies yet, want standard baselines | `baseline-suite` |
| A strategy performs poorly on specific scenarios | `strategy-diagnosis` |
| Tune boosts/weights/retrievers and compare variants | `strategy-experiments` |
| Create/edit a benchmark, choose metrics or k | `benchmark-design` |
| Run a benchmark or check evaluation status | `evaluation-execution` |
| Explain evaluation results | `evaluation-analysis` |
| Compare two or more evaluations | `evaluation-comparison` |
| Open-ended: "help me evaluate my search" | `lifecycle-orchestrator` |
| Iterate toward a metric target | `improvement-loop` |
| Version-control or export assets as files (Code only) | `assets-as-code` |
| CI regression gate for strategies (Code only) | `ci-gate` |
| Summarize results for stakeholders | `stakeholder-report` |
| Record Studio work in a conversation for teammates | `conversation-journaling` |
| Clean up unused/stale assets | `workspace-hygiene` |
| Create/manage tags | `tagging-conventions` |

## Reference files

Read these on demand — don't load them all up front:

- `references/data-model.md` — every asset's fields, which are server-computed, which are
  immutable, and what each delete cascade removes. Read before creating or updating any asset.
- `references/mcp-tools.md` — every MCP tool: purpose, parameters, return shape, notes. Read
  when unsure of a tool's exact signature.
- `references/gotchas.md` — known traps verified against the server code. Read before any
  non-trivial operation (evaluations, strategy authoring, judgement filtering).
- `references/deep-links.md` — URL patterns for linking to Studio UI pages.
- `references/metrics.md` — what NDCG, precision, recall, and MRR measure and when to prefer
  each. Read before designing a benchmark or explaining evaluation results.

## Tools

`workspaces_search`, `workspaces_get`, `healthz_mcp`. (Most other tools are used by
downstream skills — see the routing table above.)

## Examples

**Correct (resolves workspace before acting):**
User: "Create a scenario for red running shoes." Claude: "Which workspace should I add this
to?" (no workspace established yet, so it asks rather than guessing).

**Incorrect (fabricates an ID):**
User: "Add a judgement for doc abc123 in the products index." Claude invents a
`scenario_id` instead of calling `scenarios_search` to find the real one.

## Next steps

Any skill may follow, depending on intent — see the routing table above. When tools are
missing or erroring, start with `connect-and-verify`. For an open-ended request, use
`lifecycle-orchestrator`.
