# Elasticsearch Relevance Studio

*You know, for search relevance.*

Elasticsearch Relevance Studio manages the lifecycle of **search relevance engineering** so you can deliver amazing search experiences.

🚀  **[Get started](https://elastic.github.io/relevance-studio/#/docs/guide/quickstart)**<br/>
📖  **[Learn more](https://elastic.github.io/relevance-studio/#/docs/guide/welcome)**


## Why Elasticsearch Relevance Studio?

### Meet the new demands of search.

Search is more relevant than ever. Generative AI has raised the bar on our expectations for search. We expect to find relevant content faster than ever before. "Faster" doesn't just mean getting quick answers – it means getting the **best answer** the **first time** so we don't have to continue the hunt in a list of links.

But AI isn't magic. AI agents can only search within the abilities of the data store that holds your content. That means the data store is a weak link in the chain of matching the intent of a prompt with its most relevant answer. It also means the world of search relevance engineering hasn't gone away – it just moved in the tech stack and became more important.

Luckily, there is one battle-tested data store designed to handle the complex nature of search. [Elasticsearch](https://www.elastic.co/elasticsearch) is the most comprehensive solution to power agentic search today. **Elasticsearch Relevance Studio** helps you build the best strategies for your search applications using any configuration of queries, retrievers, or index settings that touch the [Search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search) of Elasticsearch, such as:

- [Vector search](https://www.elastic.co/docs/solutions/search/vector) (e.g. [kNN](https://www.elastic.co/docs/solutions/search/vector/knn))
- [Semantic search](https://www.elastic.co/docs/explore-analyze/machine-learning/nlp/ml-nlp-elser) (e.g. [ELSER](https://www.elastic.co/docs/explore-analyze/machine-learning/nlp/ml-nlp-elser))
- [Lexical search](https://www.elastic.co/docs/solutions/search/full-text) (e.g. [BM25](https://www.elastic.co/blog/practical-bm25-part-2-the-bm25-algorithm-and-its-variables), [text analysis](https://www.elastic.co/docs/manage-data/data-store/text-analysis), [synonyms](https://www.elastic.co/docs/solutions/search/full-text/search-with-synonyms))
- [Hybrid search](https://www.elastic.co/docs/solutions/search/hybrid-search) (e.g. [RRF](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion), [linear combination](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/retrievers/linear-retriever))
- [Specialized search](https://www.elastic.co/docs/reference/query-languages/query-dsl/specialized-queries) (e.g. [geospatial](https://www.elastic.co/docs/reference/query-languages/query-dsl/geo-queries), [function score](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-function-score-query), [script score](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-script-score-query), [rank features](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-rank-feature-query), [rules](https://www.elastic.co/docs/reference/query-languages/query-dsl/query-dsl-rule-query))
- [Reranking](https://www.elastic.co/docs/solutions/search/ranking/semantic-reranking) (e.g. [Elastic Rerank](https://www.elastic.co/docs/explore-analyze/machine-learning/nlp/ml-nlp-rerank))
- [Learning to Rank](https://www.elastic.co/docs/solutions/search/ranking/learning-to-rank-ltr)
- [Quantization](https://www.elastic.co/search-labs/blog/scalar-quantization-101) (e.g. [BBQ](https://www.elastic.co/search-labs/blog/bbq-implementation-into-use-case))
- [Cross-cluster search](https://www.elastic.co/docs/solutions/search/cross-cluster-search)

### Standardize on a framework.

Search relevance engineering is an area of constant research and innovation, as you can see in past [presentations](https://haystackconf.com/talks/) from the *Haystack* conference series. While there are some generally accepted concepts and best practices, there are no strict standards for implementation. This can introduce toil and friction in your process, with people reinventing the wheel and creating inconsistent results.

**Elasticsearch Relevance Studio** establishes a framework built on generally accepted concepts and best practices found in many search relevance engineering operations.

- Concepts – [Scenarios](https://elastic.github.io/relevance-studio/#/docs/guide/concepts#scenario), [Judgements](https://elastic.github.io/relevance-studio/#/docs/guide/concepts#judgement), [Strategies](https://elastic.github.io/relevance-studio/#/docs/guide/concepts#strategy)
- Metrics – [NDCG](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#_discounted_cumulative_gain_dcg), [Precision](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#k-precision), [Recall](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#k-recall), [MRR](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval#_mean_reciprocal_rank)
- Technology – [Elasticsearch](https://www.elastic.co/elasticsearch), [Search API](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-search), [Search templates](https://www.elastic.co/docs/solutions/search/search-templates), [MCP](https://modelcontextprotocol.io/docs/getting-started/intro)
- Monitoring – [OpenTelemetry](https://opentelemetry.io/)

### Manage your ground truth data with ease.

Search relevance engineering relies on a carefully curated set of [judgements](https://elastic.github.io/relevance-studio/#/docs/guide/concepts#judgement) that represent the ground truth for what is (or is not) relevant to your search scenarios. This can be *extremely* tedious and time consuming without a platform to make it intuitive.

**Elasticsearch Relevance Studio** lets you judge documents efficiently with your intuition: browse for candidates, see the details that matter, drag a rating slider, and repeat. This interface accelerates your ability to judge by an order of magnitude. Using AI agents? The same interface lets you review and adjust any judgements made by AI.

#### Life before Elasticsearch Relevance Studio

<img src="https://storage.googleapis.com/esrs-docs/screenshots/judgements-before.png" class="screenshot">

#### Life with Elasticsearch Relevance Studio

<img src="https://storage.googleapis.com/esrs-docs/screenshots/judgements.png" class="screenshot">

### Move strategies in the right direction.

With your ground truth judgements in place, you can get immediate relevance feedback with every change you make to your search strategies. Just press `Ctrl/Cmd + Enter` at any time to see the ratings and relevance metrics for your current strategy draft on a chosen scenario. It's like an IDE for search relevance.

<img src="https://storage.googleapis.com/esrs-docs/screenshots/strategy.png" class="screenshot">

### Adapt to model drift and regressions.

Search is dynamic. Content and behaviors can change over time. The search strategies you deployed yesterday can silently degrade tomorrow. This is **model drift**. As you adapt to change, the optimizations you make for one set of scenarios might negatively affect ones you haven't tested. These are **regressions**.

**Elasticsearch Relevance Studio** can surface model drift and regressions before they impact your users. Schedule [benchmarks](https://elastic.github.io/relevance-studio/#/docs/guide/concepts#benchmark) with your latest data to detect drift in your search strategies. Run benchmarks from your CI/CD pipeline to prevent regressions from reaching production. And find root causes in the analytics interface – or let AI find them for you.


<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-summary.png" class="screenshot" />

<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-heatmap.png" class="screenshot" />

<img src="https://storage.googleapis.com/esrs-docs/screenshots/evaluation-runtime-assets.png" class="screenshot" />

### AI ready :sparkles:

Elasticsearch Relevance Studio is equipped with an [MCP Server](https://elastic.github.io/relevance-studio/#/docs/reference/architecture#recommended-setup-with-mcp) to enable Agentic AI workflows. This means you can automate the entire lifecyle of search relevance engineering: reviewing your content, defining scenarios, judging documents, building strategies, learning from benchmarks, and iterating to optimize performance.

### Scale up your operations.

All of this comes down to one overarching value proposition:

_**Elasticsearch Relevance Studio** scales up your search relevance engineering operations so you can deliver better search experiences faster._

With an opinionated framework, intuitive human interface, and integration with AI agents, you can achieve much greater quality and coverage than could ever be done alone.

---

### Ready to start?

🚀  **[Get started](https://elastic.github.io/relevance-studio/#/docs/guide/quickstart)**