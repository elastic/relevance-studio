# MCP Resources Guide

This document describes the MCP Resources available in Relevance Studio for efficient, low-token data access.

**Use Resources** (Claude Code) or **Lightweight Tools** (Cursor/all clients) for reading data. **Use regular Tools** for creating, updating, deleting, or running evaluations.

## Lightweight Tools (All Clients)

These tools return filtered data and work everywhere, including Cursor:

| Tool | Description |
|------|-------------|
| `workspaces_list` | List all workspaces (_id, name, index_pattern, params, tags) |
| `scenarios_list(workspace_id)` | List scenarios (_id, name, values, tags) |
| `strategies_list(workspace_id)` | List strategies (_id, name, tags) |
| `benchmarks_list(workspace_id)` | List benchmarks (_id, name, description, tags) |
| `evaluations_list(workspace_id)` | List evaluations (_id, benchmark_id, status, took) |
| `evaluation_status(_id)` | Check if evaluation is complete |
| `evaluation_summary(_id)` | Get aggregated metrics (2KB vs 100KB) |
| `evaluation_results_for_strategy(_id, strategy_id)` | Get results for one strategy |

## Available Resources

### Static Resources (Discoverable)

These appear in the MCP client UI and can be discovered via `ListMcpResourcesTool`:

| URI | Description |
|-----|-------------|
| `workspaces://list` | List all workspaces (_id, name, index_pattern, params, rating_scale, tags) |

> **Note:** Only `workspaces://list` is available as a static resource. All other asset types require a `workspace_id` - use the resource templates below.

### Resource Templates (Require Known URIs)

These require you to know the URI pattern. Replace `{_id}`, `{workspace_id}`, etc. with actual values.

#### Displays
| URI Pattern | Description |
|-------------|-------------|
| `displays://{workspace_id}/list` | List displays for a workspace |

#### Scenarios
| URI Pattern | Description |
|-------------|-------------|
| `scenarios://{workspace_id}/list` | List scenarios for a workspace |
| `scenarios://{workspace_id}/by-tag/{tag}` | List scenarios filtered by tag |

#### Strategies
| URI Pattern | Description |
|-------------|-------------|
| `strategies://{workspace_id}/list` | List strategies for a workspace |
| `strategies://{workspace_id}/by-tag/{tag}` | List strategies filtered by tag |
| `strategies://{_id}/template` | Get just the template source for a strategy |

#### Benchmarks
| URI Pattern | Description |
|-------------|-------------|
| `benchmarks://{workspace_id}/list` | List benchmarks for a workspace |
| `benchmarks://{_id}/task` | Get just the task definition for a benchmark |

#### Evaluations
| URI Pattern | Description |
|-------------|-------------|
| `evaluations://{workspace_id}/list` | List evaluations for a workspace |
| `evaluations://{_id}/status` | Get status and metadata only (lightweight) |
| `evaluations://{_id}/summary` | Get summary metrics only (lightweight) |
| `evaluations://{_id}/task` | Get the task definition |
| `evaluations://{_id}/results/{strategy_id}` | Get results for a specific strategy |
| `evaluations://{_id}/unrated` | Get documents with unrated results |
| `evaluations://{_id}/strategies` | List strategies in the evaluation |

## Usage Examples

### Reading a Resource (Claude Code)

```
Use ReadMcpResourceTool with:
- server: "relevance-studio"
- uri: "evaluations://abc123/summary"
```

### Typical Workflow

1. **Get workspaces:** Read `workspaces://list` or use `workspaces_list()` tool
2. **Browse evaluations:** Read `evaluations://{workspace_id}/list` or use `evaluations_list(workspace_id)` tool
3. **Check status:** Read `evaluations://{_id}/status` or use `evaluation_status(_id)` tool
4. **Get summary:** Read `evaluations://{_id}/summary` or use `evaluation_summary(_id)` tool
5. **Drill into strategy:** Read `evaluations://{_id}/results/{strategy_id}` or use `evaluation_results_for_strategy(_id, strategy_id)` tool

### Token Comparison

| Approach | Typical Size |
|----------|--------------|
| `evaluations_get` tool | 50-100KB |
| `evaluations://{_id}/summary` resource | 1-2KB |

