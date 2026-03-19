# Setup for contributors

These instructions will prepare your environment for developing Relevance Studio.

Tested on MacOS 15.5.

---

### Step 1. Prepare your environment

Install dependencies:

1. Install [nvm](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating) *(required by [UI](docs/reference/architecture.md#application))*
2. Install [python3](https://www.python.org/downloads/) (tested on version 3.10) *(required by [Server](docs/reference/architecture.md#application), [Worker](docs/reference/architecture.md#application), [MCP Server](docs/reference/architecture.md#application), [MCP Proxy](docs/reference/architecture.md#application))*
3. Install [docker](https://docs.docker.com/engine/install/) (tested on version 27.3.1) *(required for integration tests)*

Clone this repo:

1. Run `git clone https://github.com/elastic/relevance-studio.git`
2. Run `cd relevance-studio` to enter the root-level directory of this project
3. Copy `.env-reference` to `.env`
4. Configure `.env` to use the endpoints and credentials of your Elastic deployment

---

### Step 2. Run the Server in development mode

In a terminal, navigate to the root-level directory of this project and run:

1. Run `python3 -m venv .venv` to create a virtual environment
2. Run `source .venv/bin/activate` to activate the virtual environment
3. Run `pip install --upgrade pip` to ensure pip is up to date
4. Run `pip install -r requirements-dev.txt` to install the dependencies
5. Run `python -m src.server.flask` to run the server in development mode

Repeat steps 2 and 5 anytime you need to start the server in a new terminal.

---

### Step 3. Run the UI in development mode

In a terminal, navigate to the root-level directory of this project and run:

1. Run `nvm install && nvm use` to use the node version specified in .nvmrc
2. Run `npm install --legacy-peer-deps` in the root project directory to install dependencies listed in `package.json`
3. Run `npm run dev` to start the app using the script defined in `package.json`
4. Open [http://localhost:8080/](http://localhost:8080/) in your browser to open the app in development mode

Repeat steps 1, 3, and 4 anytime you need to start the UI in a new terminal.

---

### Step 4. Run an evaluation worker process

In a terminal, navigate to the root-level directory of this project and run:

1. Run `source .venv/bin/activate` to activate the virtual environment
2. Run `python -m src.server.worker` to run a worker process

Repeat these steps anytime you need to start a worker in another terminal.

---

### Step 5. Setup the index templates and indices

With the server and UI running from Steps 2 and 3, open [http://localhost:8080/](http://localhost:8080/) and click the button on the homepage to setup the index templates and indices.

---

### Step 6. (Optional) Run the MCP Server

In a terminal, navigate to the root-level directory of this project and run:

1. Run `source .venv/bin/activate` to activate the virtual environment
2. Run `pip install -r requirements-mcp.txt` to install the dependencies
3. Run `python -m src.server.fastmcp` to start the MCP server

Repeat steps 1 and 3 anytime you need to start the MCP Server in another terminal.

---

### Step 7. (Optional) Run the MCP Proxy for Claude Desktop

In a terminal, navigate to the root-level directory of this project and run:

1. Run `brew install uv` which is needed by Claude Desktop
2. Run `source .venv/bin/activate` to activate the virtual environment
3. Run `pip install -r requirements-mcp.txt` to install the dependencies
4. Run `fastmcp install claude-desktop src/server/fastmcp_proxy.py` to install the MCP Proxy in Claude Desktop
5. Restart Claude Desktop

Repeat steps 2, 4, and 5 anytime you change the MCP Proxy or need to run it in another terminal.

---

### Testing

Run `pytest tests/unit` to run unit tests for the server.