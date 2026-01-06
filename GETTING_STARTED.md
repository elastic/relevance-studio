# Getting Started

Relevance Studio is a tool for evaluating search quality by running Elasticsearch queries (strategies) against test cases (scenarios) using relevance labels (judgements).

Get Relevance Studio running with Cursor in 2 steps.

## 1. Create `.env`

```bash
cp .env-reference .env
```

Edit `.env` with your Elasticsearch connection:

```bash
# Pick ONE of these:
ELASTIC_CLOUD_ID=your-cloud-id
# OR
ELASTICSEARCH_URL=https://localhost:9200

# Pick ONE auth method:
ELASTICSEARCH_API_KEY=your-api-key
# OR
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=changeme
```

## 2. Start it

```bash
docker compose up --build
```

> **Note:** If Cursor shows the MCP server as unavailable, toggle it off and on in Cursor Settings → MCP.

## First time only

Open [http://localhost:4096](http://localhost:4096) and click **Setup** to create the Elasticsearch indices.

---

## Try it out

Ask Cursor:

> "Using the relevance-studio integration tell me about the tests, etc. we have?"

---

## Terminology

| Relevance Studio | Simple Term | What It Means |
|------------------|----------------------|----------------------------------------|
| **Scenario** | User search query | A query you want to evaluate (e.g., "brown oxfords"). |
| **Judgement** | Relevance rating | Human assessment of how relevant a result is for a scenario (0-4 scale). |
| **Strategy** | Elasticsearch query | The actual ES query (DSL) being tested. |
| **Benchmark** | Evaluation | Running strategies against scenarios + judgements to measure quality. |
