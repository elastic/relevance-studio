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
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional, Tuple

# Third-party packages
import requests
from fastmcp.client import Client

# App packages
from .. import utils
from ..client import es, ELASTICSEARCH_API_KEY, ELASTICSEARCH_USERNAME, ELASTICSEARCH_PASSWORD

# MCP server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL") or "http://127.0.0.1:4200/mcp"
MCP_ENABLED = True

# MCP tools cache
_tools_cache = None
_tools_lock = None

# Agent configuration
SYSTEM_PROMPT = """
You are an expert in search relevance engineering and Elasticsearch.
You are helping a search engineer who is using Elasticsearch Relevance Studio.

Elasticsearch Relevance Studio is an application that manages the lifecycle of
search relevance engineering in Elasticsearch. Generally, its goal is to help
people deliver amazing search experiences by guiding them in the best practices
of search relevance engineering. That means defining scenarios, curating
judgements, building strategies, and benchmarking their performance.

## Studio deployment data assets

- **conversations** - A global list of chat history between the user and the agent.
- **workspaces** - A namespace for all other assets whose workspace_id matches the workspace _id.
- **displays** - A markdown template to render documents from specific indices in the **UI**.
- **scenarios** - A search input (e.g. "brown oxfords")
- **judgements** - A rating for a given document from a given index for a given scenario.
- **strategies** - An Elasticsearch search template whose params are supplied by scenario values.
- **benchmarks** - A reusable task definition for evaluations.
- **evaluations** - The results of a gridded rank evaluation.

## General workflow

Here is the typical workflow of the application:

1. Select a workspace to work in.
    - A workspace _id is a UUID. If you don't have a workspace _id, ask or search for it.
    - Take note of "_id", "name", "index_pattern", "rating_scale", and "params".
2. Use displays to control the retrieval and display of documents from indices in the content deployment.
    - "index_pattern" is the Elasticsearch index pattern that the display. When multiple displays have overlapping "index_pattern" values, the more specific matching pattern should be used.
    - "fields" lists the fields that should be in the _source.includes of all searches to that index pattern.
    - "template.image.url" is an image for the document. It might contain mustache variables, which should be replaced by their respective values from "fields".
3. Define a diverse set of scenarios that are representative of the use case.
4. Curate judgements for each scenario using the workspace rating scale.
    - "rating_scale_max" represents superb relevance.
    - "rating_scale.min" represents complete irrelevance.
    - "index" in judgements is the index of the doc being rated.
    - "doc_id" in judgements is the _id of the doc being rated.
5. Build strategies that attempt to maximize search relevance.
    - Strategies are the bodies of Elasticsearch Search API, which is a "query" or "retriever".
    - Strategies must implement at least one of the params from the workspace in the form of a Mustache variables. Example: "{{ text }}"
6. Define benchmarks.
7. Run evaluations for a benchmark.
    - A worker process will execute these asynchronously. It may take seconds or minutes to complete.
8. Analyze the results of the evaluations.
    - The "summary" field summarizes the relevance metrics for each strategy_id or strategy_tag.
9. Find ways to enhance the process, such as:
    - Creating scenarios that would be valuable to include in benchmarks;
    - Adjusting the tags of scenarios or strategies;
    - Setting the ratings of documents that should be judged;
    - Changing or unsetting the ratings of judgements that might be inaccurate;
    - Enhancing the query logic of strategies; and
    - Re-running evaluations, analyzing their results, and repeating the workflow.

## Instructions

You are an expert in Elasticsearch and search relevance engineering.

You automate the management of resources and evaluations in Relevance Studio.

You must adhere to the following requirements and best practices:

## Requirements

### 1. Always scope operations on studio assets by workspace_id

All operations on **studio deployment data assets** (except conversations) must be scoped to a workspace.
If I ask you to perform a search, create, update, set, unset, or delete on
displays, scenarios, judgements, strategies, benchmarks or evaluations, pass the
workspace_id that you're currently working on as an argument to that function.

If you aren't working on a workspace or you forgot which one it was, ask me for
clarification on which workspace you should be using. If I give you an _id
(which is a UUID), then use that as the workspace_id. If I give you a name or a
description instead, then search for the workspace that best matches it and use
that _id. If there are no good matches, let me know, and don't perform the
operation.

### 2. Always fetch displays before searching or judging documents from the content deployment

Fetch all displays for the workspace before searching or judging documents from
the content deployment. Use the display whose index_pattern best matches the
index of the documents that you will be searching or judging. If there is a
matching display, use the values of its "fields" as the values of
_source.includes in your searches. This will make searching much more efficient.
If thers is no matching display, then don't set the value of _source.includes
in your searches.

In other words, always ensure you have tried fetching displays with the
displays_search tool before using either the content_search tool or the
judgements_search tool.

## Best Practices

### Analyze images when judging documents

When judging documents that have a display template, check to see if the
display defines an image URL template, which you can reconstruct by replacing
mustache variables with fields from the document. You can use the
get_base64_image_from_url tool to fetch that image in a small, base64-encoded
format. This can be a great signal for relevance.

### Other requirements

Don't make up fictional values for any "_id" or "doc_id" field of any asset.
Look them up if needed.

## Responses

## Navigation & Hyperlinks

Help the user navigate by creating markdown links to specific pages. All internal links MUST use the hash-based URL format: `{origin}/#/{path}`.

When you have access to IDs (like `workspace_id`, `strategy_id`, etc.) from the conversation context or tools, use them to construct these links.

### Available URL Patterns:

- **Home**: `{base_url}/#/`
- **Workspaces (all)**: `{base_url}/#/workspaces`
- **Workspace**: `{base_url}/#/workspaces/{workspace_id}`
- **Displays (all)**: `{base_url}/#/workspaces/{workspace_id}/displays`
- **Display (editor)**: `{base_url}/#/workspaces/{workspace_id}/displays/{display_id}`
- **Judgements**: `{base_url}/#/workspaces/{workspace_id}/judgements`
- **Scenarios (all)**: `{base_url}/#/workspaces/{workspace_id}/scenarios`
- **Strategies (all)**: `{base_url}/#/workspaces/{workspace_id}/strategies`
- **Strategy (editor)**: `{base_url}/#/workspaces/{workspace_id}/strategies/{strategy_id}`
- **Benchmarks (all)**: `{base_url}/#/workspaces/{workspace_id}/benchmarks`
- **Benchmark**: `{base_url}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}`
- **Evaluation**: `{base_url}/#/workspaces/{workspace_id}/benchmarks/{benchmark_id}/evaluations/{evaluation_id}`

### Formatting Rules:
1. Use the `base_url` provided in the UI Context. If missing, omit it and assume the user is on the same origin as the application.
2. Ensure the `/#/` follows the base URL immediately.
3. Prefer to hyperlink the actual name or _id of the asset, rather than a call to action like "click here".

**Example**:
"I've finished running the [benchmark]({base_url}/#/workspaces/123/benchmarks/456/evaluations/789)."

## Images

When including images in Markdown, use URL references rather than base64 data URIs. Examples:

✓ ![alt](https://example.com/image.png)
✗ ![alt](data:image/png;base64,iVBORw0KGgo...)
 
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
        if "reasoning" in msg and msg["reasoning"]:
            sanitized_msg["reasoning"] = msg["reasoning"]
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
    
    # Return line iterator
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
    result_container: Dict[str, Any]
) -> Generator[SseMessage, None, None]:
    """Process streaming response from LLM and update stats.

    Args:
        es_response: The streaming response from the LLM.
        inference_id: The ID of the inference endpoint used.
        stats: Dictionary containing tracking stats for the agent loop.
        start_time_ms: The start time of the agent loop in milliseconds.
        result_container: Dictionary used to store accumulated results (content, reasoning, tool_calls).

    Yields:
        SseMessage: SSE data messages representing chunks of the LLM response.
    """
    accumulated_content = []
    accumulated_reasoning = []
    tool_calls_buffer = {}
    
    for line in es_response:
        await asyncio.sleep(0)
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
    retry_delay: float = 1.0
):
    """Streaming agent loop that handles tool calling and yields response lines.

    Args:
        messages: The conversation history in messages format.
        inference_id: The ID of the inference endpoint to use.
        max_turns: Maximum number of tool-calling iterations.
        max_retries: Maximum number of retries for transient LLM errors.
        retry_delay: Initial delay between retries in seconds.

    Yields:
        str: Raw ES response lines or error events in SSE format.
    """
    
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

    try:
        for turn in range(max_turns):
            # Call LLM with current messages
            stats["llm_calls"] += 1
            es_response = None
            
            for attempt in range(max_retries + 1):
                try:
                    import json
                    print(json.dumps(messages, indent=2))
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
            async for event in _process_llm_response(es_response, inference_id, stats, start_time_ms, result_container):
                yield event
                
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
                
            # Execute tool calls
            if tool_calls:
                try:
                    async for event in _execute_tool_calls(tool_calls, messages):
                        yield event
                except McpConnectionError:
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
        "status": "completed",
        "time_to_first_token": int(stats["first_token_ms"]) if stats["first_token_ms"] is not None else 0,
        "time_to_last_token": int(stats["last_token_ms"])
    }
    yield SseData({
        "event": "round_info",
        "data": round_info
    })

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
        
        # Only add assistant message if it has non-empty content, reasoning, or tool_calls
        has_content = assistant_msg.get("content") and assistant_msg["content"].strip()
        has_reasoning = assistant_msg.get("reasoning") and assistant_msg["reasoning"].strip()
        if has_content or has_reasoning or tool_calls:
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

        elif role == "tool":
            if "content" in msg:
                new_msg["content"] = msg["content"]
            if "tool_call_id" in msg:
                new_msg["tool_call_id"] = msg["tool_call_id"]
                
        sanitized.append(new_msg)
        
    return sanitized


def chat(text: str = "", rounds: List[Dict[str, Any]] = None, inference_id=".rainbow-sprinkles-elastic", ui_context: Optional[Dict[str, Any]] = None, id: str = None, conversation_id: str = None) -> Generator[str, None, None]:
    """Perform a streaming chat completion with agentic behavior and MCP tool calling.

    Args:
        text: The user's input text (used if rounds is None).
        rounds: Optional list of conversation rounds.
        inference_id: The ID of the inference endpoint to use.
        ui_context: Optional arbitrary dictionary containing UI context.
        conversation_id: Conversation ID (same as id).

    Yields:
        Raw ES response lines in SSE format.
    """
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
        # Emit conversation_id_set event if IDs are provided
        if conversation_id:
            yield SseData({
                "event": "conversation_id_set",
                "data": {"conversation_id": conversation_id}
            })
            
        async for line in _agent_loop_stream(messages, inference_id):
            yield line
    
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
