# Elasticsearch Relevance Studio

**Elasticsearch Relevance Studio** (`esrs`) is a framework and test harness for search relevance engineering.

> ⚠️ This application is in early development. Expect things to break or change often until it matures.

## Quickstart

1. Clone this repo: `git clone https://github.com/elastic/relevance-studio.git`
2. Enter the repo: `cd relevance-studio`
3. Copy `.env-reference` to `.env`
4. Configure `.env` to use the endpoints and credentials of your Elastic deployment
5. Start the app: `docker compose up --build`
6. Setup the index templates: `curl -XPOST http://localhost:4096/setup`
7. Open the app: [http://localhost:4096/](http://localhost:4096/)

To use MCP with Claude Desktop, you'll need to do Step 1 from the Development
section and then run `fastmcp install claude-desktop src/server/fastmcp_proxy.py`
to install the MCP proxy in Claude Desktop.

## Development

These instructions were tested on MacOS.

**Step 1. Prepare your environment**

Install dependencies:

1. Install [nvm](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating)
2. Install [yarn](https://classic.yarnpkg.com/en/docs/install) (tested on version 1.22.22)
3. Install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) (tested on version 25.3.1)
4. Install [docker](https://docs.docker.com/engine/install/) (tested on version 27.3.1)

Clone this repo:

1. Run `git clone https://github.com/elastic/relevance-studio.git`
2. Run `cd relevance-studio` to enter the root-level directory of this project
3. Copy `.env-reference` to `.env`
4. Configure `.env` to use the endpoints and credentials of your Elastic deployment

**Step 2. Run the server in develoment mode**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `conda create -n esrs python=3.10` to create a virtual environment
2. Run `conda activate esrs` to activate the virtual environment
3. Run `pip install -r requirements-dev.txt` to install the dependencies
4. Run `python -m src.server.flask` to run the server in development mode

Repeat steps 2 and 4 anytime you need to start the server in a new terminal.

**Step 3. Run the UI in development mode**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `nvm install && nvm use` to use the node version specified in .nvmrc
2. Run `yarn install` in the root project directory to install dependencies listed in `package.json`
3. Run `yarn run dev` to start the app using the script defined in `package.json`
4. Open [http://localhost:8080/](http://localhost:8080/) in your browser to open the app in development mode

Repeat steps 1, 3, and 4 anytime you need to start the UI in a new terminal.

**Step 4. Run an evaluation worker process**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `conda create -n esrs python=3.10` to create a virtual environment
2. Run `conda activate esrs` to activate the virtual environment
3. Run `python -m src.server.worker` to run a worker process

Repeat steps 2 and 3 anytime you need to start a worker in another terminal.

**Step 5. Setup the index templates and indices**

With the server and UI running from Steps 2 and 3, open [http://localhost:8080/](http://localhost:8080/) and click the button on the homepage to setup the index templates and indices.

**Step 6. (Optional) Run the MCP server and proxy for Claude Desktop**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `brew install uv` which is needed by Claude Desktop
2. Run `conda create -n esrs python=3.10` to create a virtual environment
3. Run `conda activate esrs` to activate the virtual environment
4. Run `pip install -r requirements-mcp.txt` to install the dependencies
5. Run `python -m src.server.fastmcp` to start the MCP server
6. Run `fastmcp install claude-desktop src/server/fastmcp_proxy.py` to install the MCP proxy in Claude Desktop
7. Restart Claude Desktop

Repeat steps 2, 3, 5, and 6 anytime you need to start the MCP server and proxy in another terminal.

Repeat steps 5, 6, and 7 anytime you make changes to the MCP server or proxy.

### Testing

1. Run `pytest tests/unit` to run unit tests for the server.
