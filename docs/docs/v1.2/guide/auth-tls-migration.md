# Migration guide: AUTH_ENABLED=false / TLS_ENABLED=false

This guide helps you migrate from auth-disabled or TLS-disabled configurations to the recommended secure setup.

## Migrating from AUTH_ENABLED=false

If you previously ran with `AUTH_ENABLED=false` (service-account mode), follow these steps to enable authentication:

1. **Ensure AUTH_JWT_SECRET is set** in `.env`:

   ```
   AUTH_ENABLED=true
   AUTH_JWT_SECRET=<generate with: openssl rand -hex 32>
   AUTH_SESSION_EXPIRY=24h
   ```

2. **Create Elasticsearch users or API keys** for each person or system that will access Relevance Studio. Assign the [studio deployment role](docs/{{VERSION}}/reference/security.md#studio-deployment-role-configuration) (and content role if applicable).

3. **Update MCP clients** to send credentials. See [MCP client auth configuration](docs/{{VERSION}}/guide/mcp-client-auth.md).

4. **Restart services**. Users will need to log in via the UI or `POST /api/auth/login`.

5. **Remove or rotate** the old service-account credentials from `.env` if they are no longer needed.

## Migrating from TLS_ENABLED=false

If you previously ran over HTTP, follow these steps to enable TLS:

1. **Obtain or generate certificates**:
   - For local dev: [Self-signed cert steps](docs/{{VERSION}}/guide/getting-started-tls.md#self-signed-certificates-for-local-development)
   - For production: Use a trusted CA or your organization's PKI

2. **Add to `.env`**:

   ```
   TLS_ENABLED=true
   TLS_CERT_FILE=/path/to/cert.pem
   TLS_KEY_FILE=/path/to/key.pem
   ```

3. **Update URLs** in MCP client configs from `http://` to `https://`.

4. **Restart services**. Access the app at `https://` instead of `http://`.

## Apply the v1.2.0 index template migration

After upgrading to v1.2, apply the index template migration to add `@meta.created_via` and `@meta.updated_via` fields to existing indices:

1. Open Elasticsearch Relevance Studio and run setup/upgrade from the UI, or
2. Call the upgrade API directly:

   **`curl -X POST https://localhost:4096/api/upgrade`**

   *(use `http://` if `TLS_ENABLED=false`)*

Check status at **`GET https://localhost:4096/api/setup`** — verify `upgrade.upgrade_needed: false`.

## Running behind a reverse proxy

If you run Relevance Studio behind a reverse proxy that terminates TLS and handles auth:

- Set `TLS_ENABLED=false` (proxy handles TLS)
- Set `AUTH_ENABLED=false` if the proxy enforces auth and forwards a trusted identity (or use a custom integration)

Ensure the proxy forwards the correct headers and that Relevance Studio is not exposed directly to untrusted networks.
