# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import base64
import os
import sys
from io import BytesIO
from typing import Any, Dict, List, Optional

# Third-party packages
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.server.context import Context
from PIL import Image
from starlette.requests import Request
from starlette.responses import JSONResponse

# App packages
from . import api
from . import mcp_auth
from .mcp_auth_middleware import MCPAuthMiddleware
from .models import *
from .tls import get_tls_config

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

####  Application  #############################################################

mcp = FastMCP(name="Relevance Studio")
mcp.add_middleware(MCPAuthMiddleware())
    

####  API: Conversations  ######################################################

@mcp.tool(description=api.conversations.search.__doc__)
def conversations_search(
        ctx: Context,
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.conversations.search(text, filters, sort, size, page, aggs, user=user, es_client=es_client))

@mcp.tool(description=api.conversations.get.__doc__)
def conversations_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.conversations.get(_id, user=user, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.conversations.create.__doc__ + f"""\n
JSON schema for doc:\n\n{ConversationsCreate.model_input_json_schema()}
""")
def conversations_create(ctx: Context, doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.conversations.create(doc, _id, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.conversations.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{ConversationsUpdate.model_input_json_schema()}
""")
def conversations_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.conversations.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.conversations.delete.__doc__)
def conversations_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.conversations.delete(_id, user=user, es_client=es_client))


####  API: Workspaces  #########################################################

@mcp.tool(description=api.workspaces.search.__doc__)
def workspaces_search(
        ctx: Context,
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.workspaces.search(text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.workspaces.get.__doc__)
def workspaces_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.workspaces.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.workspaces.create.__doc__ + f"""\n
JSON schema for doc:\n\n{WorkspaceCreate.model_input_json_schema()}
""")
def workspaces_create(ctx: Context, doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.workspaces.create(doc, _id, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.workspaces.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{DisplayCreate.model_input_json_schema()}
""")
def workspaces_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.workspaces.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.workspaces.delete.__doc__)
def workspaces_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.workspaces.delete(_id, es_client=es_client))


####  API: Displays  ###########################################################

@mcp.tool(description=api.displays.search.__doc__)
def displays_search(
        ctx: Context,
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.displays.search(workspace_id, text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.displays.get.__doc__)
def displays_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.displays.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.displays.create.__doc__ + f"""\n
JSON schema for doc:\n\n{DisplayCreate.model_input_json_schema()}
""")
def displays_create(ctx: Context, doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.displays.create(doc, _id, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.displays.update.__doc__ + f"""\n
JSON schema for doc_partia:\n\n{DisplayUpdate.model_input_json_schema()}
""")
def displays_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.displays.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.displays.delete.__doc__)
def displays_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.displays.delete(_id, es_client=es_client))


####  API: Scenarios  ##########################################################

@mcp.tool(description=api.scenarios.search.__doc__)
def scenarios_search(
        ctx: Context,
        workspace_id: str,
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.search(workspace_id, text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.scenarios.tags.__doc__)
def scenarios_tags(ctx: Context, workspace_id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.tags(workspace_id, es_client=es_client))

@mcp.tool(description=api.scenarios.get.__doc__)
def scenarios_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.scenarios.create.__doc__ + f"""\n
JSON schema for doc:\n\n{ScenarioCreate.model_input_json_schema()}
""")
def scenarios_create(ctx: Context, doc: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.create(doc, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.scenarios.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{ScenarioUpdate.model_input_json_schema()}
""")
def scenarios_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.scenarios.delete.__doc__)
def scenarios_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.scenarios.delete(_id, es_client=es_client))


####  API: Judgements  #########################################################

@mcp.tool(description=api.judgements.search.__doc__)
def judgements_search(
        ctx: Context,
        workspace_id: str,
        scenario_id: str,
        index_pattern: str,
        query: Dict[str, Any] = {},
        query_string: str = "*",
        filter: str = None,
        sort: str = None,
        _source: Dict[str, Any] = None
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.judgements.search(workspace_id, scenario_id, index_pattern, query, query_string, filter, sort, _source, es_client=es_client))

@mcp.tool(description=api.judgements.set.__doc__)
def judgements_set(ctx: Context, workspace_id: str, scenario_id: str, index: str, doc_id: str, rating: int) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.judgements.set(workspace_id, scenario_id, index, doc_id, rating, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.judgements.unset.__doc__)
def judgements_unset(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.judgements.unset(_id, es_client=es_client))


####  API: Strategies  #########################################################

@mcp.tool(description=api.strategies.search.__doc__)
def strategies_search(
        ctx: Context,
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.search(workspace_id, text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.strategies.tags.__doc__)
def strategies_tags(ctx: Context, workspace_id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.tags(workspace_id, es_client=es_client))

@mcp.tool(description=api.strategies.get.__doc__)
def strategies_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.strategies.create.__doc__ + f"""\n
JSON schema for doc:\n\n{StrategyCreate.model_input_json_schema()}
""")
def strategies_create(ctx: Context, doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.create(doc, _id, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.strategies.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{StrategyUpdate.model_input_json_schema()}
""")
def strategies_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.strategies.delete.__doc__)
def strategies_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.strategies.delete(_id, es_client=es_client))


####  API: Benchmarks  #########################################################

@mcp.tool(description=api.benchmarks.search.__doc__)
def benchmarks_search(
        ctx: Context,
        workspace_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.search(workspace_id, text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.benchmarks.tags.__doc__)
def benchmarks_tags(ctx: Context, workspace_id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.tags(workspace_id, es_client=es_client))

@mcp.tool(description=api.benchmarks.make_candidate_pool.__doc__)
def benchmarks_make_candidate_pool(ctx: Context, workspace_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.make_candidate_pool(workspace_id, task, es_client=es_client))

@mcp.tool(description=api.benchmarks.get.__doc__)
def benchmarks_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.benchmarks.create.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkCreate.model_input_json_schema()}
""")
def benchmarks_create(ctx: Context, doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.create(doc, _id, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.benchmarks.update.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkUpdate.model_input_json_schema()}
""")
def benchmarks_update(ctx: Context, _id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.update(_id, doc_partial, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.benchmarks.delete.__doc__)
def benchmarks_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.benchmarks.delete(_id, es_client=es_client))


####  API: Evaluations  ########################################################

@mcp.tool(description=api.evaluations.search.__doc__)
def evaluations_search(
        ctx: Context,
        workspace_id: str = "",
        benchmark_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.evaluations.search(workspace_id, benchmark_id, text, filters, sort, size, page, aggs, es_client=es_client))

@mcp.tool(description=api.evaluations.get.__doc__)
def evaluations_get(ctx: Context, _id: str, source_includes: Optional[List[str]] = None) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.evaluations.get(_id, source_includes=source_includes, es_client=es_client))

@mcp.tool(description=api.evaluations.create.__doc__ + f"""\n
JSON schema for doc:\n\n{EvaluationCreate.model_input_json_schema()}
""")
def evaluations_create(ctx: Context, workspace_id: str, benchmark_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.evaluations.create(workspace_id, benchmark_id, task, user=user, via="mcp", es_client=es_client))

@mcp.tool(description=api.evaluations.run.__doc__)
def evaluations_run(ctx: Context, evaluation: Dict[str, Any], store_results: Optional[bool] = False) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.evaluations.run(evaluation, store_results, started_by=user, es_client=es_client))

@mcp.tool(description=api.evaluations.delete.__doc__)
def evaluations_delete(ctx: Context, _id: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.evaluations.delete(_id, es_client=es_client))


####  API: Content  ############################################################

@mcp.tool(description=api.content.search.__doc__)
def content_search(ctx: Context, index_patterns: str, body: Dict[str, Any]) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.content.search(index_patterns, body, es_client=es_client))

@mcp.tool(description=api.content.mappings_browse.__doc__)
def content_mappings_browse(ctx: Context, index_patterns: str) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return dict(api.content.mappings_browse(index_patterns, es_client=es_client))
    
    
####  API: Setup  ##############################################################

@mcp.tool(description=api.setup.check.__doc__)
def setup_check(ctx: Context) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return api.setup.check(es_client=es_client)

@mcp.tool(description=api.setup.run.__doc__)
def setup_run(ctx: Context) -> Dict[str, Any]:
    user, es_client = mcp_auth.get_mcp_auth_from_context(ctx)
    return api.setup.run(via="mcp", es_client=es_client)


####  Utils  ###################################################################

@mcp.tool(description="Get the base64 encoding of an image URL.")
def get_base64_image_from_url(ctx: Context, url: str, max_size: int = 50) -> str:
    response = requests.get(url)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "")
    if not content_type.startswith("image/"):
        raise ValueError(f"URL does not point to an image. Content-Type: {content_type}")

    # Resize image
    image = Image.open(BytesIO(response.content))
    image.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = BytesIO()
    format = image.format or content_type.split("/")[1].upper()
    if format == "JPG":
        format = "JPEG" # pillow expects "JPEG"
    image.save(buffer, format=format)
    buffer.seek(0)

    # Encode as base64
    encoded = base64.b64encode(buffer.read()).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"


####  Health checks  ###########################################################

@mcp.tool
def healthz_mcp() -> Dict[str, Any]:
    """
    Test if application is running.
    """
    return { "acknowledged": True }

@mcp.custom_route("/healthz", methods=["GET"])
def healthz_http(request: Request) -> JSONResponse:
    """
    Test if application is running.
    """
    return JSONResponse({ "acknowledged": True })


####  Main  ####################################################################

if __name__ == "__main__":
    tls = get_tls_config()
    if tls["error"]:
        print(tls["error"], file=sys.stderr)
        sys.exit(1)
    port = int(os.environ.get("FASTMCP_PORT") or "4200")
    transport_kwargs = {"port": port, "log_level": "debug"}
    if tls["uvicorn_config"]:
        transport_kwargs["uvicorn_config"] = tls["uvicorn_config"]
    mcp.run(transport="http", **transport_kwargs)