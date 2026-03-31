# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import time
from unittest.mock import patch

import pytest

from server import auth


class TestParseExpiry:
    def test_seconds(self):
        assert auth._parse_expiry("30s") == 30

    def test_minutes(self):
        assert auth._parse_expiry("30m") == 30 * 60

    def test_hours(self):
        assert auth._parse_expiry("24h") == 24 * 3600

    def test_days(self):
        assert auth._parse_expiry("7d") == 7 * 86400

    def test_empty_defaults_to_24h(self):
        assert auth._parse_expiry("") == 86400

    def test_invalid_defaults_to_24h(self):
        assert auth._parse_expiry("invalid") == 86400


class TestValidateCredentials:
    def test_requires_credentials(self):
        with pytest.raises(ValueError, match="either api_key or both username and password"):
            auth.validate_credentials({})

    def test_rejects_both_api_key_and_password(self):
        with pytest.raises(ValueError, match="not both"):
            auth.validate_credentials({"api_key": "x", "username": "u", "password": "p"})

    def test_rejects_username_without_password(self):
        with pytest.raises(ValueError, match="username and password"):
            auth.validate_credentials({"username": "u"})


class TestCreateSessionApiKey:
    def test_requires_credentials(self):
        with pytest.raises(ValueError, match="either api_key or both username and password"):
            auth.create_session_api_key({})

    def test_rejects_both_api_key_and_password(self):
        with pytest.raises(ValueError, match="not both"):
            auth.create_session_api_key({"api_key": "x", "username": "u", "password": "p"})


class TestEncodeDecodeJwt:
    def test_encode_requires_jwt_secret(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "")
        with pytest.raises(ValueError, match="AUTH_JWT_SECRET"):
            auth.encode_jwt({"username": "test"}, "encoded-key")

    def test_decode_requires_jwt_secret(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "")
        with pytest.raises(ValueError, match="AUTH_JWT_SECRET"):
            auth.decode_jwt("token")

    def test_encode_decode_roundtrip(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "test-secret-key")
        user = {"username": "alice", "roles": ["user"]}
        api_key = "id:secret"
        token = auth.encode_jwt(user, api_key, expiry="1h")
        payload = auth.decode_jwt(token)
        assert payload["user"] == user
        assert payload["api_key"] == api_key
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_invalid_token_raises(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "test-secret-key")
        import jwt as jwt_lib
        with pytest.raises(jwt_lib.InvalidTokenError):
            auth.decode_jwt("invalid-token")

    def test_decode_expired_token_raises(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "test-secret-key")
        import jwt as jwt_lib
        # Encode with exp in the past by patching time.time only during encode
        with patch("time.time", return_value=1000.0):
            token = auth.encode_jwt({"username": "alice"}, "key", expiry="1h")
        with pytest.raises(jwt_lib.ExpiredSignatureError):
            auth.decode_jwt(token)

    def test_decode_tampered_token_raises(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "test-secret-key")
        import jwt as jwt_lib
        token = auth.encode_jwt({"username": "alice"}, "key", expiry="1h")
        tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
        with pytest.raises(jwt_lib.InvalidTokenError):
            auth.decode_jwt(tampered)

    def test_decode_wrong_secret_raises(self, monkeypatch):
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "secret-a")
        token = auth.encode_jwt({"username": "alice"}, "key", expiry="1h")
        monkeypatch.setattr(auth, "AUTH_JWT_SECRET", "secret-b")
        import jwt as jwt_lib
        with pytest.raises(jwt_lib.InvalidTokenError):
            auth.decode_jwt(token)
