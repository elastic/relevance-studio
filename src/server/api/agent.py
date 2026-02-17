# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import asyncio
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

# Third-party packages
import requests
from fastmcp.client import Client

# App packages
from .. import utils
from ..client import es, ELASTICSEARCH_API_KEY, ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD
from . import conversations as api_conversations

# MCP server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL") or "http://127.0.0.1:4200/mcp"
MCP_ENABLED = True

# MCP tools cache
_tools_cache = None
_tools_lock = None

# Cancellation token system — tracks sessions that have been cancelled
_cancellation_tokens = set()  # session_ids

# Agent configuration
SYSTEM_PROMPT = """
You are an expert in Elasticsearch and search relevance engineering. You help
search engineers using Elasticsearch Relevance Studio — an application that
manages the full lifecycle of search relevance engineering. That means defining
scenarios, curating judgements, building strategies, and benchmarking their
performance.

## Tone & Behavior

- Be concise. The chat is a flyout panel, not a full-page experience. Avoid
  lengthy preambles; get to the point.
- When the user gives a clear instruction, act on it immediately. Don't ask for
  confirmation unless the action is destructive (delete) or genuinely ambiguous.
- After completing an action, briefly confirm what you did and provide a
  markdown link to the affected resource.
- Proactively suggest the next logical step in the relevance engineering
  workflow when it would be helpful.
- Use markdown formatting: **bold** for emphasis, bullet points for lists, and
  code blocks for variables, values, queries, JSON, and other code.

## UI Context

Every request includes a **UI Context** JSON block appended to this prompt. It
contains pre-loaded data about the user's current page and should be your first
source of information before making any tool calls.

### Structure

- `url.base` — The application origin (e.g. `http://localhost:4096`). Use this
  as `base_url` when constructing navigation links.
- `url.path` — The current page path (e.g. `/workspaces/abc/strategies/xyz`).
  Use this to determine which page the user is viewing (see **Pages** below).
- `url.query` — Current query parameters. Possible keys include:
  - `scenario_id` — The selected scenario ID (used on Judgements and Strategy
    Editor pages). No default; if absent, the scenario selector opens
    automatically.
  - `filter` — Active filter on the Judgements page. Default: `rated` (omitted
    from URL when default). Values: `all`, `rated`, `rated-human`, `rated-ai`,
    `unrated`.
  - `sort` — Active sort on the Judgements page. Default: `rating-newest`
    (omitted from URL when default). Values: `match`, `rating-newest`,
    `rating-oldest`. Note: sorting by ratings requires a rated filter; filtering
    by unrated forces sort to `match`.
  - `query` — Free-text search query on the Judgements page. Default: empty.
- `route.params` — Extracted route parameters. Which params are present depends
  on which page the user is on:
  - `workspace_id` — Present on all workspace-scoped pages.
  - `display_id` — Present on the Display Editor page.
  - `strategy_id` — Present on the Strategy Editor page.
  - `benchmark_id` — Present on the Benchmark and Evaluation pages.
  - `evaluation_id` — Present on the Evaluation page.
- `resources` — Pre-loaded data for the current page. Only resources relevant
  to the current route are included:
  - `resources.workspace` — The current workspace document (present on all
    workspace-scoped pages). Contains `_id`, `name`, `index_pattern`,
    `rating_scale`, `params`, and `tags`.
  - `resources.display` — The current display document (Display Editor only).
  - `resources.strategy` — The current strategy document (Strategy Editor only).
    Contains the full strategy body, name, tags, and params.
  - `resources.benchmark` — The current benchmark document (Benchmark and
    Evaluation pages). Contains task definition, metrics, and tags.
  - `resources.evaluation` — The current evaluation document (Evaluation page
    only). Contains `summary` with relevance metrics, status, and results.
  - `resources.scenario` — The current scenario (present when `scenario_id`
    appears in `url.query`).
  - `resources.displays` — All displays for the workspace (present on the
    Judgements, Strategy Editor, and Evaluation pages — not available on all
    pages).

### Pages

Use `url.path` to determine which page the user is viewing and tailor your
responses accordingly:

| Path pattern | Page | What the user sees |
|---|---|---|
| `/` | Home | Welcome screen and setup |
| `/workspaces` | Workspaces | Searchable list of all workspaces |
| `/workspaces/:workspace_id` | Workspace Overview | Navigation hub for a workspace |
| `/workspaces/:workspace_id/displays` | Displays | List of display templates |
| `/workspaces/:workspace_id/displays/:display_id` | Display Editor | Markdown template editor with live doc preview |
| `/workspaces/:workspace_id/scenarios` | Scenarios | Searchable table of scenarios with tags and judgement counts |
| `/workspaces/:workspace_id/judgements` | Judgements | Grid of documents with rating cards for a selected scenario |
| `/workspaces/:workspace_id/strategies` | Strategies | List of strategies |
| `/workspaces/:workspace_id/strategies/:strategy_id` | Strategy Editor | JSON editor for query body with test panel and rank eval |
| `/workspaces/:workspace_id/benchmarks` | Benchmarks | List of benchmarks with evaluation counts |
| `/workspaces/:workspace_id/benchmarks/:benchmark_id` | Benchmark | Evaluation list for a benchmark with run controls |
| `/workspaces/:workspace_id/benchmarks/:benchmark_id/evaluations/:evaluation_id` | Evaluation | Results view with metrics summary, heatmap, and scatterplot |

### Using UI Context Effectively

- Use `route.params.workspace_id` as the active workspace. Only ask the user
  for a workspace if it is absent from the UI Context.
- Use `resources.workspace` to read workspace fields (name, index_pattern,
  rating_scale, params) without calling `workspaces_get`.
- Use `resources.displays` to find matching displays without calling
  `displays_search` — only call the tool if displays are not in the context.
- Use `resources.strategy`, `resources.benchmark`, etc. to avoid redundant
  lookups for the asset the user is currently viewing.
- Use `url.path` to understand what the user is looking at and tailor your
  response. For example, if they're on the Strategy Editor, they're likely
  asking about that strategy; if they're on the Evaluation page, they're
  likely analyzing results.
- Minimize tool calls by checking the UI Context first. Every tool call adds
  latency and visual noise in the reasoning panel.

## Studio Data Assets

- **conversations** — Chat history between the user and the agent (global, not workspace-scoped).
- **workspaces** — A namespace for all other assets. Each asset has a `workspace_id` that matches the workspace `_id`.
- **displays** — A markdown template that controls how documents from specific indices are rendered. Contains `index_pattern`, `fields`, and optional `template.image.url`.
- **scenarios** — A search input representing a user query (e.g. "brown oxfords"). Supports tags for filtering.
- **judgements** — A relevance rating for a specific document (`doc_id`) from a specific index, for a given scenario.
- **strategies** — An Elasticsearch search template (a `query` or `retriever` body) whose params are supplied by scenario values. Supports tags for filtering.
- **benchmarks** — A reusable task definition that specifies which scenarios, strategies, and metrics to evaluate. Supports tags for filtering.
- **evaluations** — The results of running a benchmark, including per-strategy relevance metrics in a `summary` field.

## General Workflow

The typical search relevance engineering workflow:

1. **Select a workspace.** Take note of `_id`, `name`, `index_pattern`, `rating_scale`, and `params`.
2. **Configure displays** to control how documents from content indices are retrieved and rendered.
    - `index_pattern` determines which indices a display applies to. When multiple displays overlap, use the more specific pattern.
    - `fields` lists the fields that should be in `_source.includes` for all searches to that index pattern.
    - `template.image.url` may contain Mustache variables to construct image URLs from document fields.
3. **Define scenarios** — a diverse set of search inputs representative of the use case.
4. **Curate judgements** for each scenario using the workspace's rating scale.
    - `rating_scale.max` represents superb relevance; `rating_scale.min` represents complete irrelevance.
    - Each judgement references an `index` and `doc_id` for the rated document.
5. **Build strategies** — Elasticsearch Search API bodies (a `query` or `retriever`).
    - Strategies must use at least one workspace param as a Mustache variable (e.g. `{{ text }}`).
    - Use `content_mappings_browse` to explore index field structure before writing queries.
6. **Define benchmarks** that specify which scenarios and strategies to evaluate together.
    - Use `benchmarks_make_candidate_pool` to generate candidate documents for evaluation.
7. **Run evaluations** for a benchmark.
    - A worker process executes these asynchronously. It may take seconds or minutes.
    - Use `evaluations_get` to check completion status.
8. **Analyze results.** The `summary` field contains relevance metrics for each `strategy_id` or `strategy_tag`.
9. **Iterate and improve:**
    - Create additional scenarios; adjust tags on scenarios, strategies, or benchmarks.
    - Set or correct judgement ratings.
    - Enhance strategy query logic.
    - Re-run evaluations and compare results.

## Requirements

### 1. Always scope operations by workspace_id

All operations on studio data assets (except conversations) must include a
`workspace_id`. Determine the workspace in this order:

1. Check `route.params.workspace_id` in the UI Context.
2. If absent, check whether a workspace was established earlier in the conversation.
3. If still unknown, ask the user. If they give a name instead of an ID, search
   for the best match with `workspaces_search`. If there are no good matches,
   let the user know and don't perform the operation.

### 2. Always use _source filtering when searching content

Documents in the content deployment often contain very large fields (e.g. dense
vector embeddings, raw metadata) that are irrelevant to relevance engineering.
Returning them wastes context window tokens and slows down the browser. You MUST
use display-informed `_source` filtering whenever searching content indices,
unless the user explicitly instructs you otherwise.

**How to get display fields:**

1. Check `resources.displays` in the UI Context — if present, use it.
2. If not available, call `displays_search` for the workspace.
3. Find the display whose `index_pattern` best matches the target index.

**Which tools require _source filtering and how to apply it:**

| Tool | How to apply | Notes |
|---|---|---|
| `content_search` | Include `"_source": { "includes": [...] }` in the `body` parameter. | The tool passes `body` directly to Elasticsearch. |
| `judgements_search` | Pass `_source: { "includes": [...] }` as the `_source` parameter. | The tool accepts `_source` as a top-level argument. |

If there is no matching display for the target index, omit `_source` filtering
rather than guessing at field names.

**Important:** `evaluations_run` also queries the content deployment (via
Elasticsearch's Rank Eval API), but its queries are constructed from strategy
templates — you do not need to apply `_source` filtering for evaluations.

### 3. Never fabricate IDs

Don't make up fictional values for any `_id` or `doc_id` field of any asset.
Always look them up with the appropriate search or get tool.

## Best Practices

### Strategy authoring

A strategy's `template.source` is a JSON string representing an Elasticsearch
Search API body. It uses Mustache variables (e.g. `{{ text }}`) that are
populated by scenario values at search time.

Key rules:
- The `template.source` must be valid JSON (with Mustache placeholders).
- It must use at least one workspace param as a Mustache variable.
- The `params` field is auto-computed from the template — don't set it manually.
- When creating or editing a strategy, check `resources.workspace.params` to
  know which variables are available.
- Use `content_mappings_browse` to discover which fields exist in the index
  and their types (text, keyword, dense_vector, etc.).
- If `resources.displays` is available, check the display `fields` to
  understand which fields are most useful for the use case.
- Use `content_search` with a simple query to preview sample documents.

### Benchmark task definitions

A benchmark's `task` controls which strategies, scenarios, and metrics are
evaluated together. The structure is:

```
{
  "metrics": ["mrr", "ndcg", "precision", "recall"],  // default: "ndcg", "precision", "recall"
  "k": 10,  // evaluation depth; default: 10; immutable after creation
  "strategies": {
    "_ids": [...],   // specific strategy IDs to include
    "tags": [...]    // include strategies matching these tags
  },
  "scenarios": {
    "_ids": [...],   // specific scenario IDs to include
    "tags": [...],   // include scenarios matching these tags
    "sample_size": 1000,  // max scenarios to randomly sample; default: 1000
    "sample_seed": null   // optional seed for deterministic sampling
  }
}
```

Key behaviors:
- Strategies and scenarios are matched by **param compatibility** — a strategy
  is paired with a scenario only if all strategy params exist in the scenario's
  params.
- Scenarios with no judgements (or no ratings > 0) are automatically excluded.
- If neither `_ids` nor `tags` are specified for strategies or scenarios, all
  compatible assets in the workspace are included.
- Valid metrics: `mrr`, `ndcg`, `precision`, `recall`.
- Use `benchmarks_make_candidate_pool` to preview which strategies and scenarios
  would be included before creating an evaluation.

### Tags

Scenarios, strategies, and benchmarks all support tags. Tags are particularly
important because they affect how evaluation results are analyzed — the
evaluation `summary` groups metrics by `strategy_tag` and `strategy_id`.

Guidelines for tagging:
- **Prefer a small number of high-value tags.** Tags like `baseline`, `v2`,
  `hybrid`, `bm25`, `semantic` are more useful than overly specific ones.
- **Stay consistent with existing tags.** Before creating new tags, use
  `scenarios_tags`, `strategies_tags`, or `benchmarks_tags` to see what's
  already in use. Reuse existing tags rather than creating near-duplicates
  (e.g. don't create `bm-25` if `bm25` already exists).
- **Use tags to define benchmark scope.** Benchmarks filter strategies and
  scenarios by tags, so consistent tagging makes it easy to create benchmarks
  that target specific slices (e.g. all `ecommerce` scenarios against all
  `hybrid` strategies).
- **Tag strategies by approach**, not by iteration. Use `bm25`, `hybrid`,
  `semantic` rather than `attempt-1`, `attempt-2`.
- **Tag scenarios by category** to represent different query types or user
  intents (e.g. `navigational`, `long-tail`, `faceted`).

### Analyze images when judging documents

When judging documents that have a display with a `template.image.url`, reconstruct
the image URL by replacing Mustache variables with document field values. Use the
`get_base64_image_from_url` tool to fetch a small, base64-encoded version. This
is a valuable signal for relevance.

### Handle errors gracefully

- If a tool returns an error, explain the issue to the user in plain language.
- If a search returns no results, suggest broadening the query or checking
  filters and tags.
- If an evaluation is still running, let the user know and offer to check again.
- Never silently swallow errors.

### Pagination

Search tools default to `size: 10`. When comprehensive results are needed,
increase the `size` parameter. Use the `page` parameter to paginate through
large result sets. Set `aggs: true` when aggregation data (like tag counts)
would be useful.

## Guardrails

- **Only use parameters listed in a tool's description.** Each tool only
  accepts the parameters defined in its schema. Do not infer or add parameters
  from other tools, even if they seem related.
- **Don't dump raw JSON** from tool results. Summarize what you found in plain
  language, using tables or bullet points for structured data.
- **Confirm before bulk operations.** If asked to create, update, or delete
  many assets at once (e.g. "create 20 scenarios"), outline the plan and get
  confirmation before proceeding.
- **Confirm before cross-workspace operations.** Don't modify or delete assets
  in a workspace other than the active one without explicit confirmation.

## Responses

### Referencing studio assets

Refer to assets by their names rather than their IDs, which are hard to read.
    - Good: "You are in the [Products](...) workspace"
    - Bad: "You are in the [Products](...) workspace with ID 123"

### Hyperlinks

Help the user navigate by using markdown links to specific pages.

#### URL patterns

| Page | URL |
|---|---|
| Home | `{base}/#/` |
| Workspaces | `{base}/#/workspaces` |
| Workspace Overview | `{base}/#/workspaces/{workspace_id}` |
| Displays | `{base}/#/workspaces/{workspace_id}/displays` |
| Display Editor | `{base}/#/workspaces/{workspace_id}/displays/{display_id}` |
| Scenarios | `{base}/#/workspaces/{workspace_id}/scenarios` |
| Judgements | `{base}/#/workspaces/{workspace_id}/judgements` |
| Strategies | `{base}/#/workspaces/{workspace_id}/strategies` |
| Strategy Editor | `{base}/#/workspaces/{workspace_id}/strategies/{strategy_id}` |
| Benchmarks | `{base}/#/workspaces/{workspace_id}/benchmarks` |
| Benchmark | `{base}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}` |
| Evaluation | `{base}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}/evaluations/{evaluation_id}` |

Query parameters can be appended to deep-link into a specific state:

| Page | Query params | Purpose |
|---|---|---|
| Judgements | `?scenario_id={scenario_id}` | Open judgements for a specific scenario |
| Judgements | `?scenario_id={scenario_id}&filter=unrated` | Show only unrated docs for a scenario |
| Judgements | `?scenario_id={scenario_id}&filter=rated-ai` | Show only AI-rated docs for a scenario |
| Judgements | `?scenario_id={scenario_id}&sort=match` | Sort by query match instead of rating recency |
| Strategy Editor | `?scenario_id={scenario_id}` | Pre-select a scenario for testing |

#### Hyperlink Formatting

- All internal links MUST use the hash-based URL format: `{base}/#{path}`, where
`{base}` is `url.base` from the UI Context. If `url.base` is not available,
omit the base and use only `/#{path}`.
- Prefer hyperlinking the actual names of assets, rather than generic text like "click here" or a raw URL.
    - Good: "the [Products](...) workspace"
    - Good: "Here are the [evaluation results]({base}/#/workspaces/123/benchmarks/456/evaluations/789)."
    - Bad: "[Click here](https://localhost:4096/#/workspaces/123/benchmarks/456/evaluations/789)"
    - Bad: "Click here: https://localhost:4096/#/workspaces/123/benchmarks/456/evaluations/789"
        
### Images

When including images in Markdown, use URL references rather than base64 data URIs:

- Good: `![alt](https://example.com/image.png)`
- Bad: `![alt](data:image/png;base64,iVBORw0KGgo...)`

"""

class SseMessage(str):
    """Base class for Server-Sent Events messages."""
    pass

class SseEvent(SseMessage):
    """An SSE event line."""
    PREFIX = "event: "
    def __new__(cls, name: str):
        return super().__new__(cls, f"{cls.PREFIX}{name}\n")

class SseData(SseMessage):
    """An SSE data line."""
    PREFIX = "data: "
    def __new__(cls, data: Any):
        payload = data if isinstance(data, str) else json.dumps(data)
        return super().__new__(cls, f"{cls.PREFIX}{payload}\n\n")

class McpError(Exception):
    """Base class for MCP-related errors."""
    pass

class McpConnectionError(McpError):
    """Raised when connecting to MCP server fails."""
    pass


def _get_es_url_and_auth():
    """Get Elasticsearch URL and auth from the existing ES client.

    Returns:
        tuple: A tuple containing (base_url, auth, headers).
            base_url (str): The base URL of the Elasticsearch node.
            auth (tuple or None): Basic auth credentials as (username, password).
            headers (dict): Extra headers, including Authorization if an API key is used.
    """
    client = es("studio")
    
    # Get the first node URL
    node = client.transport.node_pool.get()
    base_url = node.base_url
    
    # Determine auth method
    auth = None
    headers = {}
    
    # Check for API key
    if hasattr(client.transport, "_client_meta") or hasattr(node, "config"):
        # Try to get auth from node config
        if hasattr(node, "config"):
            config = node.config
            if hasattr(config, "api_key") and config.api_key:
                # Use API key in header
                headers["Authorization"] = f"ApiKey {config.api_key}"
            elif hasattr(config, "basic_auth") and config.basic_auth:
                # Use basic auth tuple
                auth = config.basic_auth
    
    # Fallback: try to reconstruct from environment
    if not auth and not headers.get("Authorization"):
        if ELASTICSEARCH_API_KEY:
            headers["Authorization"] = f"ApiKey {ELASTICSEARCH_API_KEY}"
        elif ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD:
            auth = (ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD)
    
    return base_url, auth, headers


####  Cancellation Token System  ##############################################

def check_cancellation(session_id: str) -> bool:
    """Return True if cancellation has been requested for this session."""
    return session_id in _cancellation_tokens

def request_cancellation(session_id: str):
    """Request cancellation for a session."""
    _cancellation_tokens.add(session_id)

def cleanup_cancellation_token(session_id: str):
    """Clean up cancellation token after session ends."""
    _cancellation_tokens.discard(session_id)


####  Conversation Persistence  ###############################################

def _apply_stats_to_round(rounds: List[Dict[str, Any]], stats: Dict[str, Any], inference_id: str):
    """Write accumulated agent stats into the last round dict before saving.

    Args:
        rounds: The rounds list whose last entry will be updated.
        stats: The stats dict maintained by the agent loop.
        inference_id: The inference endpoint ID used for this round.
    """
    if not rounds:
        return
    last_round = rounds[-1]
    last_round["model_usage"] = {
        "inference_id": inference_id,
        "llm_calls": stats["llm_calls"],
        "input_tokens": stats["total_input_tokens"],
        "output_tokens": stats["total_output_tokens"],
    }
    if stats.get("first_token_ms") is not None:
        last_round["time_to_first_token"] = int(stats["first_token_ms"])
    if stats.get("last_token_ms") is not None:
        last_round["time_to_last_token"] = int(stats["last_token_ms"])


async def _save_conversation_async(conversation_id: str, rounds: List[Dict[str, Any]], final: bool = False):
    """Asynchronously save conversation state without blocking the agent loop.
    
    Args:
        conversation_id: The conversation ID to update.
        rounds: The rounds data to save.
        final: If True, force refresh for immediate searchability. 
               If False, skip refresh for better performance during streaming.
    """
    try:
        # Run in executor to avoid blocking async loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,  # Use default executor
            lambda: api_conversations.update(
                conversation_id, 
                {"rounds": rounds},
                refresh=final  # Only refresh on final save
            )
        )
    except Exception as e:
        print(f"Error saving conversation {conversation_id}: {e}")
        # Don't raise - saving errors shouldn't crash the agent


def _update_current_round_from_messages(rounds: List[Dict[str, Any]], messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Update the current (last) round based on new message content.
    
    Args:
        rounds: The original rounds structure.
        messages: All messages including the new ones (excluding system message).
    
    Returns:
        Updated rounds list with the current round reflecting the message state.
    """
    if not rounds or len(rounds) == 0:
        return rounds
    
    # Get the current round (last one)
    current_round = rounds[-1]
    
    # Clear existing steps and response to rebuild from messages
    current_round["steps"] = []
    current_round["response"] = {"message": ""}
    # Don't change status here - let the caller handle it
    
    # Find where the current round starts in messages (look for the user message).
    # Search from the end because the current round is always the last one, and
    # the user may have sent the same message text in an earlier round — using
    # the first match would cause all subsequent assistant messages to be
    # concatenated into this round's response.
    user_content = current_round["input"]["message"]
    start_idx = None
    for i in range(len(messages) - 1, -1, -1):
        msg = messages[i]
        if msg.get("role") == "user" and msg.get("content") == user_content:
            start_idx = i
            break
    
    if start_idx is None:
        # Couldn't find the user message, return unchanged
        return rounds
    
    # Process messages from this round
    reasoning_buffer = []
    tool_call_map = {}  # Map tool_call_id to step index
    response_content = []  # Accumulate all assistant responses
    
    for msg in messages[start_idx + 1:]:  # Skip the user message itself
        role = msg.get("role")
        
        if role == "assistant":
            # Accumulate assistant response content
            if msg.get("content"):
                response_content.append(msg["content"])
            
            # Handle reasoning
            if msg.get("reasoning"):
                reasoning_buffer.append(msg["reasoning"])
            
            # Handle tool calls
            if msg.get("tool_calls"):
                # Add accumulated reasoning first if any
                if reasoning_buffer:
                    current_round["steps"].append({
                        "type": "reasoning",
                        "reasoning": "".join(reasoning_buffer)
                    })
                    reasoning_buffer = []
                
                # Add tool call steps
                for tc in msg["tool_calls"]:
                    raw_args = tc["function"].get("arguments")
                    parsed_args = _parse_tool_args(raw_args) if isinstance(raw_args, str) else raw_args
                    if not isinstance(parsed_args, dict):
                        parsed_args = {}
                    step_idx = len(current_round["steps"])
                    tool_call_map[tc["id"]] = step_idx
                    current_round["steps"].append({
                        "type": "tool_call",
                        "tool_id": tc["function"]["name"],
                        "tool_call_id": tc["id"],
                        "params": parsed_args,
                        "results": []
                    })
        
        elif role == "tool":
            # Add tool result to the corresponding tool call step
            tool_call_id = msg.get("tool_call_id")
            if tool_call_id in tool_call_map:
                step_idx = tool_call_map[tool_call_id]
                step = current_round["steps"][step_idx]
                
                content = msg.get("content", "")
                is_error = content.startswith("Error:")
                
                if not step.get("results"):
                    step["results"] = []
                step["results"].append({
                    "type": "error" if is_error else "success",
                    "data": {"message": content}
                })
    
    # Add any remaining reasoning
    if reasoning_buffer:
        current_round["steps"].append({
            "type": "reasoning",
            "reasoning": "".join(reasoning_buffer)
        })
    
    # Set the accumulated response content
    if response_content:
        current_round["response"]["message"] = "\n\n".join(response_content)
    
    return rounds


####  Chat Streaming and Agent Loop  ##########################################

def _chat_stream(messages: List[Dict[str, Any]], inference_id: str = ".rainbow-sprinkles-elastic", tools: Optional[List[Dict]] = None):
    """Internal function to call ES chat_completion with streaming using requests.

    Args:
        messages: A list of message objects for the chat completion.
        inference_id: The ID of the inference endpoint to use.
        tools: Optional list of tools available to the model.

    Returns:
        iterator: An iterator that yields lines from the streaming response.
    """
    # Sanitize messages to only include fields supported by the Inference API
    sanitized_messages = []
    for msg in messages:
        sanitized_msg = {
            "role": msg.get("role"),
        }
        if msg.get("content"):
            sanitized_msg["content"] = msg["content"]
        if "tool_calls" in msg and msg["tool_calls"]:
            sanitized_msg["tool_calls"] = msg["tool_calls"]
        if "tool_call_id" in msg and msg["tool_call_id"]:
            sanitized_msg["tool_call_id"] = msg["tool_call_id"]
        sanitized_messages.append(sanitized_msg)

    body = {"messages": sanitized_messages}
    
    if tools:
        body["tools"] = tools
    
    # Get ES connection details
    base_url, auth, extra_headers = _get_es_url_and_auth()
    
    # Build headers
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream, application/json"
    }
    headers.update(extra_headers)
    
    # Build URL and ensure no double slashes
    base_url = base_url.rstrip("/")
    url = f"{base_url}/_inference/chat_completion/{inference_id}/_stream"
    
    # Make streaming request with requests library
    response = requests.post(
        url,
        json=body,
        auth=auth if auth else None,
        headers=headers,
        stream=True,  # This enables true streaming
        timeout=300  # 5 minute timeout for long responses
    )    
    
    if response.status_code != 200:
        response.raise_for_status()
    
    # Force UTF-8 decoding — the upstream may not declare charset, causing
    # requests to default to ISO-8859-1 which mangles multi-byte characters.
    response.encoding = 'utf-8'
    line_iter = response.iter_lines(decode_unicode=True)
    return line_iter


async def _get_mcp_tools() -> List[Dict[str, Any]]:
    """Connect to MCP server and retrieve available tools.

    Returns:
        List[Dict[str, Any]]: A list of tools in OpenAI function calling format.

    Raises:
        McpConnectionError: If connection to the MCP server fails.
        McpError: For other MCP-related failures.
    """
    global _tools_cache
    if not MCP_ENABLED:
        return []

    if _tools_cache is not None:
        return _tools_cache
    
    global _tools_lock
    if _tools_lock is None:
        _tools_lock = asyncio.Lock()
        
    try:
        async with _tools_lock:
            if _tools_cache is not None:
                return _tools_cache
            return await _load_tools_from_mcp()
    except RuntimeError:
        # Lock might be bound to a different event loop (e.g. from startup asyncio.run)
        _tools_lock = asyncio.Lock()
        async with _tools_lock:
            if _tools_cache is not None:
                return _tools_cache
            return await _load_tools_from_mcp()

async def _load_tools_from_mcp() -> List[Dict[str, Any]]:
    """Helper to perform the actual MCP tool loading.

    Returns:
        List[Dict[str, Any]]: A list of tools in OpenAI function calling format.

    Raises:
        McpConnectionError: If connection to the MCP server fails.
        McpError: For other MCP-related failures.
    """
    global _tools_cache
    try:
        async with Client(MCP_SERVER_URL) as client:
            # List available tools
            tools_list = await client.list_tools()
            
            # Convert MCP tools to Elasticsearch Inference API format
            tools = []
            for tool in tools_list:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema
                    }
                })
            
            _tools_cache = tools
            return _tools_cache
    except Exception as e:
        error_msg = str(e)
        # Check if it looks like a connection failure
        if isinstance(e, (ConnectionError, TimeoutError, RuntimeError)) and "connect" in error_msg.lower():
            raise McpConnectionError(f"Could not connect to MCP server: {error_msg}")
        raise McpError(f"MCP server error: {error_msg}")

async def _call_mcp_tool(tool_name: str, tool_args: Dict[str, Any]) -> Any:
    """Call a specific MCP tool and return the result.

    Args:
        tool_name: The name of the tool to call.
        tool_args: A dictionary of arguments to pass to the tool.

    Returns:
        Any: The text content or string representation of the tool's result.

    Raises:
        McpConnectionError: If connection to the MCP server fails.
        McpError: If the tool call fails.
    """
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(tool_name, tool_args)
            
            # Extract text content from MCP response
            if hasattr(result, "content") and result.content:
                # result.content is a list of ContentItem objects
                text_parts = []
                for item in result.content:
                    if hasattr(item, "text"):
                        text_parts.append(item.text)
                return "\n".join(text_parts) if text_parts else str(result.content)
            
            return str(result)
    except Exception as e:
        error_msg = str(e)
        if isinstance(e, (ConnectionError, TimeoutError, RuntimeError)) and "connect" in error_msg.lower():
            raise McpConnectionError(f"Could not connect to MCP server: {error_msg}")
        raise McpError(f"MCP tool call failed: {error_msg}")


def _parse_stream_chunk(line: str) -> Optional[Dict[str, Any]]:
    """Parse a single line from the ES streaming response.

    Args:
        line: A single line from the streaming response.

    Returns:
        Optional[Dict[str, Any]]: The parsed JSON data as a dictionary, or None if the line is empty or meta.
    """
    line = line.lstrip("\ufeff").lstrip("ï»¿").strip()
    if not line or line.startswith(SseEvent.PREFIX) or line.startswith(":"):
        return None
    
    if line.startswith(SseData.PREFIX):
        data = line[len(SseData.PREFIX):].strip()
        if data == "[DONE]":
            return {"done": True}
        
        try:
            json_data = json.loads(data)
            # Unwrap chat_completion if present (Elastic Inference API nesting)
            if isinstance(json_data, dict) and "chat_completion" in json_data:
                return json_data["chat_completion"]
            return json_data
        except json.JSONDecodeError:
            return None
    
    return None


def _parse_tool_args(args: str) -> Dict[str, Any]:
    """Parse tool arguments from a string, handling potential LLM errors.

    Args:
        args: The arguments string to parse.

    Returns:
        Dict[str, Any]: The parsed arguments as a dictionary.
    """
    if not args or not args.strip():
        return {}
    
    args = args.strip()
    try:
        return json.loads(args)
    except json.JSONDecodeError:
        # Try to parse just the first object if there's extra data
        try:
            decoder = json.JSONDecoder()
            res, _ = decoder.raw_decode(args)
            return res if isinstance(res, dict) else {}
        except (json.JSONDecodeError, ValueError):
            return {}


async def _load_tools_safe() -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """Safely load tools and return them or an error dict.

    Returns:
        Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]: A tuple containing the tools list 
            and a result dict (either reasoning message or error info).
    """
    try:
        is_first_load = _tools_cache is None
        tools = await _get_mcp_tools()
        return tools, {"reasoning": f"Initialized agent with {len(tools)} tools"} if is_first_load else None
    except McpConnectionError as e:
        return None, {"error": {"message": str(e), "type": "mcp_connection_error"}}
    except McpError as e:
        return None, {"error": {"message": str(e), "type": "mcp_error"}}
    except Exception as e:
        return None, {"error": {"message": f"Unexpected error: {str(e)}", "type": "internal_error"}}


def _extract_error_message(e: Exception) -> str:
    """Extract a human-readable error message from an exception, especially HTTPError."""
    error_msg = str(e)
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        try:
            # Try to parse JSON error from ES
            response_json = e.response.json()
            if isinstance(response_json, dict) and "error" in response_json:
                error_obj = response_json["error"]
                if isinstance(error_obj, dict) and "message" in error_obj:
                        error_msg = error_obj["message"]
                elif isinstance(error_obj, str):
                        error_msg = error_obj
                else:
                        error_msg = json.dumps(error_obj)
            else:
                error_msg = e.response.text
        except Exception:
            if e.response.text:
                error_msg = e.response.text

    if error_msg:
        # Strip BOM
        error_msg = error_msg.lstrip("\ufeff").lstrip("ï»¿").strip()
        
        # Parse SSE format if present
        if "data:" in error_msg:
            try:
                for line in error_msg.splitlines():
                    line = line.strip()
                    if line.startswith("data:"):
                        data_json = line[len("data:"):].strip()
                        error_json = json.loads(data_json)
                        if isinstance(error_json, dict) and "error" in error_json:
                            inner_error = error_json["error"]
                            if isinstance(inner_error, dict) and "message" in inner_error:
                                error_msg = inner_error["message"]
                            elif isinstance(inner_error, str):
                                error_msg = inner_error
                            break
            except:
                pass

        # Clean up common nested error wrappers
        if "The model returned the following errors:" in error_msg:
            match = re.search(r"Error message: \[(.*?)\]", error_msg)
            if match:
                error_msg = match.group(1)
    
    return error_msg


def _recover_from_400(messages: List[Dict[str, Any]], error_msg: str) -> List[Dict[str, Any]]:
    """Attempt to sanitize message history after a 400 error.
    
    This usually involves finding the last assistant message with tool calls
    and either fixing it or removing the tool calls that caused the error.
    """
    # Find the last assistant message with tool calls
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("role") == "assistant" and "tool_calls" in messages[i]:
            # Found it. Now let's look for tool errors in the following messages.
            tool_errors = []
            for j in range(i + 1, len(messages)):
                if messages[j].get("role") == "tool":
                    content = messages[j].get("content", "")
                    if content.startswith("Error:"):
                        tool_errors.append(content)
            
            # Sanitization: Create a copy of the history up to the problematic turn
            new_messages = messages[:i+1].copy()
            
            # Remove tool calls from the assistant message in our new history
            assistant_msg = new_messages[i].copy()
            if "tool_calls" in assistant_msg:
                del assistant_msg["tool_calls"]
            
            # If the assistant message is now empty (no content and no tool_calls),
            # provide a placeholder so it's a valid message.
            if not assistant_msg.get("content") and not assistant_msg.get("reasoning"):
                assistant_msg["content"] = "(The model attempted an invalid tool call)"
            
            new_messages[i] = assistant_msg
            
            # Construct a recovery prompt for the model
            recovery_prompt = f"The previous request was rejected with a 400 Bad Request error from the server."
            if tool_errors:
                recovery_prompt += f" Before the rejection, these tool execution errors occurred:\n" + "\n".join(tool_errors)
            
            recovery_prompt += f"\n\nSpecific server error: {error_msg}\n\nThis usually means the previous tool calls were invalid. Please try again with a different approach or corrected tool parameters."
            
            new_messages.append({
                "role": "user",
                "content": recovery_prompt
            })
            return new_messages
            
    # If we couldn't find an assistant message with tool calls, 
    # just add the error as a user message at the end, carefully.
    error_prompt = f"The previous request resulted in a 400 Bad Request error. Specific error: {error_msg}. Please try a different approach."
    
    if messages and messages[-1].get("role") == "user":
        # Prepend to the existing user message content
        messages[-1]["content"] = f"NOTE: The previous attempt failed with a 400 error: {error_msg}\n\n" + messages[-1].get("content", "")
    else:
        messages.append({
            "role": "user",
            "content": error_prompt
        })
    return messages


async def _handle_llm_error(e: Exception) -> Generator[SseMessage, None, None]:
    """Handle LLM errors and yield appropriate SSE events.

    Args:
        e: The exception that occurred during the LLM call.

    Yields:
        SseMessage: SSE data or event messages reporting the error.
    """
    status_code = None
    if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
        status_code = e.response.status_code
        
    error_msg = _extract_error_message(e)

    # Log the failure in the stream
    yield SseData({
        "event": "round_info",
        "data": {"status": "failed"}
    })
    yield SseData({
        "event": "step_failure",
        "data": {
            "error": error_msg,
            "status_code": status_code
        }
    })
    
    # Send the final error event
    error_data = {
        "error": {
            "message": error_msg,
            "type": "llm_error",
            "status_code": status_code
        }
    }
    yield SseEvent("error")
    yield SseData(error_data)
    
    # Terminate on specific status codes or all errors
    return


async def _process_llm_response(
    es_response, 
    inference_id: str, 
    stats: Dict[str, Any],
    start_time_ms: float,
    result_container: Dict[str, Any],
    session_id: Optional[str] = None
) -> Generator[SseMessage, None, None]:
    """Process streaming response from LLM and update stats.

    Args:
        es_response: The streaming response from the LLM.
        inference_id: The ID of the inference endpoint used.
        stats: Dictionary containing tracking stats for the agent loop.
        start_time_ms: The start time of the agent loop in milliseconds.
        result_container: Dictionary used to store accumulated results (content, reasoning, tool_calls).
        session_id: Optional session ID used to check for cancellation mid-stream.

    Yields:
        SseMessage: SSE data messages representing chunks of the LLM response.
    """
    accumulated_content = []
    accumulated_reasoning = []
    tool_calls_buffer = {}
    
    for line in es_response:
        await asyncio.sleep(0)

        # Check for cancellation on every chunk — this is the only place we can interrupt
        # a live LLM stream mid-flight.
        if session_id and check_cancellation(session_id):
            result_container["cancelled"] = True
            break

        if not line:
            continue
        
        json_data = _parse_stream_chunk(line)
        if not json_data:
            continue
        if json_data.get("done"):
            break
        
        # Track first token time
        if stats["first_token_ms"] is None:
            stats["first_token_ms"] = time.time() * 1000 - start_time_ms
        
        stats["last_token_ms"] = time.time() * 1000 - start_time_ms

        # Yield model_usage if present
        if json_data.get("usage"):
            usage = json_data["usage"]
            stats["total_input_tokens"] += usage.get("prompt_tokens", 0)
            stats["total_output_tokens"] += usage.get("completion_tokens", 0)
            
            model_usage = {
                "inference_id": inference_id,
                "llm_calls": stats["llm_calls"],
                "input_tokens": stats["total_input_tokens"],
                "output_tokens": stats["total_output_tokens"]
            }
            yield SseData({
                "event": "model_usage",
                "data": model_usage
            })
        
        choices = json_data.get("choices") or []
        if not choices:
            continue
            
        choice = choices[0]
        delta = choice.get("delta", {})
        
        if "content" in delta and delta["content"]:
            accumulated_content.append(delta["content"])
            yield SseData({
                "event": "round",
                "data": {"message": delta["content"]}
            })
        
        reasoning_delta = delta.get("reasoning_content") or delta.get("reasoning")
        if reasoning_delta:
            accumulated_reasoning.append(reasoning_delta)
            yield SseData({
                "event": "reasoning",
                "data": {"reasoning": reasoning_delta}
            })
        
        if "tool_calls" in delta:
            for tc in delta["tool_calls"]:
                idx = tc.get("index", 0)
                if idx not in tool_calls_buffer:
                    tool_calls_buffer[idx] = {
                        "id": tc.get("id", ""),
                        "type": "function",
                        "function": {"name": "", "arguments": ""}
                    }
                if "id" in tc:
                    tool_calls_buffer[idx]["id"] = tc["id"]
                if "function" in tc:
                    if "name" in tc["function"]:
                        tool_calls_buffer[idx]["function"]["name"] = tc["function"]["name"]
                    if "arguments" in tc["function"]:
                        tool_calls_buffer[idx]["function"]["arguments"] += tc["function"]["arguments"]
    
    # Process tool calls
    tool_calls = []
    seen_ids = set()
    if tool_calls_buffer:
        for idx in sorted(tool_calls_buffer.keys()):
            tc = tool_calls_buffer[idx]
            
            # Skip if ID is missing or duplicate
            tc_id = tc["id"]
            if not tc_id or tc_id in seen_ids:
                continue
            seen_ids.add(tc_id)
            
            args = tc["function"]["arguments"] or "{}"
            tool_calls.append({
                "id": tc_id,
                "type": "function",
                "function": {"name": tc["function"]["name"], "arguments": args}
            })
            yield SseData({
                "event": "tool_call",
                "data": {
                    "tool_id": tc["function"]["name"],
                    "tool_call_id": tc_id,
                    "params": _parse_tool_args(args)
                }
            })
    
    result_container["content"] = accumulated_content
    result_container["reasoning"] = accumulated_reasoning
    result_container["tool_calls"] = tool_calls


async def _execute_tool_calls(
    tool_calls: List[Dict[str, Any]], 
    messages: List[Dict[str, Any]]
) -> Generator[SseMessage, None, None]:
    """Execute tool calls in parallel and yield results.

    Args:
        tool_calls: List of tool calls to execute.
        messages: The message history to update with tool results.

    Yields:
        SseMessage: SSE data messages representing tool results or errors.

    Raises:
        McpConnectionError: If connection to the MCP server fails during execution.
    """
    async def run_tool(tool_call):
        tool_name = tool_call["function"]["name"]
        args_str = tool_call["function"]["arguments"]
        tool_args = _parse_tool_args(args_str)
            
        try:
            result = await _call_mcp_tool(tool_name, tool_args)
            return {
                "role": "tool",
                "content": result if isinstance(result, str) else json.dumps(result),
                "tool_call_id": tool_call["id"],
                "status": "success",
                "result_data": result
            }
        except McpConnectionError as e:
            return {
                "status": "mcp_connection_error",
                "error_msg": str(e),
                "tool_call_id": tool_call["id"]
            }
        except Exception as e:
            return {
                "role": "tool",
                "content": f"Error: {str(e)}",
                "tool_call_id": tool_call["id"],
                "status": "error",
                "error_msg": str(e)
            }

    # Run tools in parallel
    tasks = [run_tool(tc) for tc in tool_calls]
    
    # Process results as they complete
    for future in asyncio.as_completed(tasks):
        res = await future
        
        if res["status"] == "mcp_connection_error":
            error_msg = f"MCP Connection Error: {res['error_msg']}"
            yield SseData({
                "event": "tool_result",
                "data": {
                    "tool_call_id": res["tool_call_id"],
                    "type": "error",
                    "data": {"message": error_msg}
                }
            })
            
            error_data = {"error": {"message": error_msg, "type": "mcp_connection_error"}}
            yield SseEvent("error")
            yield SseData(error_data)
            # Stop execution on connection error
            raise McpConnectionError(error_msg)
            
        # Add to messages
        messages.append({
            "role": res["role"],
            "content": res["content"],
            "tool_call_id": res["tool_call_id"]
        })
        
        if res["status"] == "success":
            result = res["result_data"]
            result_type = "data" if isinstance(result, (dict, list)) else "success"
            yield SseData({
                "event": "tool_result",
                "data": {
                    "tool_call_id": res["tool_call_id"],
                    "type": result_type,
                    "data": {"result": result}
                }
            })
        else:
            yield SseData({
                "event": "tool_result",
                "data": {
                    "tool_call_id": res["tool_call_id"],
                    "type": "error",
                    "data": {"message": res["error_msg"]}
                }
            })


async def _agent_loop_stream(
    messages: List[Dict[str, Any]],
    inference_id: str = ".rainbow-sprinkles-elastic",
    max_turns: int = 200,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    session_id: str = None,
    conversation_id: str = None,
    original_rounds: List[Dict[str, Any]] = None
):
    """Streaming agent loop that handles tool calling and yields response lines.

    Args:
        messages: The conversation history in messages format.
        inference_id: The ID of the inference endpoint to use.
        max_turns: Maximum number of tool-calling iterations.
        max_retries: Maximum number of retries for transient LLM errors.
        retry_delay: Initial delay between retries in seconds.
        session_id: Session ID for cancellation tracking.
        conversation_id: Conversation ID for saving state.
        original_rounds: Original rounds structure to update (not reconstruct).

    Yields:
        str: Raw ES response lines or error events in SSE format.
    """
    
    # Keep track of rounds for saving
    rounds_for_save = original_rounds if original_rounds else []
    
    # Set initial status to running if we have rounds
    if rounds_for_save and len(rounds_for_save) > 0:
        rounds_for_save[-1]["status"] = "running"
    
    # Get available MCP tools
    tools, load_result = await _load_tools_safe()
    if not tools and load_result and "error" in load_result:
        yield SseEvent("error")
        yield SseData(load_result)
        return
    
    if load_result and "reasoning" in load_result:
         yield SseData({
             "event": "reasoning",
             "data": load_result
         })
    
    # Agent loop stats
    stats = {
        "llm_calls": 0,
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "first_token_ms": None,
        "last_token_ms": None
    }
    
    start_time_iso = datetime.now(timezone.utc).isoformat()
    start_time_ms = time.time() * 1000

    yield SseData({
        "event": "round_info",
        "data": {
            "started_at": start_time_iso,
            "status": "running"
        }
    })

    # Wrap main loop in GeneratorExit handler for client disconnect
    was_cancelled = False
    try:
        for turn in range(max_turns):
            # Check for cancellation before each turn
            if session_id and check_cancellation(session_id):
                yield SseData({
                    "event": "reasoning",
                    "data": {"reasoning": "Agent stopped by user."}
                })
                was_cancelled = True
                break
            
            # Call LLM with current messages
            stats["llm_calls"] += 1
            es_response = None
            
            for attempt in range(max_retries + 1):
                try:
                    es_response = _chat_stream(messages, inference_id, tools if tools else None)
                    break # Success
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if e.response is not None else None
                    # Retry on 429 (Rate Limit) or 5xx (Server Error)
                    if attempt < max_retries and status_code in (429, 500, 502, 503, 504):
                        wait_time = retry_delay * (2 ** attempt) # Exponential backoff
                        yield SseData({
                            "event": "reasoning",
                            "data": {"reasoning": f"Transient error {status_code}. Retrying in {wait_time:.1f}s (attempt {attempt + 1}/{max_retries})..."}
                        })
                        await asyncio.sleep(wait_time)
                        continue
                    
                    # Handle 400 specifically to allow the agent to recover
                    if status_code == 400 and attempt < max_retries:
                        error_msg = _extract_error_message(e)
                        yield SseData({
                            "event": "reasoning",
                            "data": {"reasoning": f"Received a 400 Bad Request from the Inference API. Attempting to recover by sanitizing history and retrying. Error: {error_msg}"}
                        })
                        messages = _recover_from_400(messages, error_msg)
                        continue

                    # Non-transient or exhausted retries
                    async for event in _handle_llm_error(e):
                        yield event
                    return
                except Exception as e:
                    async for event in _handle_llm_error(e):
                        yield event
                    return
            
            if not es_response:
                return
                
            # Process the stream
            result_container = {}
            async for event in _process_llm_response(es_response, inference_id, stats, start_time_ms, result_container, session_id=session_id):
                yield event

            # If cancelled mid-stream, save state and stop
            if result_container.get("cancelled"):
                if conversation_id and rounds_for_save:
                    rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
                    rounds_for_save[-1]["status"] = "cancelled"
                    _apply_stats_to_round(rounds_for_save, stats, inference_id)
                    await _save_conversation_async(conversation_id, rounds_for_save, final=True)
                was_cancelled = True
                break
                
            accumulated_content = result_container.get("content", [])
            accumulated_reasoning = result_container.get("reasoning", [])
            tool_calls = result_container.get("tool_calls", [])

            # Add assistant message with tool calls to history
            if accumulated_content or accumulated_reasoning or tool_calls:
                assistant_message = {"role": "assistant"}
                if accumulated_content:
                    assistant_message["content"] = "".join(accumulated_content)
                if accumulated_reasoning:
                    assistant_message["reasoning"] = "".join(accumulated_reasoning)
                if tool_calls:
                    assistant_message["tool_calls"] = tool_calls
                messages.append(assistant_message)
                
                # Save conversation state after LLM response
                if conversation_id and rounds_for_save:
                    rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
                    rounds_for_save[-1]["status"] = "running"  # Still working
                    _apply_stats_to_round(rounds_for_save, stats, inference_id)
                    await _save_conversation_async(conversation_id, rounds_for_save, final=False)
                
            # Execute tool calls
            if tool_calls:
                try:
                    async for event in _execute_tool_calls(tool_calls, messages):
                        # Check for cancellation during tool execution
                        if session_id and check_cancellation(session_id):
                            yield SseData({
                                "event": "reasoning",
                                "data": {"reasoning": "Agent stopped by user."}
                            })
                            # Save current state before stopping
                            if conversation_id and rounds_for_save:
                                rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
                                rounds_for_save[-1]["status"] = "cancelled"
                                _apply_stats_to_round(rounds_for_save, stats, inference_id)
                                await _save_conversation_async(conversation_id, rounds_for_save, final=True)
                            return
                        yield event
                    
                    # Save conversation state after tool execution
                    if conversation_id and rounds_for_save:
                        rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
                        rounds_for_save[-1]["status"] = "running"  # Still working
                        _apply_stats_to_round(rounds_for_save, stats, inference_id)
                        await _save_conversation_async(conversation_id, rounds_for_save, final=False)
                        
                except McpConnectionError:
                    # Save state before returning on connection error
                    if conversation_id and rounds_for_save:
                        rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
                        rounds_for_save[-1]["status"] = "failed"  # Connection error
                        _apply_stats_to_round(rounds_for_save, stats, inference_id)
                        await _save_conversation_async(conversation_id, rounds_for_save, final=True)
                    return
            else:
                # No tool calls, we're done with this round
                break
        else:
            # Hit max_turns
            yield SseData({
                "event": "reasoning",
                "data": {"reasoning": f"Agent reached maximum number of turns ({max_turns}) and stopped to prevent a potential loop."}
            })
    
    except GeneratorExit:
        # Client disconnected (user cancelled and aborted the stream)
        print(f"Client disconnected from session {session_id}, saving state as cancelled...")
        if conversation_id and rounds_for_save:
            rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
            rounds_for_save[-1]["status"] = "cancelled"
            _apply_stats_to_round(rounds_for_save, stats, inference_id)
            await _save_conversation_async(conversation_id, rounds_for_save, final=True)
        raise  # Re-raise to properly close the generator
        
    except Exception as e:
        # Unexpected error in the loop logic itself
        error_msg = f"Internal Agent Error: {str(e)}"
        yield SseData({
            "event": "step_failure",
            "data": {"error": error_msg}
        })
        yield SseEvent("error")
        yield SseData({"error": {"message": error_msg, "type": "internal_error"}})
        return

    # Final round info
    if stats["last_token_ms"] is None:
        stats["last_token_ms"] = time.time() * 1000 - start_time_ms

    round_info = {
        "status": "cancelled" if was_cancelled else "completed",
        "time_to_first_token": int(stats["first_token_ms"]) if stats["first_token_ms"] is not None else 0,
        "time_to_last_token": int(stats["last_token_ms"])
    }
    yield SseData({
        "event": "round_info",
        "data": round_info
    })
    
    # Final save with refresh=True for searchability
    if conversation_id and rounds_for_save:
        rounds_for_save = _update_current_round_from_messages(rounds_for_save, messages[1:])
        # Set appropriate status based on how the agent finished
        if was_cancelled:
            rounds_for_save[-1]["status"] = "cancelled"
        else:
            rounds_for_save[-1]["status"] = "completed"
        _apply_stats_to_round(rounds_for_save, stats, inference_id)
        await _save_conversation_async(conversation_id, rounds_for_save, final=True)
    
    # Clean up cancellation token
    if session_id:
        cleanup_cancellation_token(session_id)

def _build_messages_from_rounds(rounds: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert conversation rounds into a list of message dictionaries.

    Args:
        rounds: List of conversation rounds to convert.

    Returns:
        List[Dict[str, Any]]: List of messages formatted for the LLM.
    """
    messages = []
    for r in rounds:
        # Add user input
        if "input" in r and "message" in r["input"]:
            messages.append({"role": "user", "content": r["input"]["message"]})
        
        # Add assistant response and steps
        assistant_msg = {"role": "assistant"}
        if "response" in r and "message" in r["response"]:
            assistant_msg["content"] = r["response"]["message"]
        
        tool_calls = []
        for step in r.get("steps", []):
            step_type = step.get("type")
            if step_type == "tool_call":
                tool_calls.append({
                    "id": step["tool_call_id"],
                    "type": "function",
                    "function": {
                        "name": step["tool_id"],
                        "arguments": json.dumps(step.get("params", {}))
                    }
                })
            elif step_type == "reasoning":
                assistant_msg["reasoning"] = (assistant_msg.get("reasoning") or "") + (step.get("reasoning") or "")
        
        if tool_calls:
            assistant_msg["tool_calls"] = tool_calls
        
        # Only add assistant message if it has non-empty content or tool_calls.
        # Reasoning-only assistant messages are not sent to the Inference API and can
        # collapse into invalid empty-content assistant turns after sanitization.
        has_content = assistant_msg.get("content") and assistant_msg["content"].strip()
        if has_content or tool_calls:
            messages.append(assistant_msg)
        
        # Add tool results
        for step in r.get("steps", []):
            step_type = step.get("type")
            if (step_type == "tool_call" or step_type == "tool_result") and "results" in step:
                results = step["results"]
                if not results:
                    continue
                
                # If there are multiple results for one tool call, merge them to avoid duplicate tool_call_id messages
                if len(results) == 1:
                    content = json.dumps(results[0].get("data", {}))
                else:
                    merged_data = [res.get("data", {}) for res in results]
                    content = json.dumps(merged_data)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": step["tool_call_id"],
                    "content": content
                })
    return messages


def _prepare_system_prompt(ui_context: Optional[Dict[str, Any]] = None) -> str:
    """Prepare the system prompt with optional UI context.

    Args:
        ui_context: Optional dictionary containing UI context to include in the prompt.

    Returns:
        str: The full system prompt string.
    """
    full_system_prompt = SYSTEM_PROMPT
    if ui_context:
        full_system_prompt += f"\n\n## UI Context\n\n{json.dumps(ui_context, indent=2, sort_keys=True)}"
    return full_system_prompt


def _run_sync_generator_from_async(async_gen_func) -> Generator[Any, None, None]:
    """Run an async generator in a synchronous generator wrapper.

    Args:
        async_gen_func: A callable that returns an async generator.

    Yields:
        Any: Chunks yielded by the async generator.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        async_gen = async_gen_func()
        while True:
            try:
                yield loop.run_until_complete(async_gen.__anext__())
            except StopAsyncIteration:
                break
    finally:
        loop.close()


def _sanitize_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sanitize messages by filtering invalid roles and fields.
    
    Args:
        messages: List of message dictionaries.
        
    Returns:
        List[Dict[str, Any]]: List of sanitized messages.
    """
    sanitized = []
    for msg in messages:
        role = msg.get("role")
        if role not in ("user", "assistant", "tool"):
            continue
            
        new_msg = {"role": role}
        
        if role == "user":
            if "content" in msg:
                new_msg["content"] = msg["content"]
            if "name" in msg:
                new_msg["name"] = msg["name"]
                
        elif role == "assistant":
            if "content" in msg:
                new_msg["content"] = msg["content"]
            if "tool_calls" in msg:
                new_tool_calls = []
                for tc in msg["tool_calls"]:
                    new_tc = {}
                    if "id" in tc:
                        new_tc["id"] = tc["id"]
                    if "type" in tc:
                        new_tc["type"] = tc["type"]
                    if "function" in tc:
                        new_func = {}
                        if "name" in tc["function"]:
                            new_func["name"] = tc["function"]["name"]
                        if "arguments" in tc["function"]:
                            new_func["arguments"] = tc["function"]["arguments"]
                        new_tc["function"] = new_func
                    new_tool_calls.append(new_tc)
                new_msg["tool_calls"] = new_tool_calls

            # Skip assistant messages that have neither meaningful content nor tool calls.
            # The Inference API rejects assistant messages with missing/empty content.
            has_content = isinstance(new_msg.get("content"), str) and bool(new_msg["content"].strip())
            has_tool_calls = bool(new_msg.get("tool_calls"))
            if not has_content and not has_tool_calls:
                continue

        elif role == "tool":
            if "content" in msg:
                new_msg["content"] = msg["content"]
            if "tool_call_id" in msg:
                new_msg["tool_call_id"] = msg["tool_call_id"]
                
        sanitized.append(new_msg)
        
    return sanitized


def chat(text: str = "", rounds: List[Dict[str, Any]] = None, inference_id=".rainbow-sprinkles-elastic", ui_context: Optional[Dict[str, Any]] = None, id: str = None, conversation_id: str = None, session_id: str = None) -> Generator[str, None, None]:
    """Perform a streaming chat completion with agentic behavior and MCP tool calling.

    Args:
        text: The user's input text (used if rounds is None).
        rounds: Optional list of conversation rounds.
        inference_id: The ID of the inference endpoint to use.
        ui_context: Optional arbitrary dictionary containing UI context.
        conversation_id: Conversation ID (same as id).
        session_id: Optional session ID for cancellation tracking. Generated if not provided.

    Yields:
        Raw ES response lines in SSE format.
    """
    # Generate session_id if not provided
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if rounds:
        messages = _build_messages_from_rounds(rounds)
    else:
        messages = [{"role": "user", "content": text}]
    
    # Filter out any messages where role is neither "user" nor "assistant" nor "tool"
    # and filter out fields that aren't valid for each role.
    messages = _sanitize_messages(messages)
    
    # Prepend the system prompt
    full_system_prompt = _prepare_system_prompt(ui_context)
    messages.insert(0, {"role": "system", "content": full_system_prompt})
    
    async def run_async_stream():
        try:
            # Emit session_started event with session_id
            yield SseData({
                "event": "session_started",
                "data": {"session_id": session_id}
            })
            
            # Emit conversation_id_set event if IDs are provided
            if conversation_id:
                yield SseData({
                    "event": "conversation_id_set",
                    "data": {"conversation_id": conversation_id}
                })
            
            async for line in _agent_loop_stream(
                messages, 
                inference_id,
                session_id=session_id,
                conversation_id=conversation_id,
                original_rounds=rounds
            ):
                yield line
        except GeneratorExit:
            # Client disconnected - cleanup handled in agent loop
            print(f"Client disconnected from session {session_id}")
            raise
        finally:
            # Always clean up cancellation token
            cleanup_cancellation_token(session_id)
    
    return _run_sync_generator_from_async(run_async_stream)

def endpoints() -> List[Dict[str, Any]]:
    """List all chat_completion inference endpoints.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing chat_completion endpoints.
    """
    es_response = es("studio").inference.get()
    response = []
    for endpoint in es_response.get("endpoints", []):
        if endpoint["task_type"] == "chat_completion":
            response.append(endpoint)
    return response
