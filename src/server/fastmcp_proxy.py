# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
MCP proxy that forwards requests to the Relevance Studio MCP server.

Transport modes for the proxy itself (FASTMCP_SERVER_TRANSPORT):
  - "stdio" (default): Claude Desktop launches the proxy and communicates via
    stdin/stdout. No TLS needed on the proxy side.
  - "http": The proxy serves over HTTP(S) on FASTMCP_PROXY_PORT (default 4201).
    TLS config (TLS_ENABLED, TLS_CERT_FILE, TLS_KEY_FILE) applies to the proxy's
    own listener. Use this when a client connects to the proxy via URL.

Upstream connection (proxy → MCP server):
  - URL: MCP_SERVER_URL if set, otherwise derived from TLS_ENABLED + FASTMCP_PORT.
  - TLS: When TLS_ENABLED=true the proxy connects over HTTPS and uses TLS_CERT_FILE
    as the CA bundle for SSL verification (required for self-signed certificates).

Auth forwarding:
  - HTTP mode: FastMCP automatically forwards the Authorization header from every
    incoming request to the upstream server.
  - stdio mode: Set ELASTICSEARCH_API_KEY or ELASTICSEARCH_USERNAME +
    ELASTICSEARCH_PASSWORD in the proxy's environment; they are injected as a
    static auth header on every upstream request.

MCP clients should send one of:
  - Basic:  Authorization: Basic <base64(username:password)>
  - ApiKey: Authorization: ApiKey <base64(id:api_key)>
  - Bearer: Authorization: Bearer <base64(id:api_key)>

See docs for MCP client credential configuration.
"""

# Standard packages
import base64
import os
import sys

# Third-party packages
import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp.server.proxy import ProxyClient

# App packages
from .tls import get_tls_config, log_tls_status

load_dotenv()

####  Helpers  #################################################################

def _upstream_url() -> str:
    """Derive the upstream MCP server URL from environment."""
    explicit = os.environ.get("MCP_SERVER_URL", "").strip()
    if explicit:
        return explicit.rstrip("/") + "/"
    tls_raw = os.environ.get("TLS_ENABLED", "true").strip().lower()
    tls_on = tls_raw not in ("false", "0", "no", "off")
    scheme = "https" if tls_on else "http"
    port = int(os.environ.get("FASTMCP_PORT") or "4200")
    return f"{scheme}://127.0.0.1:{port}/mcp/"


def _static_auth_headers() -> dict[str, str]:
    """
    Build an Authorization header from env vars for stdio / static-auth mode.
    Returns an empty dict when no credentials are configured (rely on per-request
    forwarding in HTTP proxy mode instead).
    """
    api_key = os.environ.get("ELASTICSEARCH_API_KEY", "").strip()
    if api_key:
        return {"Authorization": f"ApiKey {api_key}"}
    username = os.environ.get("ELASTICSEARCH_USERNAME", "").strip()
    password = os.environ.get("ELASTICSEARCH_PASSWORD", "")
    if username:
        encoded = base64.b64encode(f"{username}:{password}".encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {}


def _ssl_httpx_factory(verify):
    """
    Return an McpHttpClientFactory that applies custom SSL verification.

    ``verify`` accepts the same values as httpx: True (default CA), False
    (skip verification), or a path to a CA bundle / certificate file.
    """
    def factory(
        headers: dict[str, str] | None = None,
        timeout: httpx.Timeout | None = None,
        auth: httpx.Auth | None = None,
        **kwargs,
    ) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers=headers or {},
            timeout=timeout or httpx.Timeout(30.0, read=300.0),
            auth=auth,
            follow_redirects=kwargs.get("follow_redirects", True),
            verify=verify,
        )
    return factory


####  Build proxy  #############################################################

_tls = get_tls_config()

# Fail fast on invalid TLS config at import time. This must run at module scope
# (not just in __main__) because the stdio entry point imports ``mcp`` from this
# module without ever entering this file's __main__ block. Without this check,
# a misconfigured TLS_CERT_FILE/TLS_KEY_FILE would silently fall back to the
# system CA bundle and surface as opaque certificate-verify errors at the
# first tool call instead of the clear, actionable message produced by
# get_tls_config().
if _tls["error"]:
    print(_tls["error"], file=sys.stderr)
    sys.exit(1)

_upstream = _upstream_url()
_headers = _static_auth_headers()

if _tls["enabled"]:
    # Use TLS_CERT_FILE as the CA bundle so self-signed certs are accepted.
    _verify = _tls["ssl_context"][0]
    _transport = StreamableHttpTransport(
        _upstream,
        headers=_headers,
        httpx_client_factory=_ssl_httpx_factory(_verify),
    )
else:
    _transport = StreamableHttpTransport(_upstream, headers=_headers)

mcp = FastMCP.as_proxy(ProxyClient(_transport), name="relevance-studio")


####  Main  ####################################################################

if __name__ == "__main__":
    server_transport = os.environ.get("FASTMCP_SERVER_TRANSPORT", "stdio").strip().lower()

    if server_transport == "http":
        # FASTMCP_PROXY_PORT is the port the proxy itself listens on.
        # Keep it separate from FASTMCP_PORT (the upstream MCP server port).
        host = os.environ.get("FASTMCP_HOST") or "0.0.0.0"
        port = int(os.environ.get("FASTMCP_PROXY_PORT") or "4201")
        log_tls_status("esrs-proxy-mcp", host, port, _tls)
        transport_kwargs: dict = {"port": port, "log_level": "debug"}
        if _tls["uvicorn_config"]:
            transport_kwargs["uvicorn_config"] = _tls["uvicorn_config"]
        mcp.run(transport="http", **transport_kwargs)
    else:
        mcp.run()
