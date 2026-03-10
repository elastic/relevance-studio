# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Central TLS configuration loader for Relevance Studio servers.

Environment variables:
- TLS_ENABLED: "true" or "false" (default: "true")
- TLS_CERT_FILE: Path to PEM certificate file (required when TLS_ENABLED=true)
- TLS_KEY_FILE: Path to PEM private key file (required when TLS_ENABLED=true)

When TLS_ENABLED is true, both TLS_CERT_FILE and TLS_KEY_FILE must be set and
the files must exist. Otherwise startup fails with a clear error message.
"""

# Standard packages
import os
from typing import Any, Dict, Optional, Tuple

# Third-party packages
from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: Optional[str], default: bool = True) -> bool:
    """Parse a string as boolean. Default when empty/None."""
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def get_tls_config() -> Dict[str, Any]:
    """
    Load TLS configuration from environment.

    Returns:
        Dict with:
        - enabled: bool
        - ssl_context: Optional[Tuple[str, str]] - (cert_path, key_path) for Flask/werkzeug
        - uvicorn_config: Optional[Dict] - ssl_certfile/ssl_keyfile for FastMCP/uvicorn
        - error: Optional[str] - clear error message when config is invalid
    """
    enabled = _parse_bool(os.environ.get("TLS_ENABLED"), default=True)
    cert_file = (os.environ.get("TLS_CERT_FILE") or "").strip()
    key_file = (os.environ.get("TLS_KEY_FILE") or "").strip()

    if not enabled:
        return {
            "enabled": False,
            "ssl_context": None,
            "uvicorn_config": None,
            "error": None,
        }

    # TLS enabled: require both vars
    if not cert_file:
        return {
            "enabled": True,
            "ssl_context": None,
            "uvicorn_config": None,
            "error": "TLS_ENABLED is true but TLS_CERT_FILE is not set. Set TLS_CERT_FILE to the path of your PEM certificate, or set TLS_ENABLED=false to disable TLS.",
        }
    if not key_file:
        return {
            "enabled": True,
            "ssl_context": None,
            "uvicorn_config": None,
            "error": "TLS_ENABLED is true but TLS_KEY_FILE is not set. Set TLS_KEY_FILE to the path of your PEM private key, or set TLS_ENABLED=false to disable TLS.",
        }

    # Require files to exist
    if not os.path.isfile(cert_file):
        return {
            "enabled": True,
            "ssl_context": None,
            "uvicorn_config": None,
            "error": f"TLS_CERT_FILE does not exist or is not a file: {cert_file}. Provide a valid PEM certificate path or set TLS_ENABLED=false.",
        }
    if not os.path.isfile(key_file):
        return {
            "enabled": True,
            "ssl_context": None,
            "uvicorn_config": None,
            "error": f"TLS_KEY_FILE does not exist or is not a file: {key_file}. Provide a valid PEM key path or set TLS_ENABLED=false.",
        }

    ssl_context: Tuple[str, str] = (cert_file, key_file)
    uvicorn_config = {"ssl_certfile": cert_file, "ssl_keyfile": key_file}

    return {
        "enabled": True,
        "ssl_context": ssl_context,
        "uvicorn_config": uvicorn_config,
        "error": None,
    }
