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

Full auth flow (login with real ES credentials, session enforcement) requires
a secured Elasticsearch cluster and is not covered by the current test setup.
"""

import pytest
import requests

pytestmark = pytest.mark.integration_setup


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
    assert r.status_code == 200


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
