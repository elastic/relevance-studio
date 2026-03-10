# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
MCP middleware: enforce auth per request/tool except /healthz and healthz tool.
Parse Authorization header (Basic, ApiKey), validate via auth module,
create per-request ES client, and store user/es_client in context state.
"""

# Standard packages
from typing import Any

# Third-party packages
import mcp.types
from mcp import McpError
from mcp.types import ErrorData
from typing_extensions import override

# App packages
from . import mcp_auth
from .mcp_auth import HEALTHZ_TOOL_NAME

# FastMCP
from fastmcp.server.dependencies import get_http_request
from fastmcp.server.middleware.middleware import CallNext, Middleware, MiddlewareContext


class MCPAuthMiddleware(Middleware):
    """
    Enforce authentication for MCP requests except healthz tool.
    When AUTH_ENABLED=false, uses default user and singleton ES client.
    """

    @override
    async def on_request(
        self,
        context: MiddlewareContext[mcp.types.Request[Any, Any]],
        call_next: CallNext[mcp.types.Request[Any, Any], Any],
    ) -> Any:
        ctx = context.fastmcp_context
        if ctx is None:
            return await call_next(context)

        # Exempt /healthz HTTP route
        request = get_http_request()
        if request and request.url.path.rstrip("/").endswith("/healthz"):
            user, es_client = mcp_auth.get_default_user_and_client()
            ctx.set_state("mcp_user", user)
            ctx.set_state("mcp_es_client", es_client)
            return await call_next(context)

        # Exempt healthz tool
        if context.method == "tools/call":
            msg = context.message
            if hasattr(msg, "name") and msg.name == HEALTHZ_TOOL_NAME:
                user, es_client = mcp_auth.get_default_user_and_client()
                ctx.set_state("mcp_user", user)
                ctx.set_state("mcp_es_client", es_client)
                return await call_next(context)

        # AUTH_ENABLED=false: use default
        if not mcp_auth.AUTH_ENABLED:
            user, es_client = mcp_auth.get_default_user_and_client()
            ctx.set_state("mcp_user", user)
            ctx.set_state("mcp_es_client", es_client)
            return await call_next(context)

        # Require auth: parse Authorization header
        request = get_http_request()
        if request is None:
            raise McpError(
                ErrorData(
                    code=-32001,
                    message="Unauthorized: No HTTP request context. "
                    "Send Authorization header (Basic or ApiKey).",
                )
            )
        auth_header = request.headers.get("Authorization")
        credentials = mcp_auth.parse_authorization_header(auth_header)
        if not credentials:
            raise McpError(
                ErrorData(
                    code=-32001,
                    message="Unauthorized: Missing or invalid Authorization header. "
                    "Use Basic (username:password) or ApiKey/Bearer.",
                )
            )

        try:
            user, es_client = mcp_auth.validate_and_get_es_client(credentials)
        except Exception as e:
            from elasticsearch.exceptions import AuthenticationException

            if isinstance(e, AuthenticationException):
                raise McpError(
                    ErrorData(code=-32001, message=f"Unauthorized: {e!s}")
                ) from e
            raise McpError(
                ErrorData(code=-32001, message=f"Unauthorized: {e!s}")
            ) from e

        ctx.set_state("mcp_user", user)
        ctx.set_state("mcp_es_client", es_client)
        return await call_next(context)
