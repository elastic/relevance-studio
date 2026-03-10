# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Integration tests for TLS: verify Flask serves HTTPS when configured with TLS,
and rejects when TLS is misconfigured.
"""

import os
import shutil
import socket
import subprocess
import sys
import time
from typing import Optional, Tuple

import pytest
import requests
from requests.exceptions import SSLError

pytestmark = pytest.mark.integration_tls

# Project root (where src/ lives)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_PATH = os.path.join(PROJECT_ROOT, "src")


def _find_available_port() -> int:
    """Find an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _generate_self_signed_certs(tmpdir: str) -> Tuple[str, str]:
    """Generate self-signed cert and key using openssl. Returns (cert_path, key_path)."""
    cert_path = os.path.join(tmpdir, "cert.pem")
    key_path = os.path.join(tmpdir, "key.pem")
    subprocess.run(
        [
            "openssl", "req", "-x509", "-nodes", "-days", "1",
            "-newkey", "rsa:2048",
            "-keyout", key_path,
            "-out", cert_path,
            "-subj", "/CN=localhost",
        ],
        check=True,
        capture_output=True,
    )
    return cert_path, key_path


def _start_flask_subprocess(
    port: int,
    tls_enabled: str,
    tls_cert_file: Optional[str] = None,
    tls_key_file: Optional[str] = None,
) -> subprocess.Popen:
    """Start Flask server as subprocess. Caller must terminate it."""
    env = os.environ.copy()
    env["PYTHONPATH"] = SRC_PATH
    env["FLASK_RUN_HOST"] = "127.0.0.1"
    env["FLASK_RUN_PORT"] = str(port)
    env["ELASTICSEARCH_URL"] = "http://localhost:9200"
    env["AUTH_ENABLED"] = "false"
    env["TLS_ENABLED"] = tls_enabled
    if tls_cert_file:
        env["TLS_CERT_FILE"] = tls_cert_file
    if tls_key_file:
        env["TLS_KEY_FILE"] = tls_key_file

    proc = subprocess.Popen(
        [sys.executable, "-m", "server.flask"],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


def _wait_for_server(url: str, timeout_sec: float = 10.0, verify: bool = False) -> bool:
    """Poll until server responds or timeout."""
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        try:
            r = requests.get(url, timeout=2, verify=verify)
            if r.status_code == 200:
                return True
        except (requests.exceptions.ConnectionError, requests.exceptions.SSLError):
            pass
        time.sleep(0.2)
    return False


@pytest.fixture
def cert_dir(tmp_path):
    """Temporary directory for generated certs."""
    return str(tmp_path)


@pytest.mark.skipif(
    not shutil.which("openssl"),
    reason="openssl not available",
)
class TestFlaskTlsIntegration:
    """TLS integration tests for Flask server."""

    def test_flask_serves_https_with_valid_certs(self, cert_dir):
        """Start Flask with valid self-signed certs, make HTTPS request with verify=False, assert 200."""
        cert_path, key_path = _generate_self_signed_certs(cert_dir)
        port = _find_available_port()
        proc = _start_flask_subprocess(
            port, "true", tls_cert_file=cert_path, tls_key_file=key_path
        )
        try:
            assert _wait_for_server(
                f"https://127.0.0.1:{port}/healthz", verify=False
            ), "Server did not become ready"
            r = requests.get(
                f"https://127.0.0.1:{port}/healthz",
                verify=False,
                timeout=5,
            )
            assert r.status_code == 200
            assert r.json() == {"acknowledged": True}
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_flask_serves_http_when_tls_disabled(self):
        """Start Flask with TLS_ENABLED=false, make HTTP request to /healthz, assert 200."""
        port = _find_available_port()
        proc = _start_flask_subprocess(port, "false")
        try:
            assert _wait_for_server(
                f"http://127.0.0.1:{port}/healthz", verify=False
            ), "Server did not become ready"
            r = requests.get(
                f"http://127.0.0.1:{port}/healthz",
                timeout=5,
            )
            assert r.status_code == 200
            assert r.json() == {"acknowledged": True}
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    def test_flask_fails_to_start_with_missing_cert(self):
        """TLS_ENABLED=true with nonexistent TLS_CERT_FILE: Flask exits with non-zero."""
        port = _find_available_port()
        nonexistent = "/nonexistent/cert.pem"
        proc = _start_flask_subprocess(
            port, "true", tls_cert_file=nonexistent, tls_key_file="/tmp/key.pem"
        )
        # Wait up to 5 seconds for process to exit
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.terminate()
            proc.wait(timeout=2)
            pytest.fail("Flask should have exited with error for missing cert")
        assert proc.returncode != 0
        stderr = proc.stderr.read() if proc.stderr else ""
        assert "TLS" in stderr or "cert" in stderr.lower() or "exist" in stderr.lower()

    def test_https_without_trust_fails_verification(self, cert_dir):
        """HTTPS with verify=True (default) raises SSL error for self-signed cert."""
        cert_path, key_path = _generate_self_signed_certs(cert_dir)
        port = _find_available_port()
        proc = _start_flask_subprocess(
            port, "true", tls_cert_file=cert_path, tls_key_file=key_path
        )
        try:
            assert _wait_for_server(
                f"https://127.0.0.1:{port}/healthz", verify=False
            ), "Server did not become ready"
            with pytest.raises(SSLError):
                requests.get(
                    f"https://127.0.0.1:{port}/healthz",
                    verify=True,  # default; enforce verification
                    timeout=5,
                )
        finally:
            proc.terminate()
            proc.wait(timeout=5)
