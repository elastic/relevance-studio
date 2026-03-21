# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Unit tests for the quickstart script.

These tests run the quickstart script via subprocess with --no-start and --dir
pointed at a temp directory. Git and Docker are stubbed out via PATH manipulation
so no real clone or container operations occur.
"""

# Standard packages
import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

# Third-party packages
import pytest

# Paths relative to repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
QUICKSTART_SCRIPT = REPO_ROOT / "scripts" / "quickstart.sh"
ENV_REFERENCE = REPO_ROOT / ".env-reference"


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture()
def install_dir():
    """Create and tear down a temp directory for each test."""
    tmpdir = tempfile.mkdtemp(prefix="quickstart-test-")
    yield Path(tmpdir)
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture()
def seeded_dir(install_dir):
    """
    Pre-seed the install dir with .git/ and .env-reference so the script
    skips cloning and has a template to copy.
    """
    (install_dir / ".git").mkdir()
    shutil.copy(ENV_REFERENCE, install_dir / ".env-reference")
    return install_dir


@pytest.fixture()
def fake_bin(install_dir):
    """
    Create fake git and docker executables that always succeed.
    Returns the path to the fake bin directory.
    """
    bin_dir = install_dir / "_fake_bin"
    bin_dir.mkdir()

    # Fake git — succeeds for fetch, checkout, tag, rev-parse, pull
    fake_git = bin_dir / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        '  tag) echo "v1.0.0" ;;\n'
        '  rev-parse) exit 0 ;;\n'
        '  *) exit 0 ;;\n'
        "esac\n"
    )
    fake_git.chmod(fake_git.stat().st_mode | stat.S_IEXEC)

    # Fake docker — passes prerequisite checks
    fake_docker = bin_dir / "docker"
    fake_docker.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        '  compose) echo "Docker Compose version v2.20.0" ;;\n'
        '  info) exit 0 ;;\n'
        '  *) exit 0 ;;\n'
        "esac\n"
    )
    fake_docker.chmod(fake_docker.stat().st_mode | stat.S_IEXEC)

    return bin_dir


def run_quickstart(
    args: list,
    fake_bin: Path,
    install_dir: Path,
    extra_env: dict = None,
    stdin_input: str = None,
) -> subprocess.CompletedProcess:
    """
    Helper to invoke the quickstart script with fake PATH and NO_COLOR=1.
    Always includes --no-start and --dir <install_dir>.
    """
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["NO_COLOR"] = "1"  # Disable ANSI escapes for easier assertions
    if extra_env:
        env.update(extra_env)

    cmd = ["bash", str(QUICKSTART_SCRIPT)]
    cmd += ["--no-start", "--dir", str(install_dir)]
    cmd += args

    return subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def run_quickstart_raw(
    args: list,
    fake_bin: Path,
    extra_env: dict = None,
) -> subprocess.CompletedProcess:
    """
    Run the quickstart script without automatically injecting --no-start/--dir.
    Useful for testing --help, --uninstall, and argument parsing that exits early.
    """
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["NO_COLOR"] = "1"
    if extra_env:
        env.update(extra_env)

    cmd = ["bash", str(QUICKSTART_SCRIPT)] + args
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def run_quickstart_stdin(
    args: list,
    fake_bin: Path,
    extra_env: dict = None,
) -> subprocess.CompletedProcess:
    """
    Run the quickstart script by piping its contents to bash stdin.
    This matches `curl ... | bash` behavior where BASH_SOURCE may be unset.
    """
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["NO_COLOR"] = "1"
    if extra_env:
        env.update(extra_env)

    cmd = ["bash", "-s", "--"] + args
    return subprocess.run(
        cmd,
        input=QUICKSTART_SCRIPT.read_text(),
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def run_quickstart_interactive(
    args: list,
    fake_bin: Path,
    install_dir: Path,
    stdin_input: str,
    extra_env: dict = None,
) -> subprocess.CompletedProcess:
    """
    Run quickstart with non-TTY prompt mode enabled for tests.
    """
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["NO_COLOR"] = "1"
    env["QUICKSTART_ALLOW_NON_TTY_PROMPTS"] = "true"
    if extra_env:
        env.update(extra_env)

    cmd = ["bash", str(QUICKSTART_SCRIPT)]
    cmd += ["--no-start", "--dir", str(install_dir)]
    cmd += args

    return subprocess.run(
        cmd,
        input=stdin_input,
        capture_output=True,
        text=True,
        timeout=30,
        env=env,
    )


def read_env(install_dir: Path) -> dict:
    """Parse the generated .env file into a dict, ignoring comments and blanks.
    Strips surrounding double quotes from values (matching dotenv behavior)."""
    env = {}
    env_file = install_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                value = value.strip()
                # Strip surrounding double quotes (like dotenv does)
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                env[key.strip()] = value
    return env


def read_env_raw(install_dir: Path) -> dict:
    """Parse the generated .env file into a dict without stripping quotes.
    Useful for asserting that specific values are double-quoted in the file."""
    env = {}
    env_file = install_dir / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                env[key.strip()] = value.strip()
    return env


def write_fake_openssl(fake_bin: Path):
    """Create a fake openssl binary for deterministic tests."""
    fake_openssl = fake_bin / "openssl"
    fake_openssl.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"rand\" ]]; then\n"
        "  echo \"stub-jwt-secret\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"req\" ]]; then\n"
        "  cert_file=\"\"\n"
        "  key_file=\"\"\n"
        "  i=1\n"
        "  while [[ $i -le $# ]]; do\n"
        "    arg=\"${!i}\"\n"
        "    if [[ \"$arg\" == \"-out\" ]]; then\n"
        "      ((i++))\n"
        "      cert_file=\"${!i}\"\n"
        "    elif [[ \"$arg\" == \"-keyout\" ]]; then\n"
        "      ((i++))\n"
        "      key_file=\"${!i}\"\n"
        "    fi\n"
        "    ((i++))\n"
        "  done\n"
        "  [[ -n \"$cert_file\" ]] && { mkdir -p \"$(dirname \"$cert_file\")\"; printf \"stub-cert\\n\" > \"$cert_file\"; }\n"
        "  [[ -n \"$key_file\" ]] && { mkdir -p \"$(dirname \"$key_file\")\"; printf \"stub-key\\n\" > \"$key_file\"; }\n"
        "  if [[ -n \"${OPENSSL_REQ_COUNT_FILE:-}\" ]]; then\n"
        "    if [[ -f \"$OPENSSL_REQ_COUNT_FILE\" ]]; then\n"
        "      count=$(cat \"$OPENSSL_REQ_COUNT_FILE\")\n"
        "    else\n"
        "      count=0\n"
        "    fi\n"
        "    count=$((count + 1))\n"
        "    printf \"%s\" \"$count\" > \"$OPENSSL_REQ_COUNT_FILE\"\n"
        "  fi\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n"
    )
    fake_openssl.chmod(fake_openssl.stat().st_mode | stat.S_IEXEC)


def write_fake_trust_tools(fake_bin: Path, log_file: Path):
    """Create fake uname/sudo/security binaries for trust-store assertions."""
    fake_uname = fake_bin / "uname"
    fake_uname.write_text(
        "#!/usr/bin/env bash\n"
        "echo Darwin\n"
    )
    fake_uname.chmod(fake_uname.stat().st_mode | stat.S_IEXEC)

    fake_sudo = fake_bin / "sudo"
    fake_sudo.write_text(
        "#!/usr/bin/env bash\n"
        "printf '%s\\n' \"$*\" >> \"$TRUST_LOG_FILE\"\n"
        "exit 0\n"
    )
    fake_sudo.chmod(fake_sudo.stat().st_mode | stat.S_IEXEC)

    fake_security = fake_bin / "security"
    fake_security.write_text(
        "#!/usr/bin/env bash\n"
        "exit 0\n"
    )
    fake_security.chmod(fake_security.stat().st_mode | stat.S_IEXEC)


# =============================================================================
# .env construction — Studio deployment with Cloud ID + API Key
# =============================================================================

class TestStudioCloudIdWithApiKey:
    """Studio configured via Elastic Cloud ID + API Key."""

    def test_env_file_created(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "my-cloud:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyRhYmMxMjM=",
            "--studio-elasticsearch-api-key", "key-xyz-123",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTIC_CLOUD_ID"] == "my-cloud:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyRhYmMxMjM="
        assert env["ELASTICSEARCH_API_KEY"] == "key-xyz-123"

    def test_url_not_set(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "my-cloud:abc123",
            "--studio-elasticsearch-api-key", "key-xyz",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env.get("ELASTICSEARCH_URL", "") == ""

    def test_stdout_reports_cloud_id_and_api_key(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "my-cloud:abc123",
            "--studio-elasticsearch-api-key", "key-xyz",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Elastic Cloud ID" in result.stdout
        assert "API Key authentication" in result.stdout


# =============================================================================
# .env construction — Studio deployment with Cloud ID + Username/Password
# =============================================================================

class TestStudioCloudIdWithUsernamePassword:
    """Studio configured via Elastic Cloud ID + username/password."""

    def test_env_file(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "my-cloud:abc",
            "--studio-elasticsearch-username", "elastic",
            "--studio-elasticsearch-password", "changeme",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTIC_CLOUD_ID"] == "my-cloud:abc"
        assert env["ELASTICSEARCH_USERNAME"] == "elastic"
        assert env["ELASTICSEARCH_PASSWORD"] == "changeme"

    def test_stdout(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "my-cloud:abc",
            "--studio-elasticsearch-username", "elastic",
            "--studio-elasticsearch-password", "changeme",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Elastic Cloud ID" in result.stdout
        assert "Username/password authentication" in result.stdout


# =============================================================================
# .env construction — Studio deployment with URL + API Key
# =============================================================================

class TestStudioUrlWithApiKey:
    """Studio configured via Elasticsearch URL + API Key."""

    def test_env_file(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key-abc",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_URL"] == "http://localhost:9200"
        assert env["ELASTICSEARCH_API_KEY"] == "key-abc"

    def test_stdout(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key-abc",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Elasticsearch URL: http://localhost:9200" in result.stdout
        assert "API Key authentication" in result.stdout


# =============================================================================
# .env construction — Studio deployment with URL + Username/Password
# =============================================================================

class TestStudioUrlWithUsernamePassword:
    """Studio configured via URL + username/password."""

    def test_env_file(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "https://es.example.com:9243",
            "--studio-elasticsearch-username", "admin",
            "--studio-elasticsearch-password", "s3cret!@#",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_URL"] == "https://es.example.com:9243"
        assert env["ELASTICSEARCH_USERNAME"] == "admin"
        assert env["ELASTICSEARCH_PASSWORD"] == "s3cret!@#"

    def test_stdout(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-username", "elastic",
            "--studio-elasticsearch-password", "changeme",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Elasticsearch URL: http://localhost:9200" in result.stdout
        assert "Username/password authentication" in result.stdout


# =============================================================================
# .env construction — Content deployment (separate)
# =============================================================================

class TestContentDeploymentSeparate:
    """Separate content deployment with its own credentials."""

    def test_content_url_with_api_key(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://studio:9200",
            "--studio-elasticsearch-api-key", "studio-key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-api-key", "content-key",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_URL"] == "http://studio:9200"
        assert env["ELASTICSEARCH_API_KEY"] == "studio-key"
        assert env["CONTENT_ELASTICSEARCH_URL"] == "http://content:9200"
        assert env["CONTENT_ELASTICSEARCH_API_KEY"] == "content-key"

    def test_content_cloud_id_with_api_key(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://studio:9200",
            "--studio-elasticsearch-api-key", "studio-key",
            "--content-elastic-cloud-id", "content-cloud:abc",
            "--content-elasticsearch-api-key", "content-key",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["CONTENT_ELASTIC_CLOUD_ID"] == "content-cloud:abc"
        assert env["CONTENT_ELASTICSEARCH_API_KEY"] == "content-key"

    def test_content_url_with_username_password(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://studio:9200",
            "--studio-elasticsearch-api-key", "studio-key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-username", "content-user",
            "--content-elasticsearch-password", "content-pass",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["CONTENT_ELASTICSEARCH_URL"] == "http://content:9200"
        assert env["CONTENT_ELASTICSEARCH_USERNAME"] == "content-user"
        assert env["CONTENT_ELASTICSEARCH_PASSWORD"] == "content-pass"

    def test_content_cloud_id_with_username_password(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://studio:9200",
            "--studio-elasticsearch-api-key", "studio-key",
            "--content-elastic-cloud-id", "content-cloud:abc",
            "--content-elasticsearch-username", "content-user",
            "--content-elasticsearch-password", "content-pass",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["CONTENT_ELASTIC_CLOUD_ID"] == "content-cloud:abc"
        assert env["CONTENT_ELASTICSEARCH_USERNAME"] == "content-user"
        assert env["CONTENT_ELASTICSEARCH_PASSWORD"] == "content-pass"

    def test_stdout_reports_content_config(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://studio:9200",
            "--studio-elasticsearch-api-key", "studio-key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-api-key", "content-key",
        ], fake_bin, seeded_dir)
        assert "Configuring content deployment" in result.stdout
        assert "Content Elasticsearch URL: http://content:9200" in result.stdout
        assert "Content API Key authentication" in result.stdout


# =============================================================================
# .env construction — No separate content deployment
# =============================================================================

class TestNoSeparateContent:
    """--no-separate-content-deployment skips content config."""

    def test_skipped_message(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        assert "Skipping separate content deployment" in result.stdout

    def test_content_keys_not_set(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env.get("CONTENT_ELASTICSEARCH_URL", "") == ""
        assert env.get("CONTENT_ELASTIC_CLOUD_ID", "") == ""
        assert env.get("CONTENT_ELASTICSEARCH_API_KEY", "") == ""
        assert env.get("CONTENT_ELASTICSEARCH_USERNAME", "") == ""
        assert env.get("CONTENT_ELASTICSEARCH_PASSWORD", "") == ""


# =============================================================================
# .env construction — OpenTelemetry
# =============================================================================

class TestOtelConfiguration:
    """OpenTelemetry configuration via CLI arguments."""

    def test_all_otel_args(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint", "https://otel.example.com:4317",
            "--otel-exporter-otlp-headers", "Authorization=ApiKey abc123",
            "--otel-resource-attributes", "service.name=esrs",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "https://otel.example.com:4317"
        assert env["OTEL_EXPORTER_OTLP_HEADERS"] == "Authorization=ApiKey abc123"
        assert env["OTEL_RESOURCE_ATTRIBUTES"] == "service.name=esrs"

    def test_otel_headers_double_quoted_in_env_file(self, seeded_dir, fake_bin):
        """OTEL_EXPORTER_OTLP_HEADERS should be double-quoted in the .env file
        because the value typically contains spaces."""
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint", "https://otel.example.com:4317",
            "--otel-exporter-otlp-headers", "Authorization=ApiKey abc123",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        raw = read_env_raw(seeded_dir)
        assert raw["OTEL_EXPORTER_OTLP_HEADERS"] == '"Authorization=ApiKey abc123"'

    def test_otel_endpoint_only(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint", "https://otel.example.com:4317",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["OTEL_EXPORTER_OTLP_ENDPOINT"] == "https://otel.example.com:4317"

    def test_otel_not_set_when_omitted(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        # OTEL keys should remain commented out (not in parsed dict)
        assert env.get("OTEL_EXPORTER_OTLP_ENDPOINT", "") == ""
        assert env.get("OTEL_EXPORTER_OTLP_HEADERS", "") == ""
        assert env.get("OTEL_RESOURCE_ATTRIBUTES", "") == ""

    def test_otel_stdout(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint", "https://otel.example.com:4317",
            "--otel-exporter-otlp-headers", "Authorization=ApiKey abc123",
            "--otel-resource-attributes", "service.name=esrs",
        ], fake_bin, seeded_dir)
        assert "Configuring OpenTelemetry" in result.stdout
        assert "OTLP Endpoint: https://otel.example.com:4317" in result.stdout
        assert "OTLP Headers" in result.stdout
        assert "OTel Resource Attributes" in result.stdout


# =============================================================================
# Argument validation — mutually exclusive options
# =============================================================================

class TestValidateArgsMutuallyExclusive:
    """Test that incompatible argument combos are rejected."""

    def test_studio_cloud_id_and_url_exclusive(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elastic-cloud-id", "cloud-id",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr

    def test_studio_api_key_and_username_exclusive(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--studio-elasticsearch-username", "elastic",
            "--studio-elasticsearch-password", "pass",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr

    def test_studio_username_without_password(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-username", "elastic",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "requires --studio-elasticsearch-password" in result.stderr

    def test_studio_password_without_username(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-password", "pass",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "requires --studio-elasticsearch-username" in result.stderr

    def test_content_cloud_id_and_url_exclusive(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--content-elastic-cloud-id", "cloud-id",
            "--content-elasticsearch-url", "http://content:9200",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr

    def test_content_api_key_and_username_exclusive(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-api-key", "content-key",
            "--content-elasticsearch-username", "user",
            "--content-elasticsearch-password", "pass",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "mutually exclusive" in result.stderr

    def test_content_username_without_password(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-username", "user",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "requires --content-elasticsearch-password" in result.stderr

    def test_content_password_without_username(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--content-elasticsearch-url", "http://content:9200",
            "--content-elasticsearch-password", "pass",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "requires --content-elasticsearch-username" in result.stderr

    def test_no_separate_content_conflicts_with_content_url(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--content-elasticsearch-url", "http://content:9200",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "conflicts with --content-" in result.stderr

    def test_no_separate_content_conflicts_with_content_cloud_id(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--content-elastic-cloud-id", "cloud-id",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "conflicts with --content-" in result.stderr

    def test_no_separate_content_conflicts_with_content_api_key(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--content-elasticsearch-api-key", "content-key",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "conflicts with --content-" in result.stderr


# =============================================================================
# Version normalization
# =============================================================================

class TestVersionNormalization:
    """Test version parsing and normalization."""

    def test_explicit_semver_with_v_prefix(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--version", "v1.0.0",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        assert "Version: v1.0.0" in result.stdout

    def test_semver_without_v_prefix(self, seeded_dir, fake_bin):
        """Script should auto-prepend 'v' to bare semver."""
        result = run_quickstart([
            "--version", "1.0.0",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        assert "Version: v1.0.0" in result.stdout

    def test_invalid_version_format(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--version", "not-a-version",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "Invalid version format" in result.stderr

    def test_incomplete_semver_rejected(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--version", "v1.0",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "Invalid version format" in result.stderr

    def test_version_latest(self, seeded_dir, fake_bin):
        """--version latest should use the latest tag from git."""
        result = run_quickstart([
            "--version", "latest",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        # The fake git returns "v1.0.0" for `git tag -l`
        assert "Version: v1.0.0" in result.stdout

    def test_version_main(self, seeded_dir, fake_bin):
        """--version main should checkout main branch."""
        result = run_quickstart([
            "--version", "main",
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        assert "Version: main (development)" in result.stdout


# =============================================================================
# Terminal output
# =============================================================================

class TestTerminalOutput:
    """Test what gets printed to stdout/stderr."""

    def test_header_printed(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Elasticsearch Relevance Studio" in result.stdout
        assert "You know, for search relevance." in result.stdout

    def test_no_start_completion_message(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Services were not started" in result.stdout
        assert "docker compose up --build -d" in result.stdout

    def test_prerequisite_checks_pass(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        assert "Checking prerequisites" in result.stdout

    def test_configuration_saved_message(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert "Configuration saved to .env" in result.stdout

    def test_install_dir_in_completion(self, seeded_dir, fake_bin):
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert str(seeded_dir) in result.stdout


# =============================================================================
# --help flag
# =============================================================================

class TestHelpFlag:
    """Test --help output."""

    def test_help_exits_zero(self, seeded_dir, fake_bin):
        result = run_quickstart_raw(["--help"], fake_bin)
        assert result.returncode == 0

    def test_help_shows_usage(self, seeded_dir, fake_bin):
        result = run_quickstart_raw(["--help"], fake_bin)
        assert "Usage:" in result.stdout

    def test_help_shows_all_options(self, seeded_dir, fake_bin):
        result = run_quickstart_raw(["--help"], fake_bin)
        for option in [
            "--version",
            "--dir",
            "--no-start",
            "--uninstall",
            "--help",
            "--studio-elastic-cloud-id",
            "--studio-elasticsearch-url",
            "--studio-elasticsearch-api-key",
            "--studio-elasticsearch-username",
            "--studio-elasticsearch-password",
            "--content-elastic-cloud-id",
            "--content-elasticsearch-url",
            "--content-elasticsearch-api-key",
            "--content-elasticsearch-username",
            "--content-elasticsearch-password",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint",
            "--otel-exporter-otlp-headers",
            "--otel-resource-attributes",
        ]:
            assert option in result.stdout, f"--help should list {option}"

    def test_help_via_stdin_exits_zero(self, seeded_dir, fake_bin):
        result = run_quickstart_stdin(["--help"], fake_bin)
        assert result.returncode == 0
        assert "Usage:" in result.stdout


# =============================================================================
# Unknown option
# =============================================================================

class TestUnknownOption:
    """Test that unknown options are rejected."""

    def test_unknown_option(self, seeded_dir, fake_bin):
        result = run_quickstart(["--bogus-flag"], fake_bin, seeded_dir)
        assert result.returncode != 0
        assert "Unknown option" in result.stderr


# =============================================================================
# Idempotency — running twice
# =============================================================================

class TestIdempotency:
    """Test running the script twice on the same directory."""

    def test_second_run_overwrites_env_with_cli_args(self, seeded_dir, fake_bin):
        """When CLI args are provided, a second run should overwrite .env."""
        # First run
        run_quickstart([
            "--studio-elasticsearch-url", "http://first:9200",
            "--studio-elasticsearch-api-key", "first-key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        env1 = read_env(seeded_dir)
        assert env1["ELASTICSEARCH_URL"] == "http://first:9200"

        # Second run with different values
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://second:9200",
            "--studio-elasticsearch-api-key", "second-key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env2 = read_env(seeded_dir)
        assert env2["ELASTICSEARCH_URL"] == "http://second:9200"
        assert env2["ELASTICSEARCH_API_KEY"] == "second-key"

    def test_generate_tls_cert_reuses_existing_certs_on_rerun(self, seeded_dir, fake_bin):
        """When cert files already exist, TLS generation should not regenerate."""
        write_fake_openssl(fake_bin)
        req_count_file = seeded_dir / "openssl-req-count.txt"

        first = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--generate-tls-cert",
        ], fake_bin, seeded_dir, extra_env={
            "OPENSSL_REQ_COUNT_FILE": str(req_count_file),
        })
        assert first.returncode == 0
        assert (seeded_dir / ".certs" / "cert.pem").exists()
        assert (seeded_dir / ".certs" / "key.pem").exists()
        assert req_count_file.read_text() == "1"

        second = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--generate-tls-cert",
        ], fake_bin, seeded_dir, extra_env={
            "OPENSSL_REQ_COUNT_FILE": str(req_count_file),
        })
        assert second.returncode == 0
        assert req_count_file.read_text() == "1"
        env = read_env(seeded_dir)
        assert env["TLS_ENABLED"] == "true"
        assert env["TLS_CERT_FILE"] == "/certs/cert.pem"
        assert env["TLS_KEY_FILE"] == "/certs/key.pem"


class TestInteractiveTlsAuth:
    """Interactive onboarding for TLS/auth defaults and cert options."""

    def test_defaults_enable_tls_autogen_and_auth(self, seeded_dir, fake_bin):
        write_fake_openssl(fake_bin)

        # 2=URL, blank=default URL, auth-required=y, 1=API key, then values/defaults for prompts:
        # content separate=n, OTel=n, TLS=y, auto-generate certs=y,
        # trust cert=n, auth=y
        stdin_input = "\n".join([
            "2",
            "",
            "y",
            "1",
            "api-key-123",
            "",
            "",
            "",
            "",
            "",
            "",
        ]) + "\n"

        result = run_quickstart_interactive([], fake_bin, seeded_dir, stdin_input=stdin_input)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["TLS_ENABLED"] == "true"
        assert env["TLS_CERT_FILE"] == "/certs/cert.pem"
        assert env["TLS_KEY_FILE"] == "/certs/key.pem"
        assert env["AUTH_ENABLED"] == "true"
        assert env["AUTH_JWT_SECRET"] == "stub-jwt-secret"
        assert env["AUTH_SESSION_EXPIRY"] == "24h"
        assert (seeded_dir / ".certs" / "cert.pem").exists()
        assert (seeded_dir / ".certs" / "key.pem").exists()

    def test_autogen_can_trust_cert_when_user_opts_in(self, seeded_dir, fake_bin):
        write_fake_openssl(fake_bin)
        trust_log_file = seeded_dir / "trust.log"
        write_fake_trust_tools(fake_bin, trust_log_file)

        stdin_input = "\n".join([
            "2",
            "",
            "y",
            "1",
            "api-key-123",
            "",
            "",
            "",
            "",
            "y",
            "",
        ]) + "\n"

        result = run_quickstart_interactive(
            [],
            fake_bin,
            seeded_dir,
            stdin_input=stdin_input,
            extra_env={"TRUST_LOG_FILE": str(trust_log_file)},
        )
        assert result.returncode == 0
        assert trust_log_file.exists()
        trust_invocations = trust_log_file.read_text()
        assert "security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain" in trust_invocations
        assert str(seeded_dir / ".certs" / "cert.pem") in trust_invocations

    def test_tls_enabled_without_autogen_prompts_for_paths(self, seeded_dir, fake_bin):
        write_fake_openssl(fake_bin)

        # 2=URL, blank=default URL, auth-required=y, 1=API key, content separate=n, OTel=n,
        # TLS=y, auto-generate certs=n, custom cert/key paths, auth=y.
        stdin_input = "\n".join([
            "2",
            "",
            "y",
            "1",
            "api-key-123",
            "",
            "",
            "",
            "n",
            "/custom/cert.pem",
            "/custom/key.pem",
            "",
        ]) + "\n"

        result = run_quickstart_interactive([], fake_bin, seeded_dir, stdin_input=stdin_input)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["TLS_ENABLED"] == "true"
        assert env["TLS_CERT_FILE"] == "/custom/cert.pem"
        assert env["TLS_KEY_FILE"] == "/custom/key.pem"
        assert env["AUTH_ENABLED"] == "true"
        assert env["AUTH_SESSION_EXPIRY"] == "24h"

    def test_can_skip_studio_deployment_credentials_when_security_disabled(self, seeded_dir, fake_bin):
        write_fake_openssl(fake_bin)

        # 2=URL, blank=default URL, auth-required=n, content separate=n,
        # OTel=n, TLS=y, auto-generate certs=y, trust cert=n, auth=n.
        stdin_input = "\n".join([
            "2",
            "",
            "n",
            "",
            "",
            "",
            "",
            "",
            "n",
        ]) + "\n"

        result = run_quickstart_interactive([], fake_bin, seeded_dir, stdin_input=stdin_input)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_URL"] == "http://localhost:9200"
        assert env.get("ELASTICSEARCH_API_KEY", "") == ""
        assert env.get("ELASTICSEARCH_USERNAME", "") == ""
        assert env.get("ELASTICSEARCH_PASSWORD", "") == ""
        assert env["AUTH_ENABLED"] == "false"


# =============================================================================
# Edge cases — special characters in values
# =============================================================================

class TestSpecialCharacters:
    """Test that special characters in values are preserved."""

    def test_api_key_with_equals_and_slashes(self, seeded_dir, fake_bin):
        """API keys often contain base64 characters."""
        api_key = "bXktYXBpLWtleQ==:dGVzdC1rZXk="
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", api_key,
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_API_KEY"] == api_key

    def test_url_with_port_and_path(self, seeded_dir, fake_bin):
        url = "https://es.example.com:9243/custom/path"
        result = run_quickstart([
            "--studio-elasticsearch-url", url,
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTICSEARCH_URL"] == url

    def test_cloud_id_with_base64(self, seeded_dir, fake_bin):
        cloud_id = "my-deployment:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvOjQ0MyRhYmMxMjMkZGVmNDU2"
        result = run_quickstart([
            "--studio-elastic-cloud-id", cloud_id,
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        env = read_env(seeded_dir)
        assert env["ELASTIC_CLOUD_ID"] == cloud_id

    def test_otel_headers_with_spaces(self, seeded_dir, fake_bin):
        headers = "Authorization=ApiKey dGVzdC1rZXk="
        result = run_quickstart([
            "--studio-elasticsearch-url", "http://localhost:9200",
            "--studio-elasticsearch-api-key", "key",
            "--no-separate-content-deployment",
            "--otel-exporter-otlp-endpoint", "https://otel:4317",
            "--otel-exporter-otlp-headers", headers,
        ], fake_bin, seeded_dir)
        assert result.returncode == 0
        # read_env strips quotes, so the parsed value should match the input
        env = read_env(seeded_dir)
        assert env["OTEL_EXPORTER_OTLP_HEADERS"] == headers
        # The raw .env file should have the value double-quoted
        raw = read_env_raw(seeded_dir)
        assert raw["OTEL_EXPORTER_OTLP_HEADERS"] == f'"{headers}"'


# =============================================================================
# Uninstall
# =============================================================================

class TestUninstall:
    """Test the --uninstall flag (no Docker needed — just directory removal)."""

    def test_uninstall_removes_directory(self, seeded_dir, fake_bin):
        # First, create a file in the directory to prove it exists
        marker = seeded_dir / "marker.txt"
        marker.write_text("exists")
        assert seeded_dir.exists()

        result = run_quickstart_raw([
            "--uninstall", "--dir", str(seeded_dir),
        ], fake_bin)
        assert result.returncode == 0
        assert not seeded_dir.exists()

    def test_uninstall_nonexistent_dir(self, install_dir, fake_bin):
        """Uninstalling a dir that doesn't exist should warn, not fail."""
        nonexistent = install_dir / "does-not-exist"
        result = run_quickstart_raw([
            "--uninstall", "--dir", str(nonexistent),
        ], fake_bin)
        assert result.returncode == 0
        assert "not found" in result.stdout
        assert "Nothing to uninstall" in result.stdout

    def test_uninstall_nonexistent_dir_no_completion_message(self, install_dir, fake_bin):
        """When the dir doesn't exist, should NOT show the completion message
        or the note about Elasticsearch indices."""
        nonexistent = install_dir / "does-not-exist"
        result = run_quickstart_raw([
            "--uninstall", "--dir", str(nonexistent),
        ], fake_bin)
        assert result.returncode == 0
        assert "Uninstall complete" not in result.stdout
        assert "esrs-*" not in result.stdout

    def test_uninstall_stdout(self, seeded_dir, fake_bin):
        result = run_quickstart_raw([
            "--uninstall", "--dir", str(seeded_dir),
        ], fake_bin)
        assert "Uninstalling" in result.stdout
        assert "Uninstall complete" in result.stdout
        assert "esrs-*" in result.stdout
