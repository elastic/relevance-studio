# Relevance Studio

## Key directories and files

### Backend (Python)

- `src/server/elastic/index_templates/` - **Elasticsearch index templates** (data persistence).
  One JSON file per index: `benchmarks`, `conversations`, `displays`, `evaluations`,
  `judgements`, `scenarios`, `strategies`, `workspaces`. Indices are prefixed `esrs-`.
- `src/server/elastic/migrations/index_templates.json` - **Schema migrations** (see below)
- `src/server/models/` - **Pydantic models** (enforces data integrity for Elasticsearch indices).
  Mirrors the index templates 1:1, plus `asset.py` for shared/base fields.
- `src/server/api/` - **Python API** (implements core functionality; uses Pydantic models).
  Mirrors the models, plus `agent.py`, `content.py`, and `setup.py`.
- `src/server/flask.py` - **Server** (implements REST API; uses Python API)
- `src/server/fastmcp.py` - **MCP Server** (implements MCP tools; uses Python API)
- `src/server/fastmcp_proxy.py` - **MCP stdio proxy** (for local clients e.g. Claude Desktop)
- `src/server/worker.py` - **Background worker** (runs evaluations; deployed separately)
- `src/server/` also holds cross-cutting concerns: `client.py` (Elasticsearch client),
  `auth.py`, `mcp_auth.py`, `mcp_auth_middleware.py`, `tls.py`, `utils.py`
- `src/server/VERSION` - **Version source of truth** (plain text, e.g. `1.2.4`)

### Frontend

- `src/ui/` - **UI** (React app; built with webpack)
- `src/ui/js/Pages/` - one directory per route
- `src/ui/js/__tests__/` - Jest tests for the UI

### Tests

- `tests/unit/` - Python unit tests (pytest, no external services needed)
- `tests/integration/` - Python integration tests (pytest; **require Docker**)
- `tests/conftest.py`, `tests/utils.py` - shared fixtures and helpers
- `tests/docker-compose.yml` - services spun up for integration tests

### Docs and deployment

- `docs/` - **Docs** (docsify, hosted by GitHub Pages; no build step)
- `docs/docs/v{MAJOR}.{MINOR}/` - versioned docs (`v1.0`, `v1.1`, `v1.2`), each with
  `guide/`, `reference/`, `development/`, and `release-notes.md`.
  Note: versioned by **minor**, not patch. There is no `v1.2.4/`.
- `docker-compose.yml` - four services: `esrs-server`, `esrs-worker`,
  `esrs-server-mcp`, `esrs-proxy-mcp`
- `Dockerfile-server`, `Dockerfile-worker`, `Dockerfile-server-mcp` - note the naming;
  there is no plain `Dockerfile`
- `scripts/` - `test.sh`, `release.sh`, `quickstart.sh`, `integrate_claude_desktop.py`

## General instructions

### Changing data structures or interfaces

The chain `index template -> Pydantic model -> Python API -> REST/MCP -> UI` is tightly
coupled, and the files are named consistently across layers. Whenever you change index
templates, Pydantic models, Python APIs, REST APIs, or MCP tools, change the downstream
usages too:

- Pydantic model and Python API for the same entity (names mirror each other)
- REST API: `src/server/flask.py`
- MCP tools: `src/server/fastmcp.py`
- UI: `src/ui/`
- Docs for the affected version: `docs/docs/v{MAJOR}.{MINOR}/`
- Sample data loader: `load_sample_data.py`
- Tests: `tests/unit/` (notably `test_models_*.py`, `test_api_*.py`) and `src/ui/js/__tests__/`
- Migration entry (see below), if the change alters an existing index

### Changing index mappings (migrations)

`src/server/elastic/migrations/index_templates.json` is a single declarative manifest, not a
directory of scripts. It has a top-level `schema_version` and a `versions` array; each entry
has a release `version` (e.g. `"1.2.0"`) and a list of `steps`. Each step specifies:

- `template` - the index template name (e.g. `esrs-workspaces`)
- `action` - `create_template` or `update_template`
- `requires_reindex` - boolean
- `description` - human-readable summary
- `mapping_additions` - the new mapping fields, for `update_template`

When you change an index template, add a step under the appropriate release version. Keep the
step's `mapping_additions` consistent with the actual template JSON.

### Changing project structure or architecture

Reflect the change in downstream consumers:

- `AGENTS.md`
- `README.md`
- `docker-compose.yml` and `tests/docker-compose.yml`
- `Dockerfile-server`, `Dockerfile-worker`, `Dockerfile-server-mcp`
- `entrypoint.sh`
- `jest.config.js`, `webpack.config.js`, `.babelrc`
- `pytest.ini`
- If you add/rename an env var, update `.env-reference` (covered by
  `tests/unit/test_env_reference.py`)

### Adding a dependency

Python dependencies live in `requirements.txt`, `requirements-mcp.txt` (MCP server), and
`requirements-dev.txt` (dev/test only). JS dependencies live in `package.json`.

- Review licenses: `python licenses.py summarize --transitive`
  (scans `requirements.txt`, `requirements-mcp.txt`, and `package.json`; add `--dev` to
  include `requirements-dev.txt` and JS devDependencies)
- Dependencies must carry an OSS or Elastic (ELv2) license. `summarize` reports what it finds
  but does not enforce a policy - surface anything ambiguous or copyleft for human review
  rather than deciding unilaterally.
- If licenses are acceptable, regenerate the notice:
  `python licenses.py generate-notice --transitive`
  (writes `NOTICE.txt` by default)

### Running tests

Use the repo's test runner rather than invoking pytest/jest directly:

- `./scripts/test.sh` - everything
- `./scripts/test.sh --lang py --type unit` - `pytest tests/unit`
- `./scripts/test.sh --lang py --type integration` - `pytest tests/integration`;
  requires a running Docker daemon and will fail fast if it is unreachable
- `./scripts/test.sh --lang js --type unit` - `npm run test:ui` (Jest)

There is **no JS integration suite**; `--lang js --type integration` exits with an error.

Frontend commands: `npm run build` (production webpack), `npm run dev` (webpack-dev-server),
`npm run test:ui` (Jest).

### Releasing a new minor version

Bumping to a new minor version is more than a version string:

1. Update `src/server/VERSION`
2. Create `docs/docs/v{MAJOR}.{MINOR}/` (copy forward from the previous version)
3. Add the version to the hardcoded `versions` array in `docs/index.html` and update the
   `latest` constant near it - docsify will not discover the new folder on its own
4. Add a `versions` entry in `src/server/elastic/migrations/index_templates.json` if index
   mappings changed
5. Write `docs/docs/v{MAJOR}.{MINOR}/release-notes.md`

### Git

- Don't commit or push changes unless instructed to.

### Writing style

- Use active voice instead of passive voice, for clarity.
- Use succinct sentences, avoiding hyphens or semicolons to join them.
- Be direct, avoid juxtopositions (e.g. instead of "That's not X, it's Y" just say "That's Y").