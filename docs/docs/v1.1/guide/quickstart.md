# Quickstart

Elasticsearch Relevance Studio has a docker compose file so you can see how everything works before planning a production deployment.

This quickstart guide was tested with macOS 15.5, Docker 27.3.1, and Elasticsearch 9.0.3.

#### Prerequisites

This quickstart guide assumes that you have:

* [docker](https://docs.docker.com/engine/install/) installed on your machine
* An Elasticsearch deployment (8.18 or higher) where your content is stored
* An Elasticsearch deployment (8.18 or higher) where Elasticsearch Relevance Studio will store its assets (this can be the same as your content deployment)

#### Step 1. Run the Quickstart Script

Download and run the quickstart script:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --version {{VERSION}}`**

The script clones the repository to `./relevance-studio/`, guides you through the setup process, and starts the services with Docker Compose.

You can use `--dir` to install to a different directory:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --version {{VERSION}} --dir my-directory`**

Use `--help` to see all available options:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --help`**

💡 *Read [roles and permissions](docs/{{VERSION}}/reference/security.md#roles-and-permissions) to see the recommended configurations for security.*

#### Step 2. Open Elasticsearch Relevance Studio to finish setup

Once the quickstart script has finished, open Elasticsearch Relevance Studio in a web browser:

[http://localhost:4096/](http://localhost:4096/)

...then click the "Setup" button to finish the setup.

You're ready to go! :rocket:

---

## Next steps

Relevance engineers should become familiar with the [concepts](docs/{{VERSION}}/guide/concepts.md) of Elasticsearch Relevance Studio.

Administrators can refer to the [architecture](docs/{{VERSION}}/reference/architecture.md) and [security](docs/{{VERSION}}/reference/security.md) documentation to plan a deployment that meets your requirements for infrastructure, scalability, and security.