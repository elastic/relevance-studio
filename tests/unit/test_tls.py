# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for TLS configuration loader.
"""

# Standard packages
import os

# Third-party packages
import pytest

# App packages
from server.tls import get_tls_config


class TestTlsConfig:
    """Tests for get_tls_config()."""

    def test_default_enabled(self, monkeypatch):
        """TLS_ENABLED defaults to true when unset."""
        monkeypatch.delenv("TLS_ENABLED", raising=False)
        monkeypatch.delenv("TLS_CERT_FILE", raising=False)
        monkeypatch.delenv("TLS_KEY_FILE", raising=False)
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is not None
        assert "TLS_CERT_FILE" in cfg["error"]

    def test_disabled_explicit(self, monkeypatch):
        """TLS_ENABLED=false disables TLS."""
        monkeypatch.setenv("TLS_ENABLED", "false")
        monkeypatch.delenv("TLS_CERT_FILE", raising=False)
        monkeypatch.delenv("TLS_KEY_FILE", raising=False)
        cfg = get_tls_config()
        assert cfg["enabled"] is False
        assert cfg["ssl_context"] is None
        assert cfg["uvicorn_config"] is None
        assert cfg["error"] is None

    def test_disabled_variants(self, monkeypatch):
        """TLS_ENABLED accepts various false values."""
        for val in ("0", "False", "no", "off"):
            monkeypatch.setenv("TLS_ENABLED", val)
            monkeypatch.delenv("TLS_CERT_FILE", raising=False)
            monkeypatch.delenv("TLS_KEY_FILE", raising=False)
            cfg = get_tls_config()
            assert cfg["enabled"] is False
            assert cfg["error"] is None

    def test_missing_cert_var(self, monkeypatch):
        """When enabled, missing TLS_CERT_FILE yields clear error."""
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.delenv("TLS_CERT_FILE", raising=False)
        monkeypatch.setenv("TLS_KEY_FILE", "/tmp/key.pem")
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is not None
        assert "TLS_CERT_FILE" in cfg["error"]
        assert cfg["ssl_context"] is None

    def test_missing_key_var(self, monkeypatch):
        """When enabled, missing TLS_KEY_FILE yields clear error."""
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.setenv("TLS_CERT_FILE", "/tmp/cert.pem")
        monkeypatch.delenv("TLS_KEY_FILE", raising=False)
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is not None
        assert "TLS_KEY_FILE" in cfg["error"]
        assert cfg["ssl_context"] is None

    def test_missing_cert_file(self, monkeypatch, tmp_path):
        """When enabled, non-existent cert file yields clear error."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        key.write_text("")
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.setenv("TLS_CERT_FILE", str(cert))
        monkeypatch.setenv("TLS_KEY_FILE", str(key))
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is not None
        assert "does not exist" in cfg["error"]
        assert cfg["ssl_context"] is None

    def test_missing_key_file(self, monkeypatch, tmp_path):
        """When enabled, non-existent key file yields clear error."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("")
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.setenv("TLS_CERT_FILE", str(cert))
        monkeypatch.setenv("TLS_KEY_FILE", str(key))
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is not None
        assert "does not exist" in cfg["error"]
        assert cfg["ssl_context"] is None

    def test_valid_files(self, monkeypatch, tmp_path):
        """When enabled with valid cert and key files, returns ssl_context tuple."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("-----BEGIN CERTIFICATE-----\ntest\n-----END CERTIFICATE-----")
        key.write_text("-----BEGIN PRIVATE KEY-----\ntest\n-----END PRIVATE KEY-----")
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.setenv("TLS_CERT_FILE", str(cert))
        monkeypatch.setenv("TLS_KEY_FILE", str(key))
        cfg = get_tls_config()
        assert cfg["enabled"] is True
        assert cfg["error"] is None
        assert cfg["ssl_context"] == (str(cert), str(key))
        assert cfg["uvicorn_config"] == {
            "ssl_certfile": str(cert),
            "ssl_keyfile": str(key),
        }

    def test_ssl_context_tuple(self, monkeypatch, tmp_path):
        """ssl_context is a tuple of (cert_path, key_path) for Flask."""
        cert = tmp_path / "cert.pem"
        key = tmp_path / "key.pem"
        cert.write_text("")
        key.write_text("")
        monkeypatch.setenv("TLS_ENABLED", "true")
        monkeypatch.setenv("TLS_CERT_FILE", str(cert))
        monkeypatch.setenv("TLS_KEY_FILE", str(key))
        cfg = get_tls_config()
        assert isinstance(cfg["ssl_context"], tuple)
        assert len(cfg["ssl_context"]) == 2
        assert cfg["ssl_context"][0] == str(cert)
        assert cfg["ssl_context"][1] == str(key)
