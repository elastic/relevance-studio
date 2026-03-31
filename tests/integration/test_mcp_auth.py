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

Auth-enabled MCP tests require ESRS_TEST_MCP_AUTH_URL, ESRS_TEST_AUTH_USERNAME,
and ESRS_TEST_AUTH_PASSWORD environment variables.
"""

import os
import base64

import pytest
import requests

pytestmark = pytest.mark.integration_setup

MCP_BASE = "http://127.0.0.1:4200"

_AUTH_MCP_URL = os.getenv("ESRS_TEST_MCP_AUTH_URL")
_AUTH_USERNAME = os.getenv("ESRS_TEST_AUTH_USERNAME")
_AUTH_PASSWORD = os.getenv("ESRS_TEST_AUTH_PASSWORD")
_AUTH_TESTS_AVAILABLE = all([_AUTH_MCP_URL, _AUTH_USERNAME, _AUTH_PASSWORD])
requires_mcp_auth_env = pytest.mark.skipif(
    not _AUTH_TESTS_AVAILABLE,
    reason="MCP auth tests require ESRS_TEST_MCP_AUTH_URL, ESRS_TEST_AUTH_USERNAME, ESRS_TEST_AUTH_PASSWORD",
)


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


@requires_mcp_auth_env
def test_mcp_healthz_no_auth_when_auth_enabled():
    """GET /healthz works without auth even when AUTH_ENABLED=true."""
    r = requests.get(f"{_AUTH_MCP_URL}/healthz", timeout=5)
    assert r.status_code == 200
    assert r.json().get("acknowledged") is True


@requires_mcp_auth_env
def test_mcp_tool_call_without_auth_returns_error():
    """MCP tool call without Authorization header returns error when AUTH_ENABLED=true."""
    r = requests.post(
        f"{_AUTH_MCP_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 1},
        timeout=5,
    )
    assert r.status_code in (401, 403) or (
        r.status_code == 200 and "error" in r.json()
    )


@requires_mcp_auth_env
def test_mcp_tool_list_with_basic_auth_succeeds():
    """MCP tools/list succeeds when valid Basic auth header is provided."""
    basic = base64.b64encode(f"{_AUTH_USERNAME}:{_AUTH_PASSWORD}".encode("utf-8")).decode("utf-8")
    r = requests.post(
        f"{_AUTH_MCP_URL}/mcp",
        json={"jsonrpc": "2.0", "method": "tools/list", "id": 2},
        headers={"Authorization": f"Basic {basic}"},
        timeout=10,
    )
    assert r.status_code == 200
    body = r.json()
    assert "error" not in body
    assert "result" in body
    assert isinstance(body["result"].get("tools", []), list)
