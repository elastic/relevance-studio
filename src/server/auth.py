# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import os
import time
from typing import Any, Dict, Optional

# Third-party packages
import jwt
from dotenv import load_dotenv
from elasticsearch.exceptions import ApiError, AuthenticationException

# App packages
from .client import es_from_credentials, es_studio_endpoint

load_dotenv()

# Config
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").strip().lower() in ("true", "1", "yes")
AUTH_JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "").strip()
AUTH_SESSION_EXPIRY = os.getenv("AUTH_SESSION_EXPIRY", "24h").strip()  # e.g. "24h", "7d", "30m"


def _parse_expiry(expiry_str: str) -> int:
    """Parse expiry string like '24h', '7d', '30m' into seconds."""
    if not expiry_str:
        return 86400  # default 24h
    unit = expiry_str[-1].lower()
    try:
        val = int(expiry_str[:-1])
    except ValueError:
        return 86400
    if unit == "s":
        return val
    if unit == "m":
        return val * 60
    if unit == "h":
        return val * 3600
    if unit == "d":
        return val * 86400
    return 86400


def session_expiry_seconds(expiry: Optional[str] = None) -> int:
    """Return session expiry in seconds from AUTH_SESSION_EXPIRY or override."""
    return _parse_expiry(expiry or AUTH_SESSION_EXPIRY)


def validate_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate credentials against Elasticsearch _security/_authenticate.
    Supports Basic Auth (username/password) or ApiKey.

    Args:
        credentials: Dict with either:
            - api_key: str (base64 encoded "id:api_key")
            - username + password: str

    Returns:
        User info from _authenticate (username, roles, metadata, etc.)

    Raises:
        ValueError: Invalid credentials format.
        AuthenticationException: Authentication failed (401).
    """
    api_key = credentials.get("api_key")
    username = credentials.get("username")
    password = credentials.get("password")

    if api_key and (username or password):
        raise ValueError("Provide either api_key or username/password, not both.")
    if not api_key and not (username and password):
        raise ValueError("You must provide either api_key or both username and password.")

    endpoint = es_studio_endpoint()
    client = es_from_credentials(
        api_key=api_key if api_key else None,
        username=username if username else None,
        password=password if password else None,
        cloud_id=endpoint.get("cloud_id"),
        url=endpoint.get("hosts", [None])[0] if endpoint.get("hosts") else None,
    )

    try:
        resp = client.security.authenticate()
    except AuthenticationException:
        raise
    except ApiError as e:
        if e.meta.status == 401:
            raise AuthenticationException(message=str(e), meta=e.meta)
        raise

    return resp.body if hasattr(resp, "body") else resp


def create_session_api_key(
    credentials: Dict[str, Any],
    expiry: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create an API key via POST /_security/api_key using the given credentials.
    The API key inherits the authenticated user's permissions.

    Args:
        credentials: Valid credentials (api_key or username/password).
        expiry: Expiration string (e.g. "24h", "7d"). Defaults to AUTH_SESSION_EXPIRY.

    Returns:
        Dict with id, api_key, encoded (base64 id:api_key), expiration.
    """
    api_key = credentials.get("api_key")
    username = credentials.get("username")
    password = credentials.get("password")

    if api_key and (username or password):
        raise ValueError("Provide either api_key or username/password, not both.")
    if not api_key and not (username and password):
        raise ValueError("You must provide either api_key or both username and password.")

    endpoint = es_studio_endpoint()
    client = es_from_credentials(
        api_key=api_key if api_key else None,
        username=username if username else None,
        password=password if password else None,
        cloud_id=endpoint.get("cloud_id"),
        url=endpoint.get("hosts", [None])[0] if endpoint.get("hosts") else None,
    )

    expiry_str = expiry or AUTH_SESSION_EXPIRY
    resp = client.security.create_api_key(
        name="relevance-studio-session",
        expiration=expiry_str,
    )
    # Handle both dict and ObjectApiResponse
    body = resp.body if hasattr(resp, "body") else resp

    return {
        "id": body["id"],
        "api_key": body["api_key"],
        "encoded": body.get("encoded", f"{body['id']}:{body['api_key']}"),
        "expiration": body.get("expiration"),
    }


def encode_jwt(
    user_metadata: Dict[str, Any],
    api_key: str,
    expiry: Optional[str] = None,
) -> str:
    """
    Encode a JWT containing user_metadata and api_key for session use.

    Args:
        user_metadata: User info (username, roles, etc.) from _authenticate.
        api_key: Encoded API key (base64 id:api_key) for ES requests.
        expiry: Expiration string. Defaults to AUTH_SESSION_EXPIRY.

    Returns:
        Signed JWT string.
    """
    if not AUTH_JWT_SECRET:
        raise ValueError("AUTH_JWT_SECRET must be set when AUTH_ENABLED is true")
    exp_seconds = session_expiry_seconds(expiry)
    payload = {
        "user": user_metadata,
        "api_key": api_key,
        "exp": int(time.time()) + exp_seconds,
        "iat": int(time.time()),
    }
    return jwt.encode(payload, AUTH_JWT_SECRET, algorithm="HS256")


def decode_jwt(token: str) -> Dict[str, Any]:
    """
    Decode and verify a JWT. Validates signature and expiration.

    Args:
        token: JWT string.

    Returns:
        Payload dict with user, api_key, exp, iat.

    Raises:
        jwt.InvalidTokenError: Invalid or expired token.
    """
    if not AUTH_JWT_SECRET:
        raise ValueError("AUTH_JWT_SECRET must be set when AUTH_ENABLED is true")
    return jwt.decode(token, AUTH_JWT_SECRET, algorithms=["HS256"])
