# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for MCP server authentication: header parsing, validation,
disabled mode, and context helpers.
"""

import base64
from unittest.mock import MagicMock

import pytest

from server import mcp_auth


class TestParseAuthorizationHeader:
    """Parse Authorization header supporting Basic and ApiKey."""

    def test_empty_returns_none(self):
        assert mcp_auth.parse_authorization_header(None) is None
        assert mcp_auth.parse_authorization_header("") is None
        assert mcp_auth.parse_authorization_header("   ") is None

    def test_basic_returns_username_password(self):
        creds = base64.b64encode(b"alice:secret123").decode("utf-8")
        out = mcp_auth.parse_authorization_header(f"Basic {creds}")
        assert out == {"username": "alice", "password": "secret123"}

    def test_basic_handles_whitespace(self):
        creds = base64.b64encode(b"bob:pass").decode("utf-8")
        out = mcp_auth.parse_authorization_header(f"  Basic  {creds}  ")
        assert out == {"username": "bob", "password": "pass"}

    def test_basic_invalid_no_colon_returns_none(self):
        creds = base64.b64encode(b"nocolon").decode("utf-8")
        assert mcp_auth.parse_authorization_header(f"Basic {creds}") is None

    def test_apikey_returns_api_key(self):
        encoded = base64.b64encode(b"id123:key456").decode("utf-8")
        out = mcp_auth.parse_authorization_header(f"ApiKey {encoded}")
        assert out == {"api_key": encoded}

    def test_bearer_returns_api_key(self):
        encoded = base64.b64encode(b"id:key").decode("utf-8")
        out = mcp_auth.parse_authorization_header(f"Bearer {encoded}")
        assert out == {"api_key": encoded}

    def test_invalid_scheme_returns_none(self):
        assert mcp_auth.parse_authorization_header("Digest xyz") is None
        assert mcp_auth.parse_authorization_header("Unknown value") is None

    def test_malformed_missing_value_returns_none(self):
        assert mcp_auth.parse_authorization_header("Basic") is None
        assert mcp_auth.parse_authorization_header("ApiKey") is None


class TestGetDefaultUserAndClient:
    """AUTH_ENABLED=false uses default user and singleton ES client."""

    def test_returns_ai_user_and_es_studio(self, monkeypatch):
        mock_es = MagicMock()
        monkeypatch.setattr("server.mcp_auth.es", lambda name: mock_es)
        user, client = mcp_auth.get_default_user_and_client()
        assert user["username"] == "ai"
        assert user["roles"] == []
        assert client is mock_es


class TestGetMcpAuthFromContext:
    """Extract user and es_client from FastMCP context state."""

    def test_none_context_returns_ai_and_none(self):
        username, es_client = mcp_auth.get_mcp_auth_from_context(None)
        assert username == "ai"
        assert es_client is None

    def test_context_with_state_returns_user_and_client(self):
        ctx = MagicMock()
        ctx.get_state.side_effect = lambda k: (
            {"username": "alice", "roles": ["user"]} if k == "mcp_user" else MagicMock()
        )
        username, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
        assert username == "alice"
        assert es_client is not None

    def test_context_missing_user_falls_back_to_ai(self):
        ctx = MagicMock()
        ctx.get_state.side_effect = lambda k: (None if k == "mcp_user" else MagicMock())
        username, _ = mcp_auth.get_mcp_auth_from_context(ctx)
        assert username == "ai"


class TestHealthzExemption:
    """healthz tool name is exempt from auth."""

    def test_healthz_tool_name_constant(self):
        assert mcp_auth.HEALTHZ_TOOL_NAME == "healthz_mcp"
