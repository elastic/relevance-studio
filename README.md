# Elasticsearch Relevance Engineering Lab

**Elasticsearch Relevance Engineering Lab** (`esrel`) is a framework and test harness for search relevance engineering.

> ⚠️ This application is in early development. Expect things to break or change often until it matures.

## Development

These instructions were tested on MacOS.

**Step 1. Prepare your environment**

Install dependencies:

1. Install [nvm](https://github.com/nvm-sh/nvm?tab=readme-ov-file#installing-and-updating)
2. Install [yarn](https://classic.yarnpkg.com/en/docs/install) (tested on version 1.22.22)
3. Install [miniconda](https://www.anaconda.com/docs/getting-started/miniconda/install) (tested on version 25.3.1)

Clone this repo:

1. Run `git clone https://github.com/elastic/esrel.git`
2. Run `cd esrel` to enter the root-level directory of this project
3. Copy `.env-reference` to `.env`
4. Configure `.env` to use the endpoints and credentials of your Elastic deployment

**Step 2. Run the server in develoment mode**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `conda create -n esrel python=3.10` to create a virtual environment
2. Run `conda active esrel` to activate the virtual environment
3. Run `pip install -r requirements.txt` to install the dependencies
4. Run `python src/server/server.py` to run the server in development mode

Repeat steps 1, 2, and 4 anytime you need to start the server in a new terminal.

**Step 3. Setup the index templates**

With the server running from Step 2, run:

`curl -XPOST http://localhost:4096/setup`

It's important to setup the index templates before using the application so that
it properly indexes the data.

**Step 4. Run the frontend in development mode**

In a terminal, navigate to the root-level directory of this project and run:

1. Run `nvm install && nvm use` to use the node version specified in .nvmrc
2. Run `yarn install` in the root project directory (`eui-quickstart`) to install dependencies listed in `package.json`
3. Run `yarn run dev` to start the app using the script defined in `package.json`
4. Open [http://localhost:8080/](http://localhost:8080/) in your browser to open the app in development mode

Repeat steps 1, 3, and 4 anytime you need to start the frontend in a new terminal.