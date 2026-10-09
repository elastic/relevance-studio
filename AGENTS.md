# Relevance Studio — agent instructions

This file is the entry point for any coding agent (Claude Code, Codex, Cursor, etc.) working
in this repository. `CLAUDE.md` is a symlink to this file.

## What this project is

Elasticsearch Relevance Studio manages the full lifecycle of search relevance engineering:
defining scenarios, curating judgements, building strategies, and benchmarking their
performance. It has four runtime components plus a docs site:

- **Server** — Flask REST API and built-in AI agent (`src/server/flask.py`,
  `src/server/api/agent.py`).
- **MCP Server** — exposes the same operations as MCP tools for external agents
  (`src/server/fastmcp.py`).
- **Worker** — runs benchmark evaluations asynchronously (`src/server/worker.py`).
- **UI** — React app, built with webpack (`src/ui/`).
- **Docs site** — Docsify-based, versioned docs (`docs/`).

## Repo map

- `src/server/api/` — REST + MCP business logic, one module per resource (workspaces,
  displays, scenarios, judgements, strategies, benchmarks, evaluations, content, setup,
  conversations, agent).
- `src/server/models/` — Pydantic create/update schemas. `extra: forbid` — server-computed
  and immutable fields are rejected as input; check here before changing any asset shape.
- `src/server/elastic/index_templates/` — Elasticsearch index templates per asset type.
- `src/ui/` — React UI.
- `docs/docs/v1.2/` — current docs version (see `docs/index.html`'s `const latest` for which
  version is current; edit the version that matches your change).
- `scripts/` — `release.sh` (versioning), `test.sh` (test runner),
  `integrate_claude_desktop.py` (Claude Desktop MCP proxy installer).
- `tests/unit/`, `tests/integration/` — pytest suites.
- `.claude-plugin/`, `src/skills/` — the `relevance-studio` Claude plugin. **Read
  `src/skills/AGENTS.md` before touching anything here.**

## Development and testing

See `docs/docs/v1.2/development/setup-for-contributors.md` for full setup. Summary:

- Copy `.env-reference` to `.env` and point it at an Elastic deployment.
- Server: `python -m src.server.flask` (after `pip install -r requirements-dev.txt` in a
  venv).
- UI: `nvm install && nvm use`, `npm install --legacy-peer-deps`, `npm run dev`.
- Worker: `python -m src.server.worker`.
- MCP Server (optional, for plugin/agent development): `python -m src.server.fastmcp`.
- Claude Desktop MCP proxy (optional): `python scripts/integrate_claude_desktop.py`, then
  fully restart Claude Desktop.

Tests:

- `./scripts/test.sh --lang py --type unit` → `pytest tests/unit`
- `./scripts/test.sh --lang py --type integration` → `pytest tests/integration` (requires
  Docker; spins up its own Elasticsearch + Server via `tests/docker-compose.yml`)
- `./scripts/test.sh --lang js --type unit` → `npm run test:ui` (Jest)
- `./scripts/test.sh` with no flags runs everything.

## Configuration

See `.env-reference` for every supported variable. Two categories matter most:

- `ELASTICSEARCH_*` — the **studio** deployment (where Relevance Studio's own indices live).
- `CONTENT_*` — an optional **separate** content deployment (where your searchable
  documents live); falls back to `ELASTICSEARCH_*` if unset.

`AUTH_ENABLED` and `TLS_ENABLED` both default to `true`. These, and all other server-side
settings, are configured via `.env` on the server/worker/MCP processes — **never** put them
in the plugin manifest (`.claude-plugin/marketplace.json`). The plugin only carries the MCP
URL and an API key as `userConfig`.

## Cross-cutting change rules

- **Changing an MCP tool, REST API, or model can break the plugin's skills.** After such a
  change, update the affected files under `src/skills/` (especially
  `src/skills/studio-fundamentals/references/mcp-tools.md`, `data-model.md`, and
  `gotchas.md`), then run `pytest tests/unit/test_plugin.py`.
- **Keep the built-in agent's `SYSTEM_PROMPT`** (`src/server/api/agent.py`) **and
  `studio-fundamentals`** roughly consistent when either changes — they describe the same
  domain to two different audiences (the built-in agent has UI context; the plugin does not).
- Docs are versioned under `docs/docs/v<major>.<minor>/`. Edit the version that matches your
  change; check `docs/index.html` for which version is `latest`.

## Release

Use `scripts/release.sh`. It bumps `package.json`, `src/server/VERSION`, and
`.claude-plugin/marketplace.json` together — never hand-edit versions in any of these three
files.

## Plugin and skills

Before creating, editing, renaming, removing, or reviewing anything under `src/skills/` or
`.claude-plugin/`, read `src/skills/AGENTS.md` and follow it.

## Windows note

`CLAUDE.md` is committed as a symlink (git mode `120000`). Windows contributors need
`git config core.symlinks true` (and Developer Mode or admin rights) for it to check out as
a real symlink rather than a text file containing the literal path.
