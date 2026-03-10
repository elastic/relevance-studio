# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Integration tests for MCP server authentication.

BLOCKER: The MCP server runs on port 4200 as a separate process. The test
docker-compose (tests/docker-compose.yml) only starts the Flask server on 4196
and does not include the MCP server. To run these tests:
  1. Start the MCP server: python -m server.fastmcp (port 4200)
  2. Set AUTH_ENABLED=true or false as needed
  3. Run: pytest tests/integration/test_mcp_auth.py -v -m integration_setup

When the MCP server is available:
  - healthz_mcp tool and GET /healthz should work without auth
  - Other tools require Authorization header when AUTH_ENABLED=true
  - When AUTH_ENABLED=false, all tools work without auth (service account)
"""

import pytest
import requests

pytestmark = pytest.mark.integration_setup

# MCP server URL - adjust if different
MCP_BASE = "http://127.0.0.1:4200"


@pytest.fixture(scope="module")
def mcp_available():
    """Skip tests if MCP server is not running on port 4200."""
    try:
        r = requests.get(f"{MCP_BASE}/healthz", timeout=2)
        if r.status_code == 200:
            return True
    except requests.exceptions.RequestException:
        pass
    pytest.skip("MCP server not available at http://127.0.0.1:4200. Start with: python -m server.fastmcp")


def test_healthz_http_no_auth_required(mcp_available):
    """GET /healthz is exempt from auth and returns 200."""
    r = requests.get(f"{MCP_BASE}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json().get("acknowledged") is True
