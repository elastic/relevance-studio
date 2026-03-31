#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  ./scripts/test.sh [--lang py|js|all] [--type unit|integration|all]

Options:
  --lang   Test language group to run (default: all)
  --type   Test type to run (default: all)
  -h, --help  Show this help message

Examples:
  ./scripts/test.sh
  ./scripts/test.sh --lang py --type unit
  ./scripts/test.sh --lang py --type integration
  ./scripts/test.sh --lang js --type unit
  ./scripts/test.sh --lang all --type all

Notes:
  - Python unit tests: pytest tests/unit
  - Python integration tests: pytest tests/integration
  - JS tests in this repo are Jest UI tests: npm run test:ui
  - A separate JS integration suite is not currently defined.
EOF
}

LANGUAGE="all"
TEST_TYPE="all"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --lang)
      [[ $# -ge 2 ]] || { echo "Missing value for --lang" >&2; usage; exit 1; }
      LANGUAGE="$2"
      shift 2
      ;;
    --type)
      [[ $# -ge 2 ]] || { echo "Missing value for --type" >&2; usage; exit 1; }
      TEST_TYPE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      exit 1
      ;;
  esac
done

case "$LANGUAGE" in
  py|js|all) ;;
  *)
    echo "Invalid --lang '$LANGUAGE'. Expected: py, js, all" >&2
    exit 1
    ;;
esac

case "$TEST_TYPE" in
  unit|integration|all) ;;
  *)
    echo "Invalid --type '$TEST_TYPE'. Expected: unit, integration, all" >&2
    exit 1
    ;;
esac

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v git >/dev/null 2>&1 && git -C "$SCRIPT_DIR" rev-parse --show-toplevel >/dev/null 2>&1; then
  REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"
else
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi
cd "$REPO_ROOT"

run_cmd() {
  echo
  echo "==> $*"
  "$@"
}

ensure_python_tools() {
  command -v pytest >/dev/null 2>&1 || {
    echo "pytest not found. Install Python dependencies first (e.g. pip install -r requirements-dev.txt)." >&2
    exit 1
  }
}

ensure_js_tools() {
  command -v npm >/dev/null 2>&1 || {
    echo "npm not found. Install Node.js and project dependencies first." >&2
    exit 1
  }
}

ensure_docker_for_integration() {
  command -v docker >/dev/null 2>&1 || {
    echo "docker not found. Python integration tests require Docker." >&2
    exit 1
  }
  docker info >/dev/null 2>&1 || {
    echo "Docker daemon is not reachable. Start Docker, then re-run integration tests." >&2
    exit 1
  }
}

run_py_unit() {
  ensure_python_tools
  run_cmd pytest tests/unit
}

run_py_integration() {
  ensure_python_tools
  ensure_docker_for_integration
  run_cmd pytest tests/integration
}

run_js_unit() {
  ensure_js_tools
  run_cmd npm run test:ui
}

if [[ "$LANGUAGE" == "js" && "$TEST_TYPE" == "integration" ]]; then
  echo "No JS integration test suite is currently defined in this repository." >&2
  echo "Use --type unit for JS tests." >&2
  exit 1
fi

if [[ "$LANGUAGE" == "py" || "$LANGUAGE" == "all" ]]; then
  if [[ "$TEST_TYPE" == "unit" || "$TEST_TYPE" == "all" ]]; then
    run_py_unit
  fi
  if [[ "$TEST_TYPE" == "integration" || "$TEST_TYPE" == "all" ]]; then
    run_py_integration
  fi
fi

if [[ "$LANGUAGE" == "js" || "$LANGUAGE" == "all" ]]; then
  if [[ "$TEST_TYPE" == "unit" || "$TEST_TYPE" == "all" ]]; then
    run_js_unit
  elif [[ "$TEST_TYPE" == "integration" ]]; then
    echo "Skipping JS integration tests (none defined)." >&2
  fi
fi

echo
echo "All requested tests completed."
