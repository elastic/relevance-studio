# Upgrade

This guide explains how to upgrade an existing Elasticsearch Relevance Studio installation from one release to another.

## Overview

Upgrading has two parts:

1. Update the application code to a newer release tag.
2. Apply any required index upgrades.

If your installation was created with quickstart, the easiest way to update code is to run quickstart again with the same install directory.

## Step 1. Update to a newer release tag

Run quickstart again and point it to the same directory where Elasticsearch Relevance Studio is already installed.

Update to the latest release:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --dir ./relevance-studio --version latest`**

Update to a specific release:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --dir ./relevance-studio --version v1.1.0`**

For development/testing (non-release) upgrades, target a specific git ref:

**`bash <(curl -fsSL https://ela.st/relevance-studio-quickstart) --dir ./relevance-studio --ref <branch-or-commit>`**

What this does:

- Reuses your existing repository in that directory.
- Fetches tags from GitHub.
- Checks out the requested release tag.
- Keeps your existing `.env` unless you choose to reconfigure it.

## Step 2. Restart services

If quickstart did not start services for you, restart from inside the install directory:

**`docker compose up --build -d`**

## Step 3. Apply index upgrades

After the new code is running, apply index upgrades:

- Open Elasticsearch Relevance Studio and run setup/upgrade from the UI, or
- Call the upgrade API directly:

**`curl -X POST https://localhost:4096/api/upgrade`**

*(use `http://` if `TLS_ENABLED=false`)*

### Upgrading to v2.0

v2.0 adds migration manifest version `2.0.0`, which introduces a new `reindex_and_cutover` step action. When you upgrade to v2.0 through the normal upgrade flow (`POST /api/upgrade`), this step runs automatically to create the new stores and copy your existing data into them:

- Creates the new `esrs-benchmark-configs` index and the `esrs-benchmark-runs` index.
- Creates the new `esrs-benchmark-results` and `esrs-benchmark-forensics` data streams.
- Copies data from the old `esrs-benchmarks` and `esrs-evaluations` indices into the new stores.

This migration is **additive**: the old `esrs-benchmarks` and `esrs-evaluations` indices are left in place and are **not** deleted. You can remove them manually once you have verified the upgrade.

The `esrs-benchmark-results` and `esrs-benchmark-forensics` data streams use [Data Stream Lifecycle (DLM)](https://www.elastic.co/docs/manage-data/lifecycle/data-stream) with no retention limit set by default, so data is retained indefinitely. Each stream's index template has a single place to set a retention period later if you want the streams to roll off automatically.

## Verify upgrade status

Check upgrade status at:

**`https://localhost:4096/api/setup`**

*(use `http://` if `TLS_ENABLED=false`)*

In the response:

- `upgrade.upgrade_needed: false` means all known upgrade steps are applied.
- `setup.failures: 0` indicates required templates and indices are present.

## Troubleshooting

- If quickstart cannot check out the target version, make sure the version exists as a release tag (for example `v1.1.0`).
- Upgrades that require a reindex (such as v2.0's `reindex_and_cutover`) are no longer blocked. The v2.0 reindex is additive: it copies data from the old `esrs-benchmarks`/`esrs-evaluations` indices into the new stores without deleting the originals, and runs automatically through the normal upgrade flow. If any step reports an error in the API response, follow the guidance there before rerunning upgrade.
