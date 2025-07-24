# Standard packages
import base64
from io import BytesIO
from typing import Any, Dict, List, Optional

# Third-party packages
import requests
from dotenv import load_dotenv
from fastmcp import FastMCP
from PIL import Image
from starlette.requests import Request
from starlette.responses import JSONResponse

# App packages
from . import api
from .models import *

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

####  Application  #############################################################

instructions = """
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

- **projects** - A namespace for all assets whose project_id matches the project _id.
- **displays** - A markdown template to render documents from specific indices in the **UI**.
- **scenarios** - A search input (e.g. "brown oxfords")
- **judgements** - A rating for a given document from a given index for a given scenario.
- **strategies** - An Elasticsearch search template whose params are supplied by scenario values.
- **benchmarks** - A reusable task definition for evaluations.
- **evaluations** - The results of a gridded rank evaluation.

## General workflow

Here is the typical workflow of the application:

1. Select a project to work in.
    - Take note of "_id", "name", "index_pattern", "rating_scale", and "params".
2. Use displays to control the retrieval and display of documents from indices in the content deployment.
    - "index_pattern" is the Elasticsearch index pattern that the display. When multiple displays have overlapping "index_pattern" values, the more specific matching pattern should be used.
    - "fields" lists the fields that should be in the _source.includes of all searches to that index pattern.
    - "template.image.url" is an image for the document. It might contain mustache variables, which should be replaced by their respective values from "fields".
3. Define a diverse set of scenarios that are representative of the use case.
4. Curate judgements for each scenario using the project rating scale.
    - "rating_scale_max" represents superb relevance.
    - "rating_scale.min" represents complete irrelevance.
    - "index" in judgements is the index of the doc being rated.
    - "doc_id" in judgements is the _id of the doc being rated.
5. Build strategies that attempt to maximize search relevance.
    - Strategies are the bodies of Elasticsearch Search API, which is a "query" or "retriever".
    - Strategies must implement at least one of the params from the project in the form of a Mustache variables. Example: "{{ text }}"
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

### 1. Always scope operations on studio assets by project_id

All operations on **studio deployment data assets** must be scoped to a project.
If I ask you to perform a search, create, update, set, unset, or delete on
displays, scenarios, judgements, strategies, benchmarks or evaluations, pass the
project_id that you're currently working on as an argument to that function.

If you aren't working on a project or you forgot which one it was, ask me for
clarification on which project you should be using. If I give you an _id
(which is a UUID), then use that as the project_id. If I give you a name or a
description instead, then search for the project that best matches it and use
that _id. If there are no good matches, let me know, and don't perform the
operation.

### 2. Always fetch displays before searching or judging documents from the content deployment

Fetch all displays for the project before searching or judging documents from
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

mcp = FastMCP(name="Relevance Studio", instructions=instructions)
    

####  API: Projects  ###########################################################

@mcp.tool(description=api.projects.search.__doc__)
def projects_search(
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.projects.search(text, filters, sort, size, page, aggs))

@mcp.tool(description=api.projects.get.__doc__)
def projects_get(_id: str) -> Dict[str, Any]:
    return dict(api.projects.get(_id))

@mcp.tool(description=api.projects.create.__doc__ + f"""\n
JSON schema for doc:\n\n{ProjectCreate.model_input_json_schema()}
""")
def projects_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.projects.create(doc, _id, user="ai"))

@mcp.tool(description=api.projects.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{DisplayCreate.model_input_json_schema()}
""")
def projects_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.projects.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.projects.delete.__doc__)
def projects_delete(_id: str) -> Dict[str, Any]:
    return dict(api.projects.delete(_id))


####  API: Displays  ###########################################################

@mcp.tool(description=api.displays.search.__doc__)
def displays_search(
        project_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.displays.search(project_id, text, filters, sort, size, page, aggs))

@mcp.tool(description=api.displays.get.__doc__)
def displays_get(_id: str) -> Dict[str, Any]:
    return dict(api.displays.get(_id))

@mcp.tool(description=api.displays.create.__doc__ + f"""\n
JSON schema for doc:\n\n{DisplayCreate.model_input_json_schema()}
""")
def displays_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.displays.create(doc, _id, user="ai"))

@mcp.tool(description=api.displays.update.__doc__ + f"""\n
JSON schema for doc_partia:\n\n{DisplayUpdate.model_input_json_schema()}
""")
def displays_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.displays.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.displays.delete.__doc__)
def displays_delete(_id: str) -> Dict[str, Any]:
    return dict(api.displays.delete(_id))


####  API: Scenarios  ###########################################################

@mcp.tool(description=api.scenarios.search.__doc__)
def scenarios_search(
        project_id: str,
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.scenarios.search(project_id, text, filters, sort, size, page, aggs))

@mcp.tool(description=api.scenarios.tags.__doc__)
def scenarios_tags(project_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.tags(project_id))

@mcp.tool(description=api.scenarios.get.__doc__)
def scenarios_get(_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.get(_id))

@mcp.tool(description=api.scenarios.create.__doc__ + f"""\n
JSON schema for doc:\n\n{ScenarioCreate.model_input_json_schema()}
""")
def scenarios_create(doc: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.scenarios.create(doc, user="ai"))

@mcp.tool(description=api.scenarios.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{ScenarioUpdate.model_input_json_schema()}
""")
def scenarios_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.scenarios.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.scenarios.delete.__doc__)
def scenarios_delete(_id: str) -> Dict[str, Any]:
    return dict(api.scenarios.delete(_id))


####  API: Judgements  #########################################################

@mcp.tool(description=api.judgements.search.__doc__)
def judgements_search(
        project_id: str,
        scenario_id: str,
        index_pattern: str,
        query: Dict[str, Any] = {},
        query_string: str = "*",
        filter: str = None,
        sort: str = None,
        _source: Dict[str, Any] = None
    ) -> Dict[str, Any]:
    return dict(api.judgements.search(project_id, scenario_id, index_pattern, query, query_string, filter, sort, _source))

@mcp.tool(description=api.judgements.set.__doc__ + f"""\n
JSON schema for doc:\n\n{JudgementCreate.model_input_json_schema()}
""")
def judgements_set(doc: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.judgements.set(doc, user="ai"))

@mcp.tool(description=api.judgements.unset.__doc__)
def judgements_unset(_id: str) -> Dict[str, Any]:
    return dict(api.judgements.unset(_id))


####  API: Strategies  ###########################################################

@mcp.tool(description=api.strategies.search.__doc__)
def strategies_search(
        project_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.strategies.search(project_id, text, filters, sort, size, page, aggs))

@mcp.tool(description=api.strategies.tags.__doc__)
def strategies_tags(project_id: str) -> Dict[str, Any]:
    return dict(api.strategies.tags(project_id))

@mcp.tool(description=api.strategies.get.__doc__)
def strategies_get(_id: str) -> Dict[str, Any]:
    return dict(api.strategies.get(_id))

@mcp.tool(description=api.strategies.create.__doc__ + f"""\n
JSON schema for doc:\n\n{StrategyCreate.model_input_json_schema()}
""")
def strategies_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.strategies.create(doc, _id, user="ai"))

@mcp.tool(description=api.strategies.update.__doc__ + f"""\n
JSON schema for doc_partial:\n\n{StrategyUpdate.model_input_json_schema()}
""")
def strategies_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.strategies.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.strategies.delete.__doc__)
def strategies_delete(_id: str) -> Dict[str, Any]:
    return dict(api.strategies.delete(_id))


####  API: Benchmarks  #########################################################

@mcp.tool(description=api.benchmarks.search.__doc__)
def benchmarks_search(
        project_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.benchmarks.search(project_id, text, filters, sort, size, page, aggs))

@mcp.tool(description=api.benchmarks.tags.__doc__)
def benchmarks_tags(project_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.tags(project_id))

@mcp.tool(description=api.benchmarks.make_candidate_pool.__doc__)
def benchmarks_make_candidate_pool(project_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.benchmarks.make_candidate_pool(project_id, task))

@mcp.tool(description=api.benchmarks.get.__doc__)
def benchmarks_get(_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.get(_id))

@mcp.tool(description=api.benchmarks.create.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkCreate.model_input_json_schema()}
""")
def benchmarks_create(doc: Dict[str, Any], _id: str = None) -> Dict[str, Any]:
    return dict(api.benchmarks.create(doc, _id, user="ai"))

@mcp.tool(description=api.benchmarks.update.__doc__ + f"""\n
JSON schema for doc:\n\n{BenchmarkUpdate.model_input_json_schema()}
""")
def benchmarks_update(_id: str, doc_partial: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.benchmarks.update(_id, doc_partial, user="ai"))

@mcp.tool(description=api.benchmarks.delete.__doc__)
def benchmarks_delete(_id: str) -> Dict[str, Any]:
    return dict(api.benchmarks.delete(_id))


####  API: Evaluations  ########################################################

@mcp.tool(description=api.evaluations.search.__doc__)
def evaluations_search(
        project_id: str = "",
        benchmark_id: str = "",
        text: Optional[str] = "",
        filters: Optional[List[Dict[str, Any]]] = [],
        sort: Dict[str, Any] = {},
        size: Optional[int] = 10,
        page: Optional[int] = 1,
        aggs: Optional[bool] = False,
    ) -> Dict[str, Any]:
    return dict(api.evaluations.search(project_id, benchmark_id, text, filters, sort, size, page, aggs))

@mcp.tool(description=api.evaluations.get.__doc__)
def evaluations_get(_id: str) -> Dict[str, Any]:
    return dict(api.evaluations.get(_id))

@mcp.tool(description=api.evaluations.create.__doc__ + f"""\n
JSON schema for doc:\n\n{EvaluationCreate.model_input_json_schema()}
""")
def evaluations_create(project_id: str, benchmark_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.evaluations.create(project_id, benchmark_id, task, user="ai"))

@mcp.tool(description=api.evaluations.run.__doc__)
def evaluations_run(evaluation: Dict[str, Any], store_results: Optional[bool] = False) -> Dict[str, Any]:
    return dict(api.evaluations.run(evaluation, store_results))

@mcp.tool(description=api.evaluations.delete.__doc__)
def evaluations_delete(_id: str) -> Dict[str, Any]:
    return dict(api.evaluations.delete(_id))


####  API: Content  ############################################################

@mcp.tool(description=api.content.search.__doc__)
def content_search(index_patterns: str, body: Dict[str, Any]) -> Dict[str, Any]:
    return dict(api.content.search(index_patterns, body))

@mcp.tool(description=api.content.mappings_browse.__doc__)
def content_mappings_browse(index_patterns: str) -> Dict[str, Any]:
    return dict(api.content.mappings_browse(index_patterns))
    
    
####  API: Setup  ##############################################################

@mcp.tool(description=api.setup.check.__doc__)
def setup_check() -> Dict[str, Any]:
    return api.setup.check()

@mcp.tool(description=api.setup.run.__doc__)
def setup_run() -> Dict[str, Any]:
    return api.setup.run()


####  Utils  ###################################################################

@mcp.tool(description="Get the base64 encoding of an image URL.")
def get_base64_image_from_url(url: str, max_size: int = 50) -> str:
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
    mcp.run(transport="http", port=4200, log_level="debug")