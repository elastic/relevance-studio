# Quickstart

Elasticsearch Relevance Studio has a docker compose file so you can see how everything works before planning a production deployment.

This quickstart guide was tested with macOS 15.5, Docker 27.3.1, and Elasticsearch 9.0.3.

#### Prerequisites

This quickstart guide assumes that you have:

* [docker](https://docs.docker.com/engine/install/) installed on your machine
* An Elasticsearch deployment (8.x or higher) where your content is stored
* An Elasticsearch deployment (8.x or higher) where Relevance Studio will store its assets (this can be the same as your content deployment)

#### Step 1. Download Relevance Studio

Clone the repo:

**`git clone https://github.com/elastic/relevance-studio.git`**

...then enter the project directory:

**`cd relevance-studio`**

#### Step 2. Configure its connections to Elasticsearch

Create your `.env` file from the given `.env-reference` file:

**`cp .env-reference .env`**

...then configure your `.env` to use the endpoints and credentials of your Elasticsearch deployment(s).

💡 *Read [roles and permissions](docs/{{VERSION}}/reference/security.md#roles-and-permissions) to see the recommended configurations for security.*

#### Step 3. Start Relevance Studio

Start Relevance Studio with docker compose:

**`docker compose up --build`**

...then open it in a web browser:

[http://localhost:4096/](http://localhost:4096/)

...then click the "Setup" button to finish the setup.

You're ready to go! :rocket:

#### Connect Claude Desktop to Relevance Studio <span style="font-weight: 300">(optional)</span>

Claude Desktop provides a way to use with Relevance Studio with an AI assistant. The docker compose file deploys an MCP server and a proxy that handles communications between Claude Desktop and Relevance Studio.

Install these on your machine:

- [Claude Desktop](https://claude.ai/download)
- [fastmcp](https://github.com/jlowin/fastmcp?tab=readme-ov-file#installation)

...then run this command from the project directory:

**`fastmcp install claude-desktop src/server/fastmcp_proxy.py`**

...then restart Claude Desktop.

Verify if things are working by asking Claude:

*Are you connected to Relevance Studio?*

Enjoy!

---

## Next steps

Relevance engineers should become familiar with the [concepts](docs/{{VERSION}}/guide/concepts.md) of Elasticsearch Relevance Studio.

Administrators can refer to the [architecture](docs/{{VERSION}}/reference/architecture.md) and [security](docs/{{VERSION}}/reference/security.md) documentation to plan a deployment that meets your requirements for infrastructure, scalability, and security.