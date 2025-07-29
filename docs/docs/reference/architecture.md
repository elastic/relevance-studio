# Architecture

## Application

- [UI](#ui) - Provides a human user experience in a web browser
- [Server](#server) - Provides a REST API for the UI and worker(s)
- [Worker](#worker) - Checks for pending evaluations and runs them
- [MCP Server](#mcp-server) *(optional)* - Enables MCP over HTTP for AI agents
- [MCP Proxy](#mcp-proxy) *(optional)* - Enables MCP over stdio for local AI agents (e.g. Claude Desktop)

## Elasticsearch

- [Studio deployment](#studio-deployment) - Stores application workspace assets
- [Content deployment](#content-deployment) - Stores documents to be judged and runs rank evaluation

## Ports and protocols

These are the default ports and protocols used by Relevance Studio:

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

---

## Deployment patterns

### Minimal setup

<img src="../img/architecture-minimal.png" style="float: right; max-width: 400px; padding-left: 15px;" />

This is the simplest deployment pattern of Relevance Studio. A minimal setup includes the UI, Server, a Worker, and an Elasticsearch deployment that stores both the studio assets and the content.

*Note: Technically the UI is optional. The Server handles the full lifecycle of Relevance Studio, and so the application could be used entirely programatically using the REST API.*

<div style="clear: both;"/>

---

### Minimal setup with MCP

<img src="../img/architecture-minimal-mcp.png" style="float: right; max-width: 400px; padding-left: 15px;" />

This pattern extends the [minimal setup](#minimal-setup) by introducing the MCP Server.  The MCP Server makes it possible to use Relevance Studio in agentic workflows using the [Model Context Protocol (MCP)](https://modelcontextprotocol.io) over HTTP.

*Note: The MCP Server doesn't depend on the Server. They provide separate implementations of the backend API.*

<div style="clear: both;"/>

---

### Recommended setup

<img src="../img/architecture-recommended.png" style="float: right; max-width: 400px; padding-left: 15px;" />

The recommended pattern separates the studio assets from the content into two Elasticsearch deployments. It also acknowledges that multiple Workers can run in parallel.

Advantages over the [minimal setup](#minimal-setup):

- Separating the studio deployment and the content deployment offers greater flexibility in terms of security and scalability.
- Adding additional workers increases the number of evaluations that can run in parallel. This can be useful for deployments with a large number of benchmarks. 

<div style="clear: both;"/>

---

### Recommended setup with MCP

<img src="../img/architecture-recommended-mcp.png" style="float: right; max-width: 400px; padding-left: 15px;" />

This pattern extends the [recommended setup](#recommended-setup) by introducing the MCP Server. The MCP Server follows the same implementation pattern as the [minimal setup with MCP](#minimal-setup-with-mcp).

<div style="clear: both;"/>

---

### Recommended setup with MCP and Proxy for Claude Desktop

<img src="../img/architecture-recommended-mcp-proxy.png" style="float: right; max-width: 400px; padding-left: 15px;" />

This pattern extends the [recommended setup with MCP](#recommended-setup-with-mcp) by introducing a local proxy designed primarily for integration Claude Desktop.

The MCP Proxy brokers communications between Claude Desktop and the MCP Server. The proxy must run on the same machine Claude Desktop. Claude Desktop communicates with the local MCP Proxy over stdio, and the MCP Proxy communicates with the MCP Server over HTTP. You can learn more about the details of this pattern in the [FastMCP documentation for Claude Desktop](https://gofastmcp.com/integrations/claude-desktop).

<div style="clear: both;"/>