# Getting started: Authentication

This guide walks you through enabling and configuring authentication for Elasticsearch Relevance Studio.

## Overview

When `AUTH_ENABLED=true` (default):

- **Server**: Users log in via `POST /api/auth/login` with Elasticsearch credentials (username/password or API key). A session cookie (JWT) is issued for subsequent API requests.
- **MCP Server**: Clients send credentials via the `Authorization` header on each request.

When `AUTH_ENABLED=false`, Studio and MCP do not require per-request auth, and Studio uses no credentials for the studio deployment.

## Enable authentication

1. Set in `.env`:

   ```
   AUTH_ENABLED=true
   AUTH_JWT_SECRET=<your-secret>
   AUTH_SESSION_EXPIRY=24h
   ```

2. Generate a strong `AUTH_JWT_SECRET`:

   ```bash
   openssl rand -hex 32
   ```

3. Restart the Server and MCP Server.

## Configure MCP clients

When auth is enabled, MCP clients must send credentials. See [MCP client auth configuration](docs/{{VERSION}}/guide/mcp-client-auth.md) for details.

## Session expiry

`AUTH_SESSION_EXPIRY` controls how long a login session remains valid. Examples:

- `30m` — 30 minutes
- `24h` — 24 hours (default)
- `7d` — 7 days

## Troubleshooting

- **"No session cookie"**: Ensure you have logged in via `POST /api/auth/login` and that cookies are being sent with requests.
- **"Invalid or expired session"**: The JWT has expired. Log in again.
- **"Invalid session payload"**: Ensure `AUTH_JWT_SECRET` is set and has not changed since the session was created.
