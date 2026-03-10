# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Integration tests for MCP server authentication.

When the MCP server is available (via docker-compose esrs-mcp service):
  - healthz_mcp tool and GET /healthz should work without auth
  - Other tools require Authorization header when AUTH_ENABLED=true
  - When AUTH_ENABLED=false, all tools work without auth (service account)
"""

import pytest
import requests

pytestmark = pytest.mark.integration_setup

MCP_BASE = "http://127.0.0.1:4200"


@pytest.fixture(scope="module")
def mcp_base(services):
    """Return MCP URL when available (docker or manual), else skip."""
    mcp_url = services.get("mcp")
    if mcp_url:
        return mcp_url
    try:
        r = requests.get(f"{MCP_BASE}/healthz", timeout=2)
        if r.status_code == 200:
            return MCP_BASE
    except requests.exceptions.RequestException:
        pass
    pytest.skip("MCP server not available at http://127.0.0.1:4200. Start with: python -m server.fastmcp")


def test_healthz_http_no_auth_required(services, mcp_base):
    """GET /healthz is exempt from auth and returns 200."""
    r = requests.get(f"{mcp_base}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json().get("acknowledged") is True
