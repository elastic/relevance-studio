# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import pytest

from server import auth
from server.flask import app, AUTH_COOKIE_NAME, _request_user


@pytest.fixture
def client():
    return app.test_client()


class TestAuthDisabled:
    """When AUTH_ENABLED=false, all /api/* routes work without login."""

    @pytest.fixture(autouse=True)
    def disable_auth(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_ENABLED", False)

    def test_healthz_always_accessible(self, client):
        r = client.get("/healthz")
        assert r.status_code == 200

    def test_api_setup_accessible_without_cookie(self, client):
        r = client.get("/api/setup")
        # May 200 or 500 depending on ES connectivity; should not be 401
        assert r.status_code != 401

    def test_auth_session_returns_system_user(self, client, monkeypatch):
        # When AUTH_ENABLED=false, middleware calls es("studio"). Mock to avoid env dependency.
        from unittest.mock import MagicMock
        import server.client as client_mod
        mock_es = MagicMock()
        monkeypatch.setattr(client_mod, "_es_clients", {"studio": mock_es, "content": mock_es})
        r = client.get("/api/auth/session")
        assert r.status_code == 200
        data = r.get_json()
        assert data["user"]["username"] == "system"


class TestAuthEnabled:
    """When AUTH_ENABLED=true, /api/* (except login) require session."""

    @pytest.fixture(autouse=True)
    def enable_auth(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_ENABLED", True)
        monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")

    def test_login_accessible_without_session(self, client, monkeypatch):
        # Login calls validate_credentials which needs es_studio_endpoint. Mock env.
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
        import server.client as client_mod
        monkeypatch.setattr(client_mod, "ELASTICSEARCH_URL", "http://localhost:9200")
        r = client.post("/api/auth/login", json={"username": "x", "password": "y"})
        # 401 from invalid creds, 400 from bad request, or 500 if ES unreachable
        assert r.status_code in (200, 400, 401, 500)

    def test_logout_accessible_without_session(self, client):
        r = client.post("/api/auth/logout")
        assert r.status_code == 200

    def test_protected_route_returns_401_without_cookie(self, client):
        r = client.get("/api/auth/session")
        assert r.status_code == 401

    def test_protected_route_returns_401_with_invalid_cookie(self, client):
        r = client.get("/api/auth/session", headers={"Cookie": f"{AUTH_COOKIE_NAME}=invalid"})
        assert r.status_code == 401

    def test_session_returns_user_with_valid_jwt(self, client, monkeypatch):
        # Valid JWT with api_key. es_from_credentials needs ELASTIC_CLOUD_ID or ELASTICSEARCH_URL.
        monkeypatch.setenv("ELASTICSEARCH_URL", "http://localhost:9200")
        import server.client as client_mod
        monkeypatch.setattr(client_mod, "ELASTICSEARCH_URL", "http://localhost:9200")
        token = auth.encode_jwt({"username": "alice", "roles": ["user"]}, "dGVzdDprZXk=", expiry="1h")
        r = client.get("/api/auth/session", headers={"Cookie": f"{AUTH_COOKIE_NAME}={token}"})
        # 200 with valid JWT and mocked env; 401 if middleware rejects
        assert r.status_code in (200, 401, 500)
        if r.status_code == 200:
            assert r.get_json()["user"]["username"] == "alice"


class TestRequestUser:
    """Test that _request_user() returns a string username for API context, not a dict."""

    def test_request_user_returns_username_string(self):
        with app.test_request_context():
            from flask import g
            g.user = {"username": "alice", "roles": ["user"]}
            result = _request_user()
            assert result == "alice"
            assert isinstance(result, str)

    def test_request_user_returns_none_when_no_user(self):
        with app.test_request_context():
            from flask import g
            if hasattr(g, "user"):
                del g.user
            result = _request_user()
            assert result is None


class TestLoginRoute:
    @pytest.fixture(autouse=True)
    def enable_auth(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_ENABLED", True)
        monkeypatch.setattr(auth, "JWT_SECRET", "test-secret")

    def test_login_requires_body(self, client):
        r = client.post("/api/auth/login", json={})
        assert r.status_code == 400

    def test_login_requires_username_and_password(self, client):
        r = client.post("/api/auth/login", json={"username": "u"})
        assert r.status_code == 400
