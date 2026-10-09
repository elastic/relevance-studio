#!/usr/bin/env python3
# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Install the Relevance Studio MCP proxy in Claude Desktop.

Reads .env from the project root, then writes (or updates) the
claude_desktop_config.json entry that tells Claude Desktop how to launch the
proxy process.  Existing entries for other MCP servers are preserved.

Usage (from anywhere inside the project):

    python scripts/integrate_claude_desktop.py

Re-run whenever .env changes, then restart Claude Desktop (Cmd+Q, reopen).
"""

import json
import os
import platform
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths (all resolved from this script's location, not cwd)
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = _SCRIPT_DIR.parent
ENV_FILE = PROJECT_ROOT / ".env"
ENTRY_POINT = PROJECT_ROOT / "src" / "fastmcp_proxy_entry.py"
SERVER_NAME = "relevance-studio"

# Platform-appropriate venv Python
if platform.system() == "Windows":
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
else:
    VENV_PYTHON = PROJECT_ROOT / ".venv" / "bin" / "python"

# ---------------------------------------------------------------------------
# Env vars forwarded to Claude Desktop
# ---------------------------------------------------------------------------

# Only vars consumed by fastmcp_proxy.py are forwarded; everything else
# (ES connection details for the server, OTEL, etc.) stays out of the
# Claude Desktop process.
_PROXY_ENV_KEYS = [
    # Upstream URL / TLS
    "MCP_SERVER_URL",
    "FASTMCP_PORT",
    "TLS_ENABLED",
    "TLS_CERT_FILE",
    "TLS_KEY_FILE",
    # Static auth injected into upstream requests (AUTH_ENABLED=true)
    "ELASTICSEARCH_API_KEY",
    "ELASTICSEARCH_USERNAME",
    "ELASTICSEARCH_PASSWORD",
]


def read_env_file(path: Path) -> dict[str, str]:
    """
    Parse a .env file and return a dict of KEY→VALUE.

    Handles comments (#), blank lines, and inline comments.
    Does not expand variable references or shell escapes.
    """
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        # Strip inline comment (naïve: first unquoted #)
        if "#" in value and not (value.startswith('"') or value.startswith("'")):
            value = value[: value.index("#")].strip()
        # Strip surrounding quotes
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        result[key] = value
    return result


def get_claude_config_path() -> Path:
    """Return the platform-specific path to claude_desktop_config.json."""
    system = platform.system()
    if system == "Darwin":
        return (
            Path.home()
            / "Library"
            / "Application Support"
            / "Claude"
            / "claude_desktop_config.json"
        )
    if system == "Windows":
        appdata = os.environ.get("APPDATA") or ""
        if not appdata:
            sys.exit("APPDATA environment variable is not set.")
        return Path(appdata) / "Claude" / "claude_desktop_config.json"
    sys.exit(
        f"Unsupported platform: {system}. "
        "Configure claude_desktop_config.json manually."
    )


def main() -> None:
    # ------------------------------------------------------------------
    # Preflight checks
    # ------------------------------------------------------------------
    errors: list[str] = []
    if not VENV_PYTHON.exists():
        errors.append(
            f"Virtual environment not found: {VENV_PYTHON}\n"
            "  Run: python -m venv .venv && pip install -r requirements.txt"
        )
    if not ENTRY_POINT.exists():
        errors.append(f"Entry point not found: {ENTRY_POINT}")
    if not ENV_FILE.exists():
        errors.append(f".env file not found: {ENV_FILE}")
    if errors:
        sys.exit("\n".join(errors))

    # ------------------------------------------------------------------
    # Build the env block for the Claude Desktop entry
    # ------------------------------------------------------------------
    all_env = read_env_file(ENV_FILE)
    proxy_env = {k: all_env[k] for k in _PROXY_ENV_KEYS if all_env.get(k)}

    # Resolve relative cert/key paths against the project root so they work
    # regardless of the working directory Claude Desktop uses when launching
    # the proxy process.
    for key in ("TLS_CERT_FILE", "TLS_KEY_FILE"):
        if key in proxy_env and not Path(proxy_env[key]).is_absolute():
            proxy_env[key] = str((PROJECT_ROOT / proxy_env[key]).resolve())

    # ------------------------------------------------------------------
    # Read (or initialise) claude_desktop_config.json
    # ------------------------------------------------------------------
    config_path = get_claude_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            sys.exit(
                f"Could not parse {config_path}: {exc}\n"
                "Fix the JSON and re-run."
            )

    config.setdefault("mcpServers", {})

    # ------------------------------------------------------------------
    # Upsert the Relevance Studio entry
    # ------------------------------------------------------------------
    config["mcpServers"][SERVER_NAME] = {
        "command": str(VENV_PYTHON),
        "args": [str(ENTRY_POINT)],
        "env": proxy_env,
    }

    config_path.write_text(
        json.dumps(config, indent=2) + "\n", encoding="utf-8"
    )

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    tls = all_env.get("TLS_ENABLED", "true").strip().lower()
    tls_status = "disabled (HTTP)" if tls in ("false", "0", "no", "off") else "enabled (HTTPS)"
    auth_status = (
        "enabled" if all_env.get("ELASTICSEARCH_API_KEY") or all_env.get("ELASTICSEARCH_USERNAME")
        else "disabled (no credentials in .env)"
    )

    print(f"✓  Installed '{SERVER_NAME}' in Claude Desktop")
    print(f"   Config:  {config_path}")
    print(f"   Python:  {VENV_PYTHON}")
    print(f"   TLS:     {tls_status}")
    print(f"   Auth:    {auth_status}")
    print()
    print("→  Restart Claude Desktop (Cmd+Q, then reopen) to apply.")


if __name__ == "__main__":
    main()
