# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for .env-reference.

Verifies that:
- Required auth/TLS env vars are documented in .env-reference
- App-used env vars (from src/) are cross-referenced in .env-reference
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
ENV_REFERENCE = REPO_ROOT / ".env-reference"
SRC_DIR = REPO_ROOT / "src"

# Required vars that must appear in .env-reference (auth + TLS from Issue 7)
REQUIRED_ENV_VARS = [
    "AUTH_ENABLED",
    "AUTH_JWT_SECRET",
    "AUTH_SESSION_EXPIRY",
    "TLS_ENABLED",
    "TLS_CERT_FILE",
    "TLS_KEY_FILE",
]

# App-used env vars that should be documented (user-configurable)
# Excludes internal vars like FLASK_RUN_PORT, FASTMCP_PORT, WORKER_*
APP_ENV_VARS = [
    "ELASTIC_CLOUD_ID",
    "ELASTICSEARCH_URL",
    "ELASTICSEARCH_API_KEY",
    "ELASTICSEARCH_USERNAME",
    "ELASTICSEARCH_PASSWORD",
    "CONTENT_ELASTIC_CLOUD_ID",
    "CONTENT_ELASTICSEARCH_URL",
    "CONTENT_ELASTICSEARCH_API_KEY",
    "CONTENT_ELASTICSEARCH_USERNAME",
    "CONTENT_ELASTICSEARCH_PASSWORD",
    "AUTH_ENABLED",
    "AUTH_JWT_SECRET",
    "AUTH_SESSION_EXPIRY",
    "TLS_ENABLED",
    "TLS_CERT_FILE",
    "TLS_KEY_FILE",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "OTEL_EXPORTER_OTLP_HEADERS",
    "OTEL_RESOURCE_ATTRIBUTES",
]


def _parse_env_reference_vars(path: Path) -> set:
    """Extract env var names from .env-reference (VAR= or # VAR=)."""
    vars_found = set()
    pattern = re.compile(r"^#?\s*([A-Za-z_][A-Za-z0-9_]*)\s*=")
    with open(path) as f:
        for line in f:
            m = pattern.match(line.strip())
            if m:
                vars_found.add(m.group(1))
    return vars_found


def test_env_reference_exists():
    """Ensure .env-reference exists at repo root."""
    assert ENV_REFERENCE.exists(), f".env-reference not found at {ENV_REFERENCE}"


def test_required_auth_tls_vars_in_env_reference():
    """Verify AUTH_ENABLED, AUTH_JWT_SECRET, AUTH_SESSION_EXPIRY, TLS_ENABLED, TLS_CERT_FILE, TLS_KEY_FILE are in .env-reference."""
    vars_in_ref = _parse_env_reference_vars(ENV_REFERENCE)
    missing = [v for v in REQUIRED_ENV_VARS if v not in vars_in_ref]
    assert not missing, (
        f"Required env vars missing from .env-reference: {missing}. "
        "Add documentation for these variables."
    )


def test_app_used_env_vars_in_env_reference():
    """Cross-reference: app-used env vars should exist in .env-reference."""
    vars_in_ref = _parse_env_reference_vars(ENV_REFERENCE)
    missing = [v for v in APP_ENV_VARS if v not in vars_in_ref]
    assert not missing, (
        f"App-used env vars not documented in .env-reference: {missing}. "
        "Add these to .env-reference or exclude from APP_ENV_VARS if internal."
    )
