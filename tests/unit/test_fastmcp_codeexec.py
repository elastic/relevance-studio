"""
Tests for fastmcp_codeexec.py - Code Execution MCP Server.

Tests cover:
- execute_in_sandbox: core sandbox execution
- model_schema: Pydantic schema retrieval
- _generate_api_signatures: API documentation generation
- Sandbox security: blocked imports, restricted operations
"""

from server.fastmcp_codeexec import (
    execute_in_sandbox,
    _generate_api_signatures,
    SAFE_BUILTINS,
)
from server import models


class TestExecuteInSandbox:
    """Tests for the execute_in_sandbox function."""

    def test_simple_result(self):
        """Setting result variable returns the value."""
        code = "result = 42"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == 42
        assert output["output"] is None

    def test_result_dict(self):
        """Result can be a complex data structure."""
        code = 'result = {"name": "test", "values": [1, 2, 3]}'
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == {"name": "test", "values": [1, 2, 3]}

    def test_result_none_by_default(self):
        """Result is None if not set."""
        code = "x = 1 + 1"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] is None

    def test_print_capture(self):
        """Print statements are captured in output."""
        code = 'print("hello")\nprint("world")\nresult = "done"'
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "done"
        assert output["output"] == "hello\nworld"

    def test_print_multiple_args(self):
        """Print with multiple arguments joins them with spaces."""
        code = 'print("a", "b", "c")'
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["output"] == "a b c"

    def test_syntax_error(self):
        """SyntaxError is caught and reported."""
        code = "def foo(\n"  # Invalid syntax
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert output["error"]["type"] == "SyntaxError"
        assert "line" in output["error"]

    def test_runtime_error(self):
        """Runtime errors are caught and reported."""
        code = "x = 1 / 0"
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert output["error"]["type"] == "ZeroDivisionError"
        assert "traceback" in output["error"]

    def test_key_error(self):
        """KeyError is caught and reported."""
        code = 'd = {}\nx = d["missing"]'
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert output["error"]["type"] == "KeyError"

    def test_output_captured_on_error(self):
        """Print output is captured even when code fails."""
        code = 'print("before error")\nx = 1 / 0'
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert output["output"] == "before error"


class TestSandboxBuiltins:
    """Tests for safe builtins availability."""

    def test_len(self):
        code = "result = len([1, 2, 3])"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == 3

    def test_max_min(self):
        code = "result = (max([1, 5, 3]), min([1, 5, 3]))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == (5, 1)

    def test_sorted(self):
        code = "result = sorted([3, 1, 2])"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [1, 2, 3]

    def test_enumerate(self):
        code = "result = list(enumerate(['a', 'b']))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [(0, "a"), (1, "b")]

    def test_zip(self):
        code = "result = list(zip([1, 2], ['a', 'b']))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [(1, "a"), (2, "b")]

    def test_map_filter(self):
        code = "result = list(filter(lambda x: x > 2, map(lambda x: x * 2, [1, 2, 3])))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [4, 6]

    def test_sum(self):
        code = "result = sum([1, 2, 3, 4])"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == 10

    def test_all_any(self):
        code = "result = (all([True, True]), any([False, True]))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == (True, True)

    def test_isinstance(self):
        code = "result = (isinstance(1, int), isinstance('a', str))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == (True, True)

    def test_dict_list_set_operations(self):
        code = """
d = dict(a=1, b=2)
l = list(range(3))
s = set([1, 2, 2, 3])
result = {"dict": d, "list": l, "set_len": len(s)}
"""
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == {"dict": {"a": 1, "b": 2}, "list": [0, 1, 2], "set_len": 3}


class TestSandboxPreloadedModules:
    """Tests for pre-loaded modules in the sandbox."""

    def test_json_module(self):
        code = '''
data = json.dumps({"key": "value"})
parsed = json.loads(data)
result = parsed["key"]
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "value"

    def test_re_module(self):
        code = r'''
match = re.search(r"(\d+)", "abc123def")
result = match.group(1) if match else None
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "123"

    def test_math_module(self):
        code = "result = (math.sqrt(16), math.ceil(3.2), math.floor(3.8))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == (4.0, 4, 3)

    def test_collections_module(self):
        code = '''
counter = collections.Counter(["a", "b", "a", "c", "a"])
result = counter.most_common(2)
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [("a", 3), ("b", 1)]

    def test_itertools_module(self):
        code = "result = list(itertools.chain([1, 2], [3, 4]))"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == [1, 2, 3, 4]

    def test_functools_module(self):
        code = "result = functools.reduce(lambda a, b: a + b, [1, 2, 3, 4])"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == 10

    def test_datetime_module(self):
        code = '''
dt = datetime(2025, 1, 15, 10, 30, 0)
result = dt.isoformat()
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "2025-01-15T10:30:00"

    def test_date_module(self):
        code = '''
d = date(2025, 6, 15)
result = d.isoformat()
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "2025-06-15"

    def test_timedelta_module(self):
        code = '''
delta = timedelta(days=5, hours=3)
result = delta.total_seconds()
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == 5 * 24 * 3600 + 3 * 3600


class TestSandboxSecurity:
    """Tests for sandbox security restrictions."""

    def test_import_blocked(self):
        """Import statements should fail."""
        code = "import os"
        output = execute_in_sandbox(code)
        assert output["success"] is False
        # Import fails because __import__ is not in SAFE_BUILTINS

    def test_from_import_blocked(self):
        """From imports should fail."""
        code = "from os import path"
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test_eval_not_available(self):
        """eval should not be available."""
        code = 'result = eval("1 + 1")'
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert "eval" in output["error"]["message"].lower() or "name" in output["error"]["message"].lower()

    def test_exec_not_available(self):
        """exec should not be available as a builtin."""
        code = 'exec("x = 1")'
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test_open_not_available(self):
        """open should not be available."""
        code = 'f = open("/etc/passwd")'
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test_compile_not_available(self):
        """compile should not be available."""
        code = 'compile("x = 1", "<string>", "exec")'
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test_globals_not_available(self):
        """globals should not be available."""
        code = "result = globals()"
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test_locals_not_available(self):
        """locals should not be available."""
        code = "result = locals()"
        output = execute_in_sandbox(code)
        assert output["success"] is False

    def test___import___not_available(self):
        """__import__ should not be available."""
        code = '__import__("os")'
        output = execute_in_sandbox(code)
        assert output["success"] is False


class TestSandboxApiAccess:
    """Tests for API module access in sandbox."""

    def test_api_module_available(self):
        """The api module should be accessible."""
        code = "result = hasattr(api, 'workspaces')"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] is True

    def test_helpers_module_available(self):
        """The helpers module should be accessible."""
        code = "result = hasattr(helpers, 'workspaces_list')"
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] is True

    def test_api_submodules(self):
        """API submodules should be accessible."""
        code = '''
submodules = [
    hasattr(api, 'workspaces'),
    hasattr(api, 'scenarios'),
    hasattr(api, 'strategies'),
    hasattr(api, 'benchmarks'),
    hasattr(api, 'evaluations'),
]
result = all(submodules)
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] is True


class TestSandboxExceptionHandling:
    """Tests for exception handling within sandbox code."""

    def test_try_except_works(self):
        """Try/except blocks should work with available exceptions."""
        code = '''
try:
    d = {}
    x = d["missing"]
except KeyError:
    result = "caught"
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] == "caught"

    def test_exception_types_available(self):
        """Common exception types should be available."""
        code = '''
exceptions = [
    Exception,
    KeyError,
    ValueError,
    TypeError,
    IndexError,
    AttributeError,
]
result = all(callable(e) for e in exceptions)
'''
        output = execute_in_sandbox(code)
        assert output["success"] is True
        assert output["result"] is True

    def test_raise_custom_exception(self):
        """Raising exceptions should work."""
        code = 'raise ValueError("custom error")'
        output = execute_in_sandbox(code)
        assert output["success"] is False
        assert output["error"]["type"] == "ValueError"
        assert "custom error" in output["error"]["message"]


class TestModelSchema:
    """Tests for model schemas used by model_schema tool."""

    def test_workspace_create_schema(self):
        """WorkspaceCreate model has a valid schema."""
        schema = models.WorkspaceCreate.model_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]

    def test_workspace_update_schema(self):
        """WorkspaceUpdate model has a valid schema."""
        schema = models.WorkspaceUpdate.model_json_schema()
        assert "properties" in schema

    def test_various_create_models_exist(self):
        """Various Create models should exist and have schemas."""
        model_names = [
            "WorkspaceCreate",
            "DisplayCreate",
            "ScenarioCreate",
            "StrategyCreate",
            "BenchmarkCreate",
            "EvaluationCreate",
            "JudgementCreate",
        ]
        for model_name in model_names:
            assert hasattr(models, model_name), f"{model_name} should exist"
            model_class = getattr(models, model_name)
            schema = model_class.model_json_schema()
            assert "properties" in schema, f"{model_name} should have properties"

    def test_various_update_models_exist(self):
        """Various Update models should exist and have schemas."""
        model_names = [
            "WorkspaceUpdate",
            "DisplayUpdate",
            "ScenarioUpdate",
            "StrategyUpdate",
            "BenchmarkUpdate",
        ]
        for model_name in model_names:
            assert hasattr(models, model_name), f"{model_name} should exist"
            model_class = getattr(models, model_name)
            schema = model_class.model_json_schema()
            assert "properties" in schema, f"{model_name} should have properties"


class TestGenerateApiSignatures:
    """Tests for the _generate_api_signatures function."""

    def test_returns_string(self):
        """Should return a non-empty string."""
        signatures = _generate_api_signatures()
        assert isinstance(signatures, str)
        assert len(signatures) > 0

    def test_contains_api_modules(self):
        """Should contain expected API module names."""
        signatures = _generate_api_signatures()
        expected_modules = ["workspaces", "scenarios", "strategies", "benchmarks", "evaluations"]
        for module in expected_modules:
            assert f"api.{module}:" in signatures, f"Should contain api.{module}"

    def test_contains_function_signatures(self):
        """Should contain function signatures with parentheses."""
        signatures = _generate_api_signatures()
        # Should have function definitions with parameters
        assert "(" in signatures
        assert ")" in signatures


class TestSafeBuiltins:
    """Tests for SAFE_BUILTINS configuration."""

    def test_types_available(self):
        """Basic types should be in SAFE_BUILTINS."""
        types = ["bool", "int", "float", "str", "bytes", "list", "tuple", "dict", "set"]
        for t in types:
            assert t in SAFE_BUILTINS, f"{t} should be in SAFE_BUILTINS"

    def test_constants_available(self):
        """Constants should be in SAFE_BUILTINS."""
        assert "None" in SAFE_BUILTINS
        assert "True" in SAFE_BUILTINS
        assert "False" in SAFE_BUILTINS

    def test_dangerous_builtins_excluded(self):
        """Dangerous builtins should NOT be in SAFE_BUILTINS."""
        dangerous = ["eval", "exec", "compile", "open", "__import__", "globals", "locals", "input"]
        for d in dangerous:
            assert d not in SAFE_BUILTINS, f"{d} should NOT be in SAFE_BUILTINS"
