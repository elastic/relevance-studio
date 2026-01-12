# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

"""
Code Execution MCP Server for Relevance Studio.

This server implements the "Code Execution with MCP" pattern from Anthropic's
engineering blog. Instead of many pre-defined tools, it exposes a single
`execute_code` tool that runs Python code in a sandbox with the `api` module
available.

Benefits:
- LLM writes code to fetch, filter, and transform data
- Intermediate data (e.g., 100KB evaluation) stays in sandbox
- Only final results enter LLM context
- 98%+ token reduction for complex operations

Example:
    # LLM writes this code:
    eval_data = api.evaluations.get("abc123")
    summary = eval_data.body["_source"]["summary"]
    best = max(summary["strategy_id"].items(),
               key=lambda x: x[1]["_total"]["metrics"]["ndcg"]["avg"])
    result = {"strategy_id": best[0], "ndcg": best[1]["_total"]["metrics"]["ndcg"]["avg"]}

    # Only `result` (100 bytes) goes back to LLM, not the 100KB evaluation
"""

import signal
import traceback
from contextlib import contextmanager
from typing import Any, Dict

from dotenv import load_dotenv
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from . import api
from .client import es
from . import models
from .fastmcp import instructions as FASTMCP_INSTRUCTIONS

# Parse environment variables
load_dotenv()

# Timeout for code execution (seconds)
EXECUTION_TIMEOUT = 30

# Safe builtins for the sandbox
SAFE_BUILTINS = {
    # Types
    "None": None,
    "True": True,
    "False": False,
    "bool": bool,
    "int": int,
    "float": float,
    "str": str,
    "bytes": bytes,
    "list": list,
    "tuple": tuple,
    "dict": dict,
    "set": set,
    "frozenset": frozenset,
    # Functions
    "abs": abs,
    "all": all,
    "any": any,
    "bin": bin,
    "callable": callable,
    "chr": chr,
    "dir": dir,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "format": format,
    "getattr": getattr,
    "hasattr": hasattr,
    "hash": hash,
    "hex": hex,
    "id": id,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,  # Output captured
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "setattr": setattr,
    "slice": slice,
    "sorted": sorted,
    "sum": sum,
    "type": type,
    "vars": vars,
    "zip": zip,
    # Exceptions (for try/except)
    "Exception": Exception,
    "KeyError": KeyError,
    "ValueError": ValueError,
    "TypeError": TypeError,
    "IndexError": IndexError,
    "AttributeError": AttributeError,
}


@contextmanager
def timeout_context(seconds: int):
    """Context manager for execution timeout."""
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Code execution timed out after {seconds} seconds")

    # Set the signal handler
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        # Restore the old handler and cancel the alarm
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def execute_in_sandbox(code: str) -> Dict[str, Any]:
    """
    Execute Python code in a restricted sandbox.

    The code has access to:
    - `api` module (api.workspaces, api.evaluations, etc.)
    - Safe builtins (dict, list, max, min, sorted, etc.)
    - A `result` variable to set the return value

    Returns:
        Dict with 'success', 'result' or 'error', and 'output' (print statements)
    """
    # Create restricted namespace
    namespace = {
        "__builtins__": SAFE_BUILTINS,
        "api": api,
        "es": es,  # Direct ES client access for advanced queries
        "result": None,  # User sets this to return data
    }

    # Capture print output
    output_lines = []
    original_print = SAFE_BUILTINS["print"]

    def capturing_print(*args, **kwargs):
        output_lines.append(" ".join(str(a) for a in args))

    namespace["__builtins__"] = {**SAFE_BUILTINS, "print": capturing_print}

    try:
        with timeout_context(EXECUTION_TIMEOUT):
            # Execute the code
            exec(code, namespace)

        return {
            "success": True,
            "result": namespace.get("result"),
            "output": "\n".join(output_lines) if output_lines else None,
        }

    except TimeoutError as e:
        return {
            "success": False,
            "error": {
                "type": "TimeoutError",
                "message": str(e),
            },
            "output": "\n".join(output_lines) if output_lines else None,
        }

    except SyntaxError as e:
        return {
            "success": False,
            "error": {
                "type": "SyntaxError",
                "message": str(e),
                "line": e.lineno,
                "offset": e.offset,
            },
            "output": None,
        }

    except Exception as e:
        return {
            "success": False,
            "error": {
                "type": type(e).__name__,
                "message": str(e),
                "traceback": traceback.format_exc(),
            },
            "output": "\n".join(output_lines) if output_lines else None,
        }


def _generate_api_signatures() -> str:
    """Generate API signatures with full docstrings from introspection at startup."""
    import inspect
    import types

    lines = []
    for module_name in api.__all__:
        module = getattr(api, module_name)
        funcs = []
        for name in sorted(dir(module)):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            if isinstance(obj, types.FunctionType) and obj.__module__ == module.__name__:
                sig = inspect.signature(obj)
                doc = inspect.getdoc(obj)
                funcs.append(f"  {name}{sig}")
                if doc:
                    # Indent each line of docstring
                    for doc_line in doc.split('\n'):
                        funcs.append(f"    {doc_line}")
        if funcs:
            lines.append(f"api.{module_name}:")
            lines.extend(funcs)
            lines.append("")  # Blank line between modules

    return "\n".join(lines)


# Generate API signatures once at module load
API_SIGNATURES = _generate_api_signatures()


# MCP Server setup
instructions = FASTMCP_INSTRUCTIONS + f"""
---

## Code Execution

This server provides CODE EXECUTION for Relevance Studio. Write Python code that:
1. Fetches data using the `api` module
2. Processes/filters it locally (data stays in sandbox, not in your context)
3. Sets `result` to return only what you need

### Example

```python
# Fetch large evaluation (100KB) - stays in sandbox
response = api.evaluations.get("abc123")
summary = response.body["_source"]["summary"]

# Process locally
strategies = summary["strategy_id"]
best = max(strategies.items(),
           key=lambda x: x[1]["_total"]["metrics"]["ndcg"]["avg"])

# Only this goes back to you
result = {{"best_strategy": best[0], "ndcg": best[1]["_total"]["metrics"]["ndcg"]["avg"]}}
```

## API Reference

All functions return Elasticsearch responses. Access data via `.body`.

```
{API_SIGNATURES}
```

## Direct Elasticsearch Access

```python
es("studio")  # Studio deployment (workspaces, evaluations, etc.)
es("content") # Content deployment (searchable documents)

# Example: Find latest completed evaluation
body = {{"query": {{"bool": {{"filter": [
    {{"term": {{"workspace_id": workspace_id}}}},
    {{"term": {{"@meta.status": "completed"}}}}
]}}}}, "size": 1, "sort": [{{"@meta.started_at": {{"order": "desc"}}}}]}}
response = es("studio").search(index="esrs-evaluations", body=body)
```

## Tools

- `execute_code(code)` - Run Python code in sandbox
- `model_schema(model_name)` - Get Pydantic schema for create/update (e.g., "WorkspaceCreate")
"""

mcp = FastMCP(name="Relevance Studio (Code Execution)", instructions=instructions)


@mcp.tool()
def execute_code(code: str) -> Dict[str, Any]:
    """
    Execute Python code in a sandbox with access to the Relevance Studio API.

    The code has access to:
    - `api` module (api.workspaces, api.evaluations, api.scenarios, etc.)
    - Safe builtins (dict, list, max, min, sorted, len, etc.)

    Set `result` variable to return data to the LLM.
    Use `print()` for debug output.

    Example:
        response = api.workspaces.search(size=100)
        workspaces = [{"_id": h["_id"], "name": h["_source"]["name"]}
                      for h in response.body["hits"]["hits"]]
        result = {"count": len(workspaces), "workspaces": workspaces}

    Returns:
        {
            "success": bool,
            "result": Any,      # Value of `result` variable if success
            "error": {...},     # Error details if failed
            "output": str       # Captured print() output
        }
    """
    return execute_in_sandbox(code)


@mcp.tool()
def model_schema(model_name: str) -> Dict[str, Any]:
    """
    Get the JSON schema for a Pydantic model used in create/update operations.

    Args:
        model_name: Model name (e.g., "WorkspaceCreate", "EvaluationCreate")

    Available models:
        - WorkspaceCreate, WorkspaceUpdate
        - DisplayCreate, DisplayUpdate
        - ScenarioCreate, ScenarioUpdate
        - StrategyCreate, StrategyUpdate
        - BenchmarkCreate, BenchmarkUpdate
        - EvaluationCreate
        - JudgementCreate
    """
    if not hasattr(models, model_name):
        available = [n for n in dir(models) if n.endswith(("Create", "Update"))]
        return {"error": f"Unknown model: {model_name}", "available": sorted(available)}

    model_class = getattr(models, model_name)
    if not hasattr(model_class, "model_json_schema"):
        return {"error": f"{model_name} is not a Pydantic model"}

    return {
        "model": model_name,
        "schema": model_class.model_json_schema()
    }


@mcp.tool()
def healthz_mcp() -> Dict[str, Any]:
    """Test if application is running."""
    return {"acknowledged": True}


@mcp.custom_route("/healthz", methods=["GET"])
def healthz_http(request: Request) -> JSONResponse:
    """Test if application is running."""
    return JSONResponse({"acknowledged": True})


if __name__ == "__main__":
    mcp.run(transport="http", port=4202, log_level="debug")
