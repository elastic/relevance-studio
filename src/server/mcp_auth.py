# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
MCP server authentication: parse Authorization header, validate credentials,
and provide per-request user and ES client for tool handlers.
"""

# Standard packages
import base64
from typing import Any, Dict, Optional, Tuple

# Third-party packages
from elasticsearch import Elasticsearch

# App packages
from . import auth
from .client import es, es_from_credentials, es_studio_endpoint

# Config: single source of truth from auth module
AUTH_ENABLED = auth.AUTH_ENABLED

# Exempt tool name (no auth required)
HEALTHZ_TOOL_NAME = "healthz_mcp"


def parse_authorization_header(auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
    """
    Parse Authorization header into credentials dict.

    Supports:
    - Basic: "Basic <base64(username:password)>"
    - ApiKey: "ApiKey <base64(id:api_key)>" or "Bearer <base64(id:api_key)>"

    Returns:
        Dict with either api_key or (username, password). None if missing/invalid.
    """
    if not auth_header or not auth_header.strip():
        return None
    parts = auth_header.strip().split(None, 1)
    if len(parts) != 2:
        return None
    scheme, value = parts[0], parts[1]
    try:
        if scheme.lower() == "basic":
            decoded = base64.b64decode(value).decode("utf-8")
            if ":" not in decoded:
                return None
            username, _, password = decoded.partition(":")
            return {"username": username, "password": password}
        if scheme.lower() in ("apikey", "bearer"):
            return {"api_key": value}
    except Exception:
        return None
    return None


def validate_and_get_es_client(credentials: Dict[str, Any]) -> Tuple[Dict[str, Any], Elasticsearch]:
    """
    Validate credentials and return user info and ES client.

    Raises:
        ValueError: Invalid credentials format.
        AuthenticationException: Auth failed (401).
    """
    user_info = auth.validate_credentials(credentials)
    endpoint = es_studio_endpoint()
    client = es_from_credentials(
        api_key=credentials.get("api_key"),
        username=credentials.get("username"),
        password=credentials.get("password"),
        cloud_id=endpoint.get("cloud_id"),
        url=endpoint.get("hosts", [None])[0] if endpoint.get("hosts") else None,
    )
    return user_info, client


def get_default_user_and_client() -> Tuple[Dict[str, Any], Elasticsearch]:
    """Return default user and singleton ES client when AUTH_ENABLED=false."""
    return {"username": "ai", "roles": []}, es("studio")


def get_mcp_auth_from_context(ctx: Optional[Any]) -> Tuple[str, Optional[Elasticsearch]]:
    """
    Get authenticated user and ES client from FastMCP context state.

    Call from tool handlers that accept Context. Returns (username, es_client).
    When es_client is None, API modules fall back to es("studio").

    Args:
        ctx: FastMCP Context from tool parameter, or None.

    Returns:
        (username, es_client) - username for user= param, es_client for es_client= param.
    """
    if ctx is None:
        return "ai", None
    user = ctx.get_state("mcp_user")
    es_client = ctx.get_state("mcp_es_client")
    username = (user.get("username") if isinstance(user, dict) else None) or "ai"
    return username, es_client
