---
name: "connect-and-verify"
description: "Use when Relevance Studio MCP tools are missing, failing, or returning authentication, TLS, or connection errors, when setting up the relevance-studio plugin for the first time, or when the user asks whether their Relevance Studio connection works. Diagnoses and verifies the connection in both Claude Code and Claude Desktop."
---

## When this applies

Use this skill first whenever Relevance Studio tools don't appear, a tool call fails with a
connection or auth error, or the user wants to confirm a fresh install works.

## Prerequisites

If you haven't loaded the `studio-fundamentals` skill in this conversation, load it first.

## Procedure

1. **Check tool availability.** If no Relevance Studio tools are visible at all, the plugin
   isn't installed or configured for this client. Walk the user through the install steps in
   the README's "Integrations" section for their client (Claude Code or Claude Desktop).

2. **Call `healthz_mcp`.** This requires no auth and confirms the MCP server process is
   reachable at all. If it fails, the server likely isn't running, or the URL/port is wrong
   (default MCP port is `4200`, path `/mcp`).

3. **Call `setup_check`.** Interpret the response:
   - `version` — the server's product version. Compare against this plugin's minimum
     supported server version, **`1.2.4`** (see `gotchas.md` in `studio-fundamentals`). If
     older, tell the user to upgrade the server before relying on plugin guidance — earlier
     versions ship a broken `workspaces_update` schema.
   - `setup` — whether required index templates/indices exist. If `setup.failures` is
     non-zero and none are `upgrade_only_failures`, the deployment needs initial setup.
   - `upgrade` — whether a migration is pending. If so, hand off to `upgrade-and-maintenance`.
   - `deployment.mode` (`standard` / `serverless` / `cloud`) and `deployment.license` — useful
     context for troubleshooting, not usually actionable on their own.

4. **On a fresh deployment** (setup failures present, no upgrade pending), explain what
   `setup_run` will do and offer to run it — **only after explicit confirmation**, since it
   creates/modifies index templates and indices.

5. **If anything fails, troubleshoot using this matrix:**

   | Symptom | Likely cause and fix |
   |---|---|
   | 401 / auth error | `AUTH_ENABLED=true` on the server but the plugin's `auth_header` config is blank or wrong. It must be the **full** header value: `ApiKey <base64 id:api_key>`, `Basic <base64 username:password>`, or `Bearer <base64 id:api_key>`. Check the scheme name and base64 encoding match what the server expects. |
   | TLS / certificate errors | The server has a self-signed certificate (`TLS_ENABLED=true` by default). Claude Desktop's integration script needs `TLS_CERT_FILE` / `TLS_KEY_FILE` set in `.env`. Whether Claude Code's HTTP MCP client honors `NODE_EXTRA_CA_CERTS` for a self-signed CA hasn't been verified for this plugin — if certificate errors persist, the simplest workaround for local dev is to set `TLS_ENABLED=false` on the server (HTTP only) rather than fighting a trust chain. |
   | Connection refused | MCP Server isn't running, wrong port (default `4200`), missing `/mcp` path on the URL, or an `http`/`https` mismatch with the server's `TLS_ENABLED` setting. |
   | Desktop: tools vanish after editing `.env` | Re-run `python scripts/integrate_claude_desktop.py` and fully restart Desktop (quit, don't just close the window). |
   | `AUTH_ENABLED=false` but a request was rejected anyway | This shouldn't happen — when auth is disabled the server never inspects the `Authorization` header at all, regardless of whether `auth_header` is blank or set. If a request is being rejected, the server more likely has `AUTH_ENABLED=true`; re-check its `.env`. |

6. **Warn about credential storage.** The Claude Desktop stdio proxy integration script
   stores Elasticsearch credentials in plaintext in `claude_desktop_config.json`.
   Recommend a scoped, revocable API key rather than a long-lived username/password.

## Tools

`healthz_mcp`, `setup_check`, `setup_run`.

## Guardrails

- Never run `setup_run` without explicit confirmation — it modifies index templates and
  indices.
- Don't guess at TLS/auth configuration; read it from `setup_check` and the troubleshooting
  matrix above rather than assuming a cause.

## Examples

**Correct (confirms before destructive-adjacent setup):**
"`setup_check` shows missing index templates. Want me to run `setup_run` to create them?"
— waits for yes before calling `setup_run`.

**Incorrect (guesses at the fix):**
A 401 comes back, and Claude tells the user to disable `AUTH_ENABLED` instead of checking
whether `auth_header` holds a correctly base64-encoded, correctly-scoped value first.

## Next steps

Hand off to `upgrade-and-maintenance` if `setup_check` shows a pending upgrade. Once healthy,
hand off to `lifecycle-orchestrator` for open-ended requests, or any skill relevant to what
the user asked for.
