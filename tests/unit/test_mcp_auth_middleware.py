"""Unit tests for MCPAuthMiddleware request authorization behavior."""

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from mcp import McpError

from server.mcp_auth_middleware import MCPAuthMiddleware


class _FastContext:
    def __init__(self):
        self._state = {}

    def set_state(self, key, value):
        self._state[key] = value

    def get_state(self, key):
        return self._state.get(key)


class _MiddlewareContext:
    def __init__(self, fastmcp_context=None, method="tools/list", message=None):
        self.fastmcp_context = fastmcp_context
        self.method = method
        self.message = message


def _run(coro):
    return asyncio.run(coro)


def test_no_fastmcp_context_passes_through():
    middleware = MCPAuthMiddleware()
    ctx = _MiddlewareContext(fastmcp_context=None)
    call_next = MagicMock()
    call_next.return_value = asyncio.sleep(0, result="ok")

    result = _run(middleware.on_request(ctx, call_next))

    assert result == "ok"
    call_next.assert_called_once_with(ctx)


def test_healthz_http_route_uses_default_auth(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")
    request = SimpleNamespace(url=SimpleNamespace(path="/healthz"))
    default_user = {"username": "system", "roles": ["superuser"]}
    default_client = object()

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.get_default_user_and_client",
        lambda: (default_user, default_client),
    )
    call_next = MagicMock()
    call_next.return_value = asyncio.sleep(0, result="ok")

    result = _run(middleware.on_request(ctx, call_next))

    assert result == "ok"
    assert fast_ctx.get_state("mcp_user") == default_user
    assert fast_ctx.get_state("mcp_es_client") is default_client


def test_healthz_tool_call_uses_default_auth(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    msg = SimpleNamespace(name="healthz_mcp")
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/call", message=msg)
    request = SimpleNamespace(url=SimpleNamespace(path="/mcp"))
    default_user = {"username": "system", "roles": ["superuser"]}
    default_client = object()

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.get_default_user_and_client",
        lambda: (default_user, default_client),
    )
    call_next = MagicMock()
    call_next.return_value = asyncio.sleep(0, result="ok")

    result = _run(middleware.on_request(ctx, call_next))

    assert result == "ok"
    assert fast_ctx.get_state("mcp_user") == default_user
    assert fast_ctx.get_state("mcp_es_client") is default_client


def test_auth_disabled_uses_default_auth(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")
    request = SimpleNamespace(url=SimpleNamespace(path="/mcp"))
    default_user = {"username": "system", "roles": ["superuser"]}
    default_client = object()

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr("server.mcp_auth_middleware.mcp_auth.AUTH_ENABLED", False)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.get_default_user_and_client",
        lambda: (default_user, default_client),
    )
    call_next = MagicMock()
    call_next.return_value = asyncio.sleep(0, result="ok")

    result = _run(middleware.on_request(ctx, call_next))

    assert result == "ok"
    assert fast_ctx.get_state("mcp_user") == default_user
    assert fast_ctx.get_state("mcp_es_client") is default_client


def test_auth_enabled_without_http_request_raises(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: None)
    monkeypatch.setattr("server.mcp_auth_middleware.mcp_auth.AUTH_ENABLED", True)

    with pytest.raises(McpError, match="No HTTP request context"):
        _run(middleware.on_request(ctx, lambda _ctx: asyncio.sleep(0, result="ok")))


def test_auth_enabled_invalid_header_raises(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")
    request = SimpleNamespace(url=SimpleNamespace(path="/mcp"), headers={})

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr("server.mcp_auth_middleware.mcp_auth.AUTH_ENABLED", True)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.parse_authorization_header",
        lambda _: None,
    )

    with pytest.raises(McpError, match="Missing or invalid Authorization header"):
        _run(middleware.on_request(ctx, lambda _ctx: asyncio.sleep(0, result="ok")))


def test_auth_enabled_valid_header_sets_state(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")
    request = SimpleNamespace(
        url=SimpleNamespace(path="/mcp"),
        headers={"Authorization": "Basic YWxpY2U6c2VjcmV0"},
    )
    user = {"username": "alice", "roles": ["user"]}
    es_client = object()

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr("server.mcp_auth_middleware.mcp_auth.AUTH_ENABLED", True)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.parse_authorization_header",
        lambda _: {"username": "alice", "password": "secret"},
    )
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.validate_and_get_es_client",
        lambda _credentials: (user, es_client),
    )
    call_next = MagicMock()
    call_next.return_value = asyncio.sleep(0, result="ok")

    result = _run(middleware.on_request(ctx, call_next))

    assert result == "ok"
    assert fast_ctx.get_state("mcp_user") == user
    assert fast_ctx.get_state("mcp_es_client") is es_client
    call_next.assert_called_once_with(ctx)


def test_auth_enabled_validation_error_raises(monkeypatch):
    middleware = MCPAuthMiddleware()
    fast_ctx = _FastContext()
    ctx = _MiddlewareContext(fastmcp_context=fast_ctx, method="tools/list")
    request = SimpleNamespace(
        url=SimpleNamespace(path="/mcp"),
        headers={"Authorization": "ApiKey abc"},
    )

    monkeypatch.setattr("server.mcp_auth_middleware.get_http_request", lambda: request)
    monkeypatch.setattr("server.mcp_auth_middleware.mcp_auth.AUTH_ENABLED", True)
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.parse_authorization_header",
        lambda _: {"api_key": "abc"},
    )
    monkeypatch.setattr(
        "server.mcp_auth_middleware.mcp_auth.validate_and_get_es_client",
        lambda _credentials: (_ for _ in ()).throw(ValueError("invalid credentials")),
    )

    with pytest.raises(McpError, match="Unauthorized: invalid credentials"):
        _run(middleware.on_request(ctx, lambda _ctx: asyncio.sleep(0, result="ok")))
