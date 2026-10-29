# Standard packages
import asyncio

# App packages
from server import fastmcp

# 57 `@mcp.tool` decorators before hyperparameter optimization, 18 of which are
# the bulk operations whose parameter types are lists. Hyperparameter
# optimization added 5: strategies_promote, strategies_render,
# benchmarks_estimate, runs_get_variants, and runs_get_optimization_summary.
EXPECTED_TOOL_COUNT = 62

BULK_TOOL_NAMES = {
    "conversations_delete",
    "workspaces_create", "workspaces_update", "workspaces_delete",
    "displays_create", "displays_update", "displays_delete",
    "scenarios_create", "scenarios_update", "scenarios_delete",
    "judgements_set", "judgements_unset",
    "strategies_create", "strategies_update", "strategies_delete",
    "benchmarks_create", "benchmarks_update", "benchmarks_delete",
}


def test_mcp_tool_count():
    """The MCP tool catalog has exactly the expected tools."""
    tools = asyncio.run(fastmcp.mcp._list_tools())
    assert len(tools) == EXPECTED_TOOL_COUNT


def test_all_18_bulk_tools_are_still_registered():
    tools = asyncio.run(fastmcp.mcp._list_tools())
    names = {t.name for t in tools}
    assert BULK_TOOL_NAMES.issubset(names)
    assert len(BULK_TOOL_NAMES) == 18


def test_bulk_tool_param_schemas_stay_minimal_arrays():
    """Hard constraint 3: no growth in JSON schemas embedded in MCP tool
    descriptions. The top-level FastMCP parameter schema for list args stays
    a minimal `{"type": "array", "items": {"type": "object"}}` -- the full
    per-item Pydantic schema lives only once, in the docstring/description
    text, same as it did for the single-object tools before this change."""
    tools = asyncio.run(fastmcp.mcp._list_tools())
    by_name = {t.name: t for t in tools}
    for name in BULK_TOOL_NAMES - {"conversations_delete", "workspaces_delete",
                                    "displays_delete", "scenarios_delete",
                                    "strategies_delete", "benchmarks_delete",
                                    "judgements_unset"}:
        tool = by_name[name]
        list_params = [
            p for p in tool.parameters.get("properties", {}).values()
            if p.get("type") == "array"
        ]
        assert list_params, f"{name} should accept at least one list parameter"
        for param in list_params:
            assert param["items"].get("type") == "object"
            assert set(param["items"].keys()) <= {"type", "additionalProperties"}
