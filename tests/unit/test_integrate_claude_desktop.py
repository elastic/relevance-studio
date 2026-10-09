# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for scripts/install_mcp_proxy.py.

Tests cover .env parsing, Claude Desktop config path resolution, and the
config merge/write logic.  The filesystem writes are always directed to
tmp_path, never to the real Claude Desktop config.
"""

import json
import platform
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# The script lives in scripts/, not src/; import via importlib so pytest
# doesn't need it on sys.path.
import importlib.util


def _load_script():
    spec = importlib.util.spec_from_file_location(
        "integrate_claude_desktop",
        Path(__file__).resolve().parents[2] / "scripts" / "integrate_claude_desktop.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


script = _load_script()


####  read_env_file  ###########################################################


class TestReadEnvFile:
    """Parses a .env file into a plain dict."""

    def test_simple_key_value(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("FOO=bar\nBAZ=qux\n")
        assert script.read_env_file(f) == {"FOO": "bar", "BAZ": "qux"}

    def test_comment_lines_skipped(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("# comment\nKEY=value\n")
        assert script.read_env_file(f) == {"KEY": "value"}

    def test_blank_lines_skipped(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("\n\nKEY=value\n\n")
        assert script.read_env_file(f) == {"KEY": "value"}

    def test_inline_comment_stripped(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("KEY=value # inline comment\n")
        assert script.read_env_file(f) == {"KEY": "value"}

    def test_double_quoted_value(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text('KEY="hello world"\n')
        assert script.read_env_file(f) == {"KEY": "hello world"}

    def test_single_quoted_value(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("KEY='hello world'\n")
        assert script.read_env_file(f) == {"KEY": "hello world"}

    def test_empty_value_included(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("KEY=\n")
        assert script.read_env_file(f) == {"KEY": ""}

    def test_missing_file_returns_empty(self, tmp_path):
        assert script.read_env_file(tmp_path / "nonexistent.env") == {}

    def test_value_with_equals_sign(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("KEY=abc=def=ghi\n")
        assert script.read_env_file(f) == {"KEY": "abc=def=ghi"}

    def test_line_without_equals_skipped(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("NOTAKEY\nKEY=value\n")
        assert script.read_env_file(f) == {"KEY": "value"}

    def test_commented_out_key_skipped(self, tmp_path):
        f = tmp_path / ".env"
        f.write_text("# KEY=secret\nOTHER=ok\n")
        assert script.read_env_file(f) == {"OTHER": "ok"}


####  get_claude_config_path  #################################################


class TestGetClaudeConfigPath:

    def test_darwin_path(self):
        with patch.object(platform, "system", return_value="Darwin"):
            p = script.get_claude_config_path()
        assert "Application Support" in str(p)
        assert "Claude" in str(p)
        assert p.name == "claude_desktop_config.json"

    def test_windows_path(self, monkeypatch):
        monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")
        with patch.object(platform, "system", return_value="Windows"):
            p = script.get_claude_config_path()
        assert "Claude" in str(p)
        assert p.name == "claude_desktop_config.json"

    def test_unsupported_platform_exits(self):
        with patch.object(platform, "system", return_value="Linux"):
            with pytest.raises(SystemExit):
                script.get_claude_config_path()


####  main() integration  #####################################################


def _make_env(tmp_path, content: str) -> Path:
    p = tmp_path / ".env"
    p.write_text(content)
    return p


def _make_venv_python(tmp_path) -> Path:
    python = tmp_path / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.write_text("#!/usr/bin/env python3")
    return python


def _make_entry_point(tmp_path) -> Path:
    ep = tmp_path / "src" / "fastmcp_proxy_entry.py"
    ep.parent.mkdir(parents=True)
    ep.write_text("# entry point")
    return ep


class TestMain:
    """main() writes the correct config and handles edge cases."""

    def _run(self, tmp_path, env_content: str, existing_config: dict | None = None):
        """
        Run main() with fake project root and a temporary Claude config path.
        Returns the parsed config that was written.
        """
        venv_python = _make_venv_python(tmp_path)
        entry_point = _make_entry_point(tmp_path)
        env_file = _make_env(tmp_path, env_content)
        config_path = tmp_path / "claude_desktop_config.json"
        if existing_config is not None:
            config_path.write_text(json.dumps(existing_config))

        with (
            patch.object(script, "PROJECT_ROOT", tmp_path),
            patch.object(script, "VENV_PYTHON", venv_python),
            patch.object(script, "ENTRY_POINT", entry_point),
            patch.object(script, "ENV_FILE", env_file),
            patch.object(script, "get_claude_config_path", return_value=config_path),
        ):
            script.main()

        return json.loads(config_path.read_text())

    def test_creates_config_when_absent(self, tmp_path):
        cfg = self._run(tmp_path, "TLS_ENABLED=false\n")
        assert "relevance-studio" in cfg["mcpServers"]

    def test_command_is_absolute_venv_python(self, tmp_path):
        cfg = self._run(tmp_path, "TLS_ENABLED=false\n")
        entry = cfg["mcpServers"]["relevance-studio"]
        assert entry["command"].endswith("python")
        assert Path(entry["command"]).is_absolute()

    def test_args_contains_entry_point(self, tmp_path):
        cfg = self._run(tmp_path, "TLS_ENABLED=false\n")
        entry = cfg["mcpServers"]["relevance-studio"]
        assert any("fastmcp_proxy_entry" in a for a in entry["args"])

    def test_api_key_included_in_env(self, tmp_path):
        cfg = self._run(tmp_path, "TLS_ENABLED=false\nELASTICSEARCH_API_KEY=mykey\n")
        env = cfg["mcpServers"]["relevance-studio"]["env"]
        assert env["ELASTICSEARCH_API_KEY"] == "mykey"

    def test_empty_values_excluded_from_env(self, tmp_path):
        cfg = self._run(tmp_path, "TLS_ENABLED=false\nELASTICSEARCH_API_KEY=\n")
        env = cfg["mcpServers"]["relevance-studio"]["env"]
        assert "ELASTICSEARCH_API_KEY" not in env

    def test_non_proxy_vars_excluded(self, tmp_path):
        cfg = self._run(tmp_path, "ELASTICSEARCH_URL=https://es.example.com\n")
        env = cfg["mcpServers"]["relevance-studio"]["env"]
        assert "ELASTICSEARCH_URL" not in env

    def test_preserves_existing_other_servers(self, tmp_path):
        existing = {
            "mcpServers": {
                "Other Server": {"command": "other", "args": [], "env": {}}
            }
        }
        cfg = self._run(tmp_path, "TLS_ENABLED=false\n", existing_config=existing)
        assert "Other Server" in cfg["mcpServers"]
        assert "relevance-studio" in cfg["mcpServers"]

    def test_overwrites_existing_relevance_studio_entry(self, tmp_path):
        existing = {
            "mcpServers": {
                "relevance-studio": {"command": "old", "args": ["old"], "env": {}}
            }
        }
        cfg = self._run(
            tmp_path,
            "TLS_ENABLED=false\nELASTICSEARCH_API_KEY=newkey\n",
            existing_config=existing,
        )
        entry = cfg["mcpServers"]["relevance-studio"]
        assert entry["command"] != "old"
        assert entry["env"].get("ELASTICSEARCH_API_KEY") == "newkey"

    def test_tls_cert_vars_included_when_set(self, tmp_path):
        env = (
            "TLS_ENABLED=true\n"
            "TLS_CERT_FILE=/path/cert.pem\n"
            "TLS_KEY_FILE=/path/key.pem\n"
        )
        cfg = self._run(tmp_path, env)
        env_block = cfg["mcpServers"]["relevance-studio"]["env"]
        assert env_block.get("TLS_CERT_FILE") == "/path/cert.pem"
        assert env_block.get("TLS_KEY_FILE") == "/path/key.pem"

    def test_relative_cert_paths_resolved_to_absolute(self, tmp_path):
        # .env uses relative paths (e.g. .certs/cert.pem) which would break
        # when Claude Desktop launches the proxy from a different working dir.
        env = (
            "TLS_ENABLED=true\n"
            "TLS_CERT_FILE=.certs/cert.pem\n"
            "TLS_KEY_FILE=.certs/key.pem\n"
        )
        cfg = self._run(tmp_path, env)
        env_block = cfg["mcpServers"]["relevance-studio"]["env"]
        assert Path(env_block["TLS_CERT_FILE"]).is_absolute()
        assert Path(env_block["TLS_KEY_FILE"]).is_absolute()
        assert env_block["TLS_CERT_FILE"].endswith("cert.pem")
        assert env_block["TLS_KEY_FILE"].endswith("key.pem")

    def test_absolute_cert_paths_unchanged(self, tmp_path):
        env = (
            "TLS_ENABLED=true\n"
            "TLS_CERT_FILE=/etc/ssl/certs/ca.pem\n"
            "TLS_KEY_FILE=/etc/ssl/private/key.pem\n"
        )
        cfg = self._run(tmp_path, env)
        env_block = cfg["mcpServers"]["relevance-studio"]["env"]
        assert env_block["TLS_CERT_FILE"] == "/etc/ssl/certs/ca.pem"
        assert env_block["TLS_KEY_FILE"] == "/etc/ssl/private/key.pem"

    def test_exits_when_venv_missing(self, tmp_path):
        entry_point = _make_entry_point(tmp_path)
        env_file = _make_env(tmp_path, "TLS_ENABLED=false\n")
        missing_python = tmp_path / ".venv" / "bin" / "python"  # not created

        with (
            patch.object(script, "PROJECT_ROOT", tmp_path),
            patch.object(script, "VENV_PYTHON", missing_python),
            patch.object(script, "ENTRY_POINT", entry_point),
            patch.object(script, "ENV_FILE", env_file),
            pytest.raises(SystemExit),
        ):
            script.main()

    def test_exits_when_env_file_missing(self, tmp_path):
        venv_python = _make_venv_python(tmp_path)
        entry_point = _make_entry_point(tmp_path)
        missing_env = tmp_path / ".env"  # not created

        with (
            patch.object(script, "PROJECT_ROOT", tmp_path),
            patch.object(script, "VENV_PYTHON", venv_python),
            patch.object(script, "ENTRY_POINT", entry_point),
            patch.object(script, "ENV_FILE", missing_env),
            pytest.raises(SystemExit),
        ):
            script.main()

    def test_exits_on_invalid_json_in_existing_config(self, tmp_path):
        venv_python = _make_venv_python(tmp_path)
        entry_point = _make_entry_point(tmp_path)
        env_file = _make_env(tmp_path, "TLS_ENABLED=false\n")
        config_path = tmp_path / "claude_desktop_config.json"
        config_path.write_text("{broken json")

        with (
            patch.object(script, "PROJECT_ROOT", tmp_path),
            patch.object(script, "VENV_PYTHON", venv_python),
            patch.object(script, "ENTRY_POINT", entry_point),
            patch.object(script, "ENV_FILE", env_file),
            patch.object(script, "get_claude_config_path", return_value=config_path),
            pytest.raises(SystemExit),
        ):
            script.main()
