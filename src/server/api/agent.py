# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import asyncio
import json
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, Generator, List, Optional

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

## Application architecture

- **Studio deployment** - An Elasticsearch deployment that stores the assets created by the **server**.
- **Content deployment** - A Elasticsearch deployment that stores the documents that will be searched, judged, and used in rank evaluation.
- **Server** - A Flask server that handles API requests and interfaces with the **studio deployment** and **content deployment**.
- **MCP server** - A FastMCP server that handles MCP requests and interfaces with the **studio deployment** and **content deployment**.
- **Worker** - A background process that polls for pending evaluations in the **studio deployment**, runs them, and saves their results in the **studio deployment**.
- **UI** - A React application for the UX that interfaces with the **server**.

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
"""

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
    if hasattr(client.transport, '_client_meta') or hasattr(node, 'config'):
        # Try to get auth from node config
        if hasattr(node, 'config'):
            config = node.config
            if hasattr(config, 'api_key') and config.api_key:
                # Use API key in header
                headers['Authorization'] = f'ApiKey {config.api_key}'
            elif hasattr(config, 'basic_auth') and config.basic_auth:
                # Use basic auth tuple
                auth = config.basic_auth
    
    # Fallback: try to reconstruct from environment
    if not auth and not headers.get('Authorization'):
        if ELASTICSEARCH_API_KEY:
            headers['Authorization'] = f'ApiKey {ELASTICSEARCH_API_KEY}'
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
    base_url = base_url.rstrip('/')
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
        error_msg = f"ES Inference Error ({response.status_code}): {response.text}\n\nRequest body was: {body}"
        print(error_msg)
        response.raise_for_status()
    
    # Return line iterator
    line_iter = response.iter_lines(decode_unicode=True)
    return line_iter


async def _get_mcp_tools() -> List[Dict[str, Any]]:
    """Connect to MCP server and retrieve available tools.

    Returns:
        A list of tools in OpenAI function calling format.

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
    """Helper to perform the actual MCP tool loading."""
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
        The text content or string representation of the tool's result.

    Raises:
        McpConnectionError: If connection to the MCP server fails.
        McpError: If the tool call fails.
    """
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(tool_name, tool_args)
            
            # Extract text content from MCP response
            if hasattr(result, 'content') and result.content:
                # result.content is a list of ContentItem objects
                text_parts = []
                for item in result.content:
                    if hasattr(item, 'text'):
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
        The parsed JSON data as a dictionary, or None if the line is empty or meta.
    """
    line = line.strip()
    if not line or line.startswith('event:') or line.startswith(':'):
        return None
    
    if line.startswith('data:'):
        data = line[len('data:'):].strip()
        if data == '[DONE]':
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


async def _agent_loop_stream(
    messages: List[Dict[str, Any]],
    inference_id: str = ".rainbow-sprinkles-elastic",
    max_turns: int = 10
):
    """Streaming agent loop that handles tool calling and yields response lines.

    Args:
        messages: The conversation history in messages format.
        inference_id: The ID of the inference endpoint to use.
        max_turns: Maximum number of tool-calling iterations.

    Yields:
        str: Raw ES response lines or error events in SSE format.
    """
    
    # Get available MCP tools
    try:
        is_first_load = _tools_cache is None
        tools = await _get_mcp_tools()
        if is_first_load:
            yield f"data: {json.dumps({'event': 'reasoning', 'data': {'reasoning': f'Initialized agent with {len(tools)} tools'}})}\n\n"
    except McpConnectionError as e:
        error_data = {"error": {"message": str(e), "type": "mcp_connection_error"}}
        yield f"event: error\n"
        yield f"data: {json.dumps(error_data)}\n\n"
        return
    except McpError as e:
        error_data = {"error": {"message": str(e), "type": "mcp_error"}}
        yield f"event: error\n"
        yield f"data: {json.dumps(error_data)}\n\n"
        return
    except Exception as e:
        error_data = {"error": {"message": f"Unexpected error: {str(e)}", "type": "internal_error"}}
        yield f"event: error\n"
        yield f"data: {json.dumps(error_data)}\n\n"
        return
    
    # Agent loop
    llm_calls = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    start_time_iso = datetime.now(timezone.utc).isoformat()
    start_time_ms = time.time() * 1000
    first_token_ms = None
    last_token_ms = None

    yield f"data: {json.dumps({'event': 'round_info', 'data': {'started_at': start_time_iso, 'status': 'running'}})}\n\n"

    for turn in range(max_turns):
        # Call LLM with current messages
        llm_calls += 1
        try:
            es_response = _chat_stream(messages, inference_id, tools if tools else None)
        except Exception as e:
            yield f"data: {json.dumps({'event': 'round_info', 'data': {'status': 'failed'}})}\n\n"
            error_data = {"error": {"message": str(e), "type": "api_error"}}
            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"
            raise
        
        accumulated_content = []
        accumulated_reasoning = []
        tool_calls_buffer = {}
        
        # Stream ES response lines
        for line in es_response:
            await asyncio.sleep(0)
            if not line:
                continue
            
            # Parse for agent loop
            json_data = _parse_stream_chunk(line)
            if not json_data:
                continue
            if json_data.get("done"):
                break
            
            # Track first token time
            if first_token_ms is None:
                first_token_ms = time.time() * 1000 - start_time_ms
            
            last_token_ms = time.time() * 1000 - start_time_ms

            # Yield model_usage if present
            if json_data.get("usage"):
                usage = json_data["usage"]
                total_input_tokens += usage.get("prompt_tokens", 0)
                total_output_tokens += usage.get("completion_tokens", 0)
                
                model_usage = {
                    "inference_id": inference_id,
                    "llm_calls": llm_calls,
                    "input_tokens": total_input_tokens,
                    "output_tokens": total_output_tokens
                }
                yield f"data: {json.dumps({'event': 'model_usage', 'data': model_usage})}\n\n"
            
            choices = json_data.get("choices") or []
            if not choices:
                continue
                
            choice = choices[0]
            delta = choice.get("delta", {})
            
            if "content" in delta and delta["content"]:
                accumulated_content.append(delta["content"])
                yield f"data: {json.dumps({'event': 'round', 'data': {'message': delta['content']}})}\n\n"
            
            reasoning_delta = delta.get("reasoning_content") or delta.get("reasoning")
            if reasoning_delta:
                accumulated_reasoning.append(reasoning_delta)
                yield f"data: {json.dumps({'event': 'reasoning', 'data': {'reasoning': reasoning_delta}})}\n\n"
            
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
                    
                    # If the tool call is complete enough, yield it
                    if tool_calls_buffer[idx]["id"] and tool_calls_buffer[idx]["function"]["name"]:
                         # We yield it only once when it's just started or we can yield updates.
                         # For Kibana style, we yield when we have the ID and name.
                         pass

        # If we have tool calls, yield them and then execute
        if tool_calls_buffer:
            tool_calls = []
            for idx in sorted(tool_calls_buffer.keys()):
                tc = tool_calls_buffer[idx]
                args = tc["function"]["arguments"] or "{}"
                tool_calls.append({
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["function"]["name"], "arguments": args}
                })
                yield f"data: {json.dumps({'event': 'tool_call', 'data': {'tool_id': tc['function']['name'], 'tool_call_id': tc['id'], 'params': json.loads(args) if args else {}}})}\n\n"
            
            # Add assistant message with tool calls to history
            assistant_message = {"role": "assistant"}
            if accumulated_content:
                assistant_message["content"] = "".join(accumulated_content)
            if accumulated_reasoning:
                assistant_message["reasoning"] = "".join(accumulated_reasoning)
            assistant_message["tool_calls"] = tool_calls
            messages.append(assistant_message)
            
            # Execute tool calls
            for tool_call in tool_calls:
                tool_name = tool_call["function"]["name"]
                tool_args = json.loads(tool_call["function"]["arguments"])
                try:
                    result = await _call_mcp_tool(tool_name, tool_args)
                    tool_result_message = {
                        "role": "tool",
                        "content": result if isinstance(result, str) else json.dumps(result),
                        "tool_call_id": tool_call["id"]
                    }
                    messages.append(tool_result_message)
                    result_type = "data" if isinstance(result, (dict, list)) else "success"
                    yield f"data: {json.dumps({'event': 'tool_result', 'data': {'tool_call_id': tool_call['id'], 'type': result_type, 'data': {'result': result}}})}\n\n"
                except Exception as e:
                    tool_result_message = {
                        "role": "tool",
                        "content": f"Error: {str(e)}",
                        "tool_call_id": tool_call["id"]
                    }
                    messages.append(tool_result_message)
                    yield f"data: {json.dumps({'event': 'tool_result', 'data': {'tool_call_id': tool_call['id'], 'type': 'error', 'data': {'message': str(e)}}})}\n\n"
        else:
            # No tool calls, we're done with this round
            break

    # Final round info
    if last_token_ms is None:
        last_token_ms = time.time() * 1000 - start_time_ms

    round_info = {
        'status': 'completed',
        'time_to_first_token': int(first_token_ms) if first_token_ms is not None else 0,
        'time_to_last_token': int(last_token_ms)
    }
    yield f"data: {json.dumps({'event': 'round_info', 'data': round_info})}\n\n"

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
    # ... (conversion logic) ...
    messages = []
    # ...
    if rounds:
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
                    for res in step["results"]:
                        messages.append({
                            "role": "tool",
                            "tool_call_id": step["tool_call_id"],
                            "content": json.dumps(res.get("data", {}))
                        })
    else:
        messages = [{"role": "user", "content": text}]
    
    # Filter out any messages where role is neither "user" nor "assistant" nor "tool"
    messages = [m for m in messages if m.get("role") in ("user", "assistant", "tool")]
    
    # Prepend the system prompt
    full_system_prompt = SYSTEM_PROMPT
    if ui_context:
        full_system_prompt += f"\n\n## UI Context\n\n{json.dumps(ui_context, indent=2, sort_keys=True)}"
    messages.insert(0, {"role": "system", "content": full_system_prompt})
    
    async def run_async_stream():
        # Emit conversation_id_set event if IDs are provided
        if conversation_id:
            yield f"data: {json.dumps({'event': 'conversation_id_set', 'data': {'conversation_id': conversation_id}})}\n\n"
            
        async for line in _agent_loop_stream(messages, inference_id):
            yield line
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        async_gen = run_async_stream()
        while True:
            try:
                line = loop.run_until_complete(async_gen.__anext__())
                yield line
            except StopAsyncIteration:
                break
    finally:
        loop.close()

def endpoints() -> List[Dict[str, Any]]:
    """List all chat_completion inference endpoints.

    Returns:
        A list of dictionaries representing chat_completion endpoints.
    """
    es_response = es("studio").inference.get()
    response = []
    for endpoint in es_response.get("endpoints", []):
        if endpoint["task_type"] == "chat_completion":
            response.append(endpoint)
    return response
