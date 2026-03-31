# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Integration tests for auth routes and middleware.

When AUTH_ENABLED=false (default in test docker-compose):
- /api/auth/session returns system user
- /api/* routes work without login
- POST /api/auth/logout clears cookie (no-op when no session)

Auth-enabled tests require a secured Elasticsearch cluster with valid
credentials supplied via ESRS_TEST_AUTH_URL, ESRS_TEST_AUTH_USERNAME, and
ESRS_TEST_AUTH_PASSWORD environment variables.
"""

import os

import pytest
import requests

pytestmark = pytest.mark.integration_setup

# Auth-enabled test configuration
_AUTH_ESRS_URL = os.getenv("ESRS_TEST_AUTH_URL")
_AUTH_USERNAME = os.getenv("ESRS_TEST_AUTH_USERNAME")
_AUTH_PASSWORD = os.getenv("ESRS_TEST_AUTH_PASSWORD")
_AUTH_TESTS_AVAILABLE = all([_AUTH_ESRS_URL, _AUTH_USERNAME, _AUTH_PASSWORD])
requires_auth_env = pytest.mark.skipif(
    not _AUTH_TESTS_AVAILABLE,
    reason="Auth-enabled tests require ESRS_TEST_AUTH_URL, ESRS_TEST_AUTH_USERNAME, ESRS_TEST_AUTH_PASSWORD",
)


# ---- AUTH_ENABLED=false (default test docker-compose) ----


def test_healthz_no_auth_required(services):
    r = requests.get(f"{services['esrs']}/healthz")
    assert r.status_code == 200
    assert r.json().get("acknowledged") is True


def test_auth_session_returns_system_when_disabled(services):
    r = requests.get(f"{services['esrs']}/api/auth/session")
    assert r.status_code == 200
    data = r.json()
    assert data.get("user", {}).get("username") == "system"


def test_api_routes_accessible_without_login_when_disabled(services):
    r = requests.get(f"{services['esrs']}/api/setup")
    # Setup state can vary (e.g. not bootstrapped), but auth-disabled should never require login.
    assert r.status_code != 401


def test_auth_logout_succeeds(services):
    r = requests.post(f"{services['esrs']}/api/auth/logout")
    assert r.status_code == 200
    assert r.json().get("acknowledged") is True


def test_auth_login_returns_system_when_disabled(services):
    """When AUTH_ENABLED=false, POST /api/auth/login returns system user without validating creds."""
    r = requests.post(
        f"{services['esrs']}/api/auth/login",
        json={"username": "any", "password": "any"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data.get("user", {}).get("username") == "system"


# ---- AUTH_ENABLED=true (requires secured ES cluster) ----


@requires_auth_env
def test_login_with_valid_credentials():
    """Login with valid credentials returns 200 and a session cookie."""
    r = requests.post(
        f"{_AUTH_ESRS_URL}/api/auth/login",
        json={"username": _AUTH_USERNAME, "password": _AUTH_PASSWORD},
    )
    assert r.status_code == 200
    assert r.json().get("user", {}).get("username") == _AUTH_USERNAME
    assert "relevance_studio_session" in r.cookies


@requires_auth_env
def test_login_with_invalid_credentials():
    """Login with invalid credentials returns 401."""
    r = requests.post(
        f"{_AUTH_ESRS_URL}/api/auth/login",
        json={"username": "invalid_user", "password": "wrong_password"},
    )
    assert r.status_code == 401


@requires_auth_env
def test_api_route_without_session_returns_401():
    """API route without session cookie returns 401 when auth is enabled."""
    r = requests.get(f"{_AUTH_ESRS_URL}/api/auth/session")
    assert r.status_code == 401


@requires_auth_env
def test_api_route_with_valid_session():
    """Login then call an API route with the session cookie."""
    session = requests.Session()
    login = session.post(
        f"{_AUTH_ESRS_URL}/api/auth/login",
        json={"username": _AUTH_USERNAME, "password": _AUTH_PASSWORD},
    )
    assert login.status_code == 200
    r = session.get(f"{_AUTH_ESRS_URL}/api/auth/session")
    assert r.status_code == 200
    assert r.json().get("user", {}).get("username") == _AUTH_USERNAME


@requires_auth_env
def test_session_returns_user_metadata():
    """Session endpoint returns authenticated user metadata."""
    session = requests.Session()
    session.post(
        f"{_AUTH_ESRS_URL}/api/auth/login",
        json={"username": _AUTH_USERNAME, "password": _AUTH_PASSWORD},
    )
    r = session.get(f"{_AUTH_ESRS_URL}/api/auth/session")
    assert r.status_code == 200
    user = r.json().get("user", {})
    assert "username" in user
    assert "roles" in user


@requires_auth_env
def test_logout_clears_session():
    """Logout clears session; subsequent API call returns 401."""
    session = requests.Session()
    session.post(
        f"{_AUTH_ESRS_URL}/api/auth/login",
        json={"username": _AUTH_USERNAME, "password": _AUTH_PASSWORD},
    )
    logout = session.post(f"{_AUTH_ESRS_URL}/api/auth/logout")
    assert logout.status_code == 200
    r = session.get(f"{_AUTH_ESRS_URL}/api/auth/session")
    assert r.status_code == 401
