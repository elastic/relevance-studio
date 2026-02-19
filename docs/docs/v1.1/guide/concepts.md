# Concepts

Elasticsearch Relevance Studio is an opinionated framework for search relevance engineering. This page explains the concepts of that framework.

- [Agent](#agent)
- [Conversation](#conversation)
- [Workspace](#workspace)
- [Content](#content)
- [Display](#display)
- [Scenario](#scenario)
- [Judgement](#judgement)
- [Strategy](#strategy)
- [Benchmark](#benchmark)
- [Evaluation](#evaluation)
- [Relevance metrics](#relevance-metrics)

## Agent

An agent is the AI assistant implemented by the [Server](docs/{{VERSION}}/reference/architecture.md) and consumed through the [UI](docs/{{VERSION}}/reference/architecture.md) via the [Agent API](docs/{{VERSION}}/reference/rest-api.md#agent-api). It can interpret your request, use [MCP tools](docs/{{VERSION}}/reference/mcp-tools.md), and return a streamed response.

In practice, the agent uses workspace and UI context to reduce unnecessary tool calls and stay focused on the assets you are currently working with. Conversations persist the results of these interactions for later reference.

See also:

- [Agent API](docs/{{VERSION}}/reference/rest-api.md#agent-api)
- [MCP Tools](docs/{{VERSION}}/reference/mcp-tools.md)

---

## Conversation

A conversation is a persisted record of chat interaction with the built-in AI assistant. It includes a title and an ordered sequence of rounds.

Each round captures the user message, assistant response, and optional execution details such as tool calls and model usage. Conversations make AI-assisted relevance work reproducible and easier to review over time.

See also:

- [Conversations data model](docs/{{VERSION}}/reference/data-model.md#conversations)
- [Conversations API](docs/{{VERSION}}/reference/rest-api.md#conversations-api)
- [Conversations MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#conversations)

---

## Workspace

A workspace is a place to scope your work. Every asset you create is tied to a workspace. This keeps things organized and focused when working with multiple projects or teams.

A workspace also enforces consistency in the assets you create:

- **Content scope** - A workspace scopes all searches to a single index pattern in which your content resides. This index pattern is used by all [scenarios](#scenario), [judgements](#judgement), and [benchmarks](#benchmark) in the workspace. Searches span all indices represented in the index pattern as if they were a single index.
- **Rating scale** - A workspace enforces a consistent rating scale for all judgements. The scale can be graded (such as `0` to `4`) or binary (`0` to `1`). Whatever scale you choose, the lower bound always indicates complete irrelevance and the upper bound indicates superb relevance.
- **Search parameters** - A workspace defines the input fields that your search application uses. A common parameter is `text` which represents the text from a search bar or prompt. These are used by scenarios (which define values for those inputs) and [strategies](#strategy) (which substitute the variables of their search templates with the values from a scenario).
- **Description** - A workspace can include a markdown-formatted description to capture context such as use case, target audience, or constraints for your relevance work. This serves as guiding context for humans and agents.

See also:

- [Workspaces data model](docs/{{VERSION}}/reference/data-model.md#workspaces)
- [Workspaces API](docs/{{VERSION}}/reference/rest-api.md#workspaces-api)
- [Workspaces MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#workspaces)

---

## Content

Content refers to the documents that your search application retrieves from the [content deployment](docs/{{VERSION}}/reference/architecture.md#elasticsearch). In Elasticsearch Relevance Studio, content is queried through index patterns, then reviewed and rated through scenarios and judgements.

Workspaces define the index pattern scope for content operations. Displays determine how content is retrieved and rendered for judging, while strategies define how content is searched.

See also:

- [Content API](docs/{{VERSION}}/reference/rest-api.md#content-api)
- [Content MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#content)

---

## Display

A display is a custom presentation for documents from a given index, formatted using Markdown syntax. It serves two purposes:

- **See what matters** - A display presents only the details that you want to see when [judging](#judgement) relevance. This makes it much easier to judge the relevance of a document to a [scenario](#scenario).
- **Optimize costs** - A display improves search performance, reduces outbound data transfer, and reduces token usage (if using AI) by excluding the retrieval of data that isn't needed to judge relevance. This is especially important for documents with large vector fields, text fields, and metadata.

Let's look at an example. Here's how a document looks without a display, which falls back to its raw JSON format:

<img src="https://storage.googleapis.com/esrs-docs/screenshots/display-json.png" class="screenshot" />

And here's how the same document can look with a display:

<img src="https://storage.googleapis.com/esrs-docs/screenshots/display-markdown.png" class="screenshot" />

See also:

- [Displays data model](docs/{{VERSION}}/reference/data-model.md#displays)
- [Displays API](docs/{{VERSION}}/reference/rest-api.md#displays-api)
- [Displays MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#displays)

---

## Scenario

A scenario is a hypothetical input to your search application. It defines the values to one or more of the search parameters defined in your [workspace](#workspace).

Many times, all a scenario needs is a `text` parameter, representing the text that a user gives in the search bar or prompt. But you can include other parameters that might be worth testing, such as the language or location of the user if your [strategies](#strategy) need to personalize the results.

Scenarios can be tagged. This is a good way to categorize scenarios, such as `"head"` for vague or general searches and `"tail"` for highly specific searches. With tags, you can create benchmarks for certain types of scenarios, and you can summarize [relevance metrics](#relevance-metrics) by tags in the [evaluation](#evaluation) interface.

See also:

- [Scenarios data model](docs/{{VERSION}}/reference/data-model.md#scenarios)
- [Scenarios API](docs/{{VERSION}}/reference/rest-api.md#scenarios-api)
- [Scenarios MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#scenarios)

---

## Judgement

A judgement is a rating for how relevant a document is to a chosen [scenario](#scenario). Judgements are the basis for measuring relevance, which is why they are considered the "ground truth" data set in search relevance engineering. [Strategies](#strategy) are considered more relevant when their top results have more documents with highly rated judgements.

Judgements conform to the rating scale that you defined in the [workspace](#workspace). The scale can be graded (such as `0` to `4`) or binary (`0` to `1`). The lower bound always indicates complete irrelevance, and the upper bound indicates superb relevance. Raters should agree on clear definitions for intermediate ratings to ensure that judgements are consistent and comparable. It's important to be careful and consistent when making judgements, because a poor quality set of judgements will lead to inaccurate or untrustworthy [relevance metrics](#relevance-metrics).

Here's an example of a highly rated judgement for a document in a product catalog that was made for the scenario `"brown oxfords"`. If this document appears in the top results for a strategy that searches for "brown oxfords", then that strategy will earn higher [relevance metrics](#relevance-metrics).

<img src="https://storage.googleapis.com/esrs-docs/screenshots/judgement.png" class="screenshot" />

See also:

- [Judgements data model](docs/{{VERSION}}/reference/data-model.md#judgements)
- [Judgements API](docs/{{VERSION}}/reference/rest-api.md#judgements-api)
- [Judgements MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#judgements)

---

## Strategy

A strategy is a [search template](https://www.elastic.co/docs/solutions/search/search-templates) whose relevance will be measured in [benchmarks](#benchmark). It can be any retriever or query that runs in the [Search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search) of Elasticsearch. Search templates accept parameters in the form of Mustache variables (e.g. `"{{ text }}"`), which is how the values of [scenarios](#scenario) are passed to strategies.

Strategies can be tagged. This is a good way to categorize strategies, such as `vector` for vector queries or `hybrid` for queries that use reciprocal rank fusion or linear combination. With tags, you can create benchmarks for certain types of strategies, and you can summarize [relevance metrics](#relevance-metrics) by tags in the [evaluation](#evaluation) interface.

Here's an example of a strategy that accepts a variable `text` parameter from scenarios and then performs a semantic search over several fields in a product catalog.

```json
{
  "retriever": {
    "standard": {
      "query": {
        "bool": {
          "should": [
            {
              "semantic": {
                "field": "name.elser",
                "query": "{{ text }}",
                "boost": 2
              }
            },
            {
              "semantic": {
                "field": "categories.elser",
                "query": "{{ text }}",
                "boost": 1.8
              }
            },
            {
              "semantic": {
                "field": "color.elser",
                "query": "{{ text }}",
                "boost": 1.6
              }
            },
            {
              "semantic": {
                "field": "description.elser",
                "query": "{{ text }}",
                "boost": 1.4
              }
            }
          ]
        }
      }
    }
  }
}
```

See also:

- [Strategies data model](docs/{{VERSION}}/reference/data-model.md#strategies)
- [Strategies API](docs/{{VERSION}}/reference/rest-api.md#strategies-api)
- [Strategies MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#strategies)

---

## Benchmark

A benchmark is a reusable task definition for evaluating the relevance of a set of strategies against a set of scenarios. You can think of a benchmark as a test suite in software testing, in which [strategies](#strategy) are the systems being tested, [scenarios](#scenario) are the test cases, [judgements](#judgement) are the assertions or expected results, and [relevance metrics](#relevance-metrics) are the results.

By default, a benchmark will evaluate every strategy against every scenario. You can limit the selection of strategies and scenarios by their respective tags. A benchmark will only evaluate strategies and scenarios that are compatible with each other. If a scenario has a parameter called `language` but none of the strategies implement the `language` parameter, then that scenario has no compatible strategies, so it won't be evaluated. Additionally, a benchmark will randomly sample scenarios if there are more than 1,000 of them, up to a maximum of 10,000 scenarios. You can configure the sample size and provide a seed value to ensure that the same sample is used between evaluation runs for better consistency and comparison.

Here's an example of a benchmark that measures NDCG, Precision, and Recall for strategies tagged with `bm25`, `elser`, or `signals`, and all scenarios that are compatible with those strategies.

<img src="https://storage.googleapis.com/esrs-docs/screenshots/benchmark.png" class="screenshot" />

See also:

- [Benchmarks data model](docs/{{VERSION}}/reference/data-model.md#benchmarks)
- [Benchmarks API](docs/{{VERSION}}/reference/rest-api.md#benchmarks-api)
- [Benchmarks MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#benchmarks)

---

## Evaluation

An evaluation is the output of a [benchmark](#benchmark) run. It has the task definition, the relevance metrics for each [strategy](#strategy) and [scenario](#scenario) and their tags, the results of the rank evaluation requests, the documents that lacked judgements while appearing in the results, the contents of the index states and [workspace](#workspace) assets used at runtime, and any failures that occurred. Altogether, it's a large document with great explanatory insights into the relevance of the strategies.

<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-summary.png" class="screenshot" />

<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-heatmap.png" class="screenshot" />

<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-runtime-assets.png" class="screenshot" />

See also:

- [Evaluations data model](docs/{{VERSION}}/reference/data-model.md#evaluations)
- [Evaluations API](docs/{{VERSION}}/reference/rest-api.md#evaluations-api)
- [Evaluations MCP tools](docs/{{VERSION}}/reference/mcp-tools.md#evaluations)

---

## Relevance metrics

Relevance metrics are what you try to maximize in Elasticsearch Relevance Studio.

[Benchmarks](#benchmark) support the following metrics, which are calculated by the [Ranking Evaluation API](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval) in Elasticsearch:

- **[NDCG](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#_discounted_cumulative_gain_dcg)** *(Normalized Discounted Cumulative Gain)* - Measures how well the top `k` results were ordered by their judged relevance.
- **[Precision](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#k-precision)** - Measures how many of the top `k` documents were judged as relevant.
- **[Recall](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#k-recall)** - Measures how many relevant documents were retrieved.
- **[MRR](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#_mean_reciprocal_rank)** *(Mean Reciprocal Rank)* - Measures how early the first relevant document appears in the results.
