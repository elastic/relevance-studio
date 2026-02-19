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

**`curl -X POST http://localhost:4096/api/upgrade`**

## Verify upgrade status

Check upgrade status at:

**`http://localhost:4096/api/setup`**

In the response:

- `upgrade.upgrade_needed: false` means all known upgrade steps are applied.
- `setup.failures: 0` indicates required templates and indices are present.

## Troubleshooting

- If quickstart cannot check out the target version, make sure the version exists as a release tag (for example `v1.1.0`).
- If upgrade is blocked due to reindex requirements, follow the guidance in the API response before rerunning upgrade.
