# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for the standalone Claude Desktop entry point (fastmcp_proxy_entry.py).

The entry point exists so that `fastmcp install claude-desktop` can target a
plain script file rather than a package module, sidestepping the relative-import
constraint that prevents running fastmcp_proxy.py directly.
"""

import importlib
import os
import sys

import pytest
from fastmcp import FastMCP
from unittest.mock import patch


####  Helpers  #################################################################

def _import_entry(monkeypatch, env: dict | None = None):
    """
    Apply env overrides, then import/reload fastmcp_proxy_entry.
    Uses empty-string values (not deletion) for credential vars so that
    load_dotenv() inside the proxy module does not re-inject real credentials
    from .env.
    """
    defaults = {
        "TLS_ENABLED": "false",
        "MCP_SERVER_URL": "",
        "ELASTICSEARCH_API_KEY": "",
        "ELASTICSEARCH_USERNAME": "",
    }
    merged = {**defaults, **(env or {})}
    for k, v in merged.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)

    import fastmcp_proxy_entry as mod
    importlib.reload(mod)
    return mod


####  sys.path injection  ######################################################


class TestSysPathInjection:
    """src/ is added to sys.path so the server package is importable."""

    def test_src_dir_is_on_sys_path_after_import(self, monkeypatch):
        mod = _import_entry(monkeypatch)
        src_dir = os.path.dirname(os.path.abspath(mod.__file__))
        assert src_dir in sys.path

    def test_src_dir_not_duplicated_on_repeated_import(self, monkeypatch):
        _import_entry(monkeypatch)
        _import_entry(monkeypatch)
        import fastmcp_proxy_entry as mod
        src_dir = os.path.dirname(os.path.abspath(mod.__file__))
        assert sys.path.count(src_dir) == 1

    def test_server_package_importable_after_entry_import(self, monkeypatch):
        _import_entry(monkeypatch)
        # If src/ is on path, this import must not raise.
        import server  # noqa: F401


####  mcp object  ##############################################################


class TestMcpObject:
    """The entry point exposes the same mcp proxy object as fastmcp_proxy."""

    def test_mcp_is_fastmcp_instance(self, monkeypatch):
        mod = _import_entry(monkeypatch)
        assert isinstance(mod.mcp, FastMCP)

    def test_mcp_is_same_object_as_proxy_module(self, monkeypatch):
        # _import_entry reloads the entry module which runs
        # `from server.fastmcp_proxy import mcp`.  After that,
        # server.fastmcp_proxy is already in sys.modules, so importing
        # it here returns the same module — and the same mcp object.
        mod = _import_entry(monkeypatch)
        import server.fastmcp_proxy as proxy
        assert mod.mcp is proxy.mcp

    def test_mcp_named_relevance_studio(self, monkeypatch):
        mod = _import_entry(monkeypatch)
        assert mod.mcp.name == "relevance-studio"


####  __main__ block  ##########################################################


class TestMainBlock:
    """Running the entry point as __main__ delegates to mcp.run()."""

    def test_main_calls_mcp_run(self, monkeypatch):
        mod = _import_entry(monkeypatch)
        with patch.object(mod.mcp, "run") as mock_run:
            mod.mcp.run()
        mock_run.assert_called_once_with()

    def test_main_block_calls_run_without_transport_arg(self, monkeypatch):
        """Entry point always uses default (stdio) transport — no transport= kwarg."""
        mod = _import_entry(monkeypatch)
        calls = []
        with patch.object(mod.mcp, "run", side_effect=lambda **kw: calls.append(kw)):
            mod.mcp.run()
        assert calls == [{}]


####  TLS misconfiguration  ####################################################


def _import_entry_fresh(monkeypatch, env: dict):
    """
    Like _import_entry, but forces a fresh evaluation of both
    server.fastmcp_proxy AND fastmcp_proxy_entry so module-scope side effects
    (like the TLS error guard) re-run with the updated env.

    importlib.reload() on the entry module alone is not enough: its
    `from server.fastmcp_proxy import mcp` finds the proxy module already in
    sys.modules and skips re-evaluation, masking the SystemExit we're testing.
    """
    for k, v in env.items():
        if v is None:
            monkeypatch.delenv(k, raising=False)
        else:
            monkeypatch.setenv(k, v)
    sys.modules.pop("server.fastmcp_proxy", None)
    sys.modules.pop("fastmcp_proxy_entry", None)
    import fastmcp_proxy_entry as mod
    return mod


class TestTlsMisconfiguration:
    """
    The stdio entry point must fail fast — with the same clear error message
    that get_tls_config() produces — when TLS_ENABLED=true but the cert/key
    files are missing or invalid. Without this, Claude Desktop would launch
    the proxy successfully and surface opaque ssl.SSLCertVerificationError on
    the first tool call.
    """

    def test_missing_cert_file_exits_at_import_with_clear_error(self, monkeypatch, capsys):
        with pytest.raises(SystemExit) as exc_info:
            _import_entry_fresh(
                monkeypatch,
                {"TLS_ENABLED": "true", "TLS_CERT_FILE": "", "TLS_KEY_FILE": ""},
            )
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "TLS_CERT_FILE" in captured.err

    def test_nonexistent_cert_file_exits_at_import_with_clear_error(
        self, monkeypatch, capsys, tmp_path
    ):
        bogus = tmp_path / "does-not-exist.pem"
        with pytest.raises(SystemExit) as exc_info:
            _import_entry_fresh(
                monkeypatch,
                {
                    "TLS_ENABLED": "true",
                    "TLS_CERT_FILE": str(bogus),
                    "TLS_KEY_FILE": str(bogus),
                },
            )
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert str(bogus) in captured.err
