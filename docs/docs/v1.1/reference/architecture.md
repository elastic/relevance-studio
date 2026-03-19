# Architecture

- [Diagram](#diagram)
- [Components](#components)
    - [Server](#server)
    - [Agent](#agent)
    - [UI](#ui)
    - [Worker](#worker)
    - [MCP Server](#mcp-server)
    - [MCP Proxy](#mcp-proxy)
- [External components](#external-components)
    - [Studio Deployment](#studio-deployment)
    - [Content Deployment](#content-deployment)
- [Ports and protocols](#ports-and-protocols)

## Diagram

This diagram shows all required and optional [components of Elasticsearch Relevance Studio](#components), the external components that interface with them, their lines of communication, and the protocols by which they communicate.

<img src="https://storage.googleapis.com/esrs-docs/architecture/architecture-v1.1-reference.png" />

## Components

### Server

The Server is the central HTTP service in Elasticsearch Relevance Studio. It serves the [UI](#ui), exposes the [REST API](docs/{{VERSION}}/reference/rest-api.md), and coordinates reads and writes to the [Studio Deployment](#studio-deployment) and [Content Deployment](#content-deployment).

For users, this is the main integration point: the UI and API both go through the Server. It provides setup and health endpoints, plus workspace-scoped APIs for assets such as [displays](docs/{{VERSION}}/guide/concepts.md#display), [scenarios](docs/{{VERSION}}/guide/concepts.md#scenario), [judgements](docs/{{VERSION}}/guide/concepts.md#judgement), [strategies](docs/{{VERSION}}/guide/concepts.md#strategy), [benchmarks](docs/{{VERSION}}/guide/concepts.md#benchmark), and [evaluations](docs/{{VERSION}}/guide/concepts.md#evaluation).

For deployment and security considerations, see [Security](docs/{{VERSION}}/reference/security.md).

### Agent

The Agent is the AI assistant capability in Elasticsearch Relevance Studio. It handles chat interactions in the UI, uses LLM inference and [MCP tools](docs/{{VERSION}}/reference/mcp-tools.md), and persists [conversations](docs/{{VERSION}}/guide/concepts.md#conversation) in the [Studio Deployment](#studio-deployment). It's not a sandalone process, but rather a function executed by the Server.

Use the Agent for guided authoring and workflow assistance when working with workspace assets.

### UI

The User Interface (UI) is the browser experience for day-to-day relevance work. It is delivered by the [Server](#server) and uses the Server APIs.

The UI is organized around [workspaces](docs/{{VERSION}}/guide/concepts.md#workspace) and supports the full lifecycle of relevance engineering: defining [scenarios](docs/{{VERSION}}/guide/concepts.md#scenario), curating [judgements](docs/{{VERSION}}/guide/concepts.md#judgement), building [strategies](docs/{{VERSION}}/guide/concepts.md#strategy), creating [benchmarks](docs/{{VERSION}}/guide/concepts.md#benchmark), and analyzing [evaluations](docs/{{VERSION}}/guide/concepts.md#evaluation).

### Worker

A Worker is a background process that executes pending [evaluations](docs/{{VERSION}}/guide/concepts.md#evaluation). It polls the [Studio Deployment](#studio-deployment) for evaluation jobs, runs benchmark tasks against the [Content Deployment](#content-deployment), and writes results back to the Studio Deployment.

The Worker is what makes evaluations asynchronous. If you want to run benchmarks at all, run at least one Worker. You can run multiple Workers to increase throughput for larger benchmark workloads.

### MCP Server

The MCP Server enables [MCP](https://modelcontextprotocol.io) over HTTP for AI agents. It exposes most [REST API](docs/{{VERSION}}/reference/rest-api.md) operations as [MCP tools](docs/{{VERSION}}/reference/mcp-tools.md), so AI clients can perform the same core actions available through the REST API.

The MCP Server is required for the [Agent](#agent), and it can also be used directly by external MCP clients.

### MCP Proxy

The MCP Proxy is an optional bridge for local AI tools that require MCP over stdio (for example, Claude Desktop). It forwards stdio MCP traffic from the local tool to the [MCP Server](#mcp-server) over HTTP.

If you use this pattern, run the MCP Proxy on the same machine as the local AI client. You can learn more in the [FastMCP documentation for Claude Desktop](https://gofastmcp.com/integrations/claude-desktop).

## External components

### Studio Deployment

The Studio Deployment is an Elasticsearch deployment that stores Elasticsearch Relevance Studio [artifacts](docs/{{VERSION}}/reference/data-model) (workspaces, scenarios, judgements, strategies, benchmarks, evaluations, and related metadata). The [Server](#server), [Worker](#worker), and [MCP Server](#mcp-server) all connect to this deployment.

This deployment acts as the system-of-record for your relevance program.

### Content Deployment

The Content Deployment is an Elasticsearch deployment that stores the documents you search, judge, and evaluate. Evaluations run [rank evaluation](https://www.elastic.co/docs/api/doc/elasticsearch/operation/operation-rank-eval) on this deployment.

***This should not be a production deployment.*** Evaluation workloads can be resource-intensive and may degrade end-user search performance.

You can combine the Studio and Content deployments, but separating them is usually preferred for safer operations, clearer access boundaries, and independent scaling.

## Ports and protocols

These are the default ports and protocols used by Elasticsearch Relevance Studio:

|Service   |Port|Protocols|
|----------|----|---------|
|Server    |4096|HTTP     |
|Worker*   |-   |-        |
|MCP Server|4200|HTTP     |
|MCP Proxy*|-   |-        |

*&ast; The Worker and MCP Proxy don't expose ports because they don't accept remote connections.*

These are the default ports and protocols used by Elasticsearch:

|Service      |Port|Protocols  |
|-------------|----|-----------|
|Self-managed |9200|HTTP, HTTPS|
|Elastic Cloud|9243|HTTPS      |

You can learn more about the networking configuration of Elasticsearch here:

* For self-managed and open source: [Elasticsearch networking settings](https://www.elastic.co/docs/reference/elasticsearch/configuration-reference/networking-settings)
* For Elastic Cloud Enterprise (ECE): [ECE networking prerequisites](https://www.elastic.co/docs/deploy-manage/deploy/cloud-enterprise/ece-networking-prereq)