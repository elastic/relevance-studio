# Getting started: TLS

This guide walks you through enabling TLS for the Server and MCP Server, including self-signed certificates for local development.

## Overview

TLS is enabled by default. When `TLS_ENABLED=true`, you must provide valid PEM certificate and key files. Set `TLS_ENABLED=false` to run over HTTP (e.g. behind a reverse proxy that terminates TLS).

## Self-signed certificates for local development

### Option 1: Using OpenSSL

1. Create a certs directory:

   ```bash
   mkdir -p .certs
   ```

2. Generate a self-signed certificate:

   ```bash
   openssl req -x509 -newkey rsa:4096 -sha256 -days 365 -nodes \
     -keyout .certs/key.pem -out .certs/cert.pem \
     -subj "/CN=localhost" \
     -addext "subjectAltName=IP:127.0.0.1,DNS:localhost"
   ```

3. Add to `.env`:

   ```
   TLS_ENABLED=true
   TLS_CERT_FILE=.certs/cert.pem
   TLS_KEY_FILE=.certs/key.pem
   ```

4. For Docker, mount the local `.certs` directory into the container. The default `docker-compose.yml` already mounts `./.certs:/app/.certs:ro`, so the relative paths above resolve correctly under the container's working directory (`/app`).

5. Access the app at `https://localhost:4096` and accept the browser warning for the self-signed cert.

### Option 2: Using quickstart

If you use the quickstart script, it can generate and configure TLS certs for you. See the [quickstart](docs/{{VERSION}}/guide/quickstart.md) documentation.

## Production

For production, use certificates from a trusted CA (e.g. Let's Encrypt) or your organization's PKI. Alternatively, place the Server and MCP Server behind a reverse proxy that terminates TLS and set `TLS_ENABLED=false`.

## Disable TLS

To run over HTTP (e.g. behind a TLS-terminating proxy):

```
TLS_ENABLED=false
```

See [Migration guide](docs/{{VERSION}}/guide/auth-tls-migration.md) for moving from TLS-disabled to TLS-enabled.
