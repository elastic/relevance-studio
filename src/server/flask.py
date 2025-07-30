# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

# Standard packages
import os
from functools import wraps

# Third-party packages
from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Elastic packages
from elasticsearch.exceptions import ApiError

# App packages
from . import api
from .models import *

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

####  Application  #############################################################

DEFAULT_STATIC_PATH = os.path.abspath(os.path.join(__file__, "..", "..", "..", "dist"))

app = Flask(__name__, static_folder=os.environ.get("STATIC_PATH") or DEFAULT_STATIC_PATH)
CORS(app)

def handle_response(func):
    """
    Decorate functions that may return Elasticsearch responses or ApiErrors.
    If so, return the response and HTTP status code from Elasticsearch.
    Otherwise return the response as JSON for dicts and lists, or as-is for
    everything else.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            
            # Check if the result includes a status code
            result = func(*args, **kwargs)
            if isinstance(result, tuple) and len(result) == 2:
                response, status = result
            else:
                response, status = result, None
            
            # Return Elasticsearch response
            if hasattr(response, "body") and hasattr(response, "meta") and hasattr(response.meta, "status"):
                return jsonify(response.body), response.meta.status
            
            # Otherwise return original response as JSON if it's a dict or list
            if isinstance(response, dict) or isinstance(response, list):
                return jsonify(response), status or 200
            
            # Otherwise return original response as-is
            return response, status or 200
        
        # Handle Elasticsearch ApiError
        except ApiError as e:
            current_app.logger.exception(e)
            return jsonify(e.body), e.meta.status
        
        # Handle everything else
        except Exception as e: # TODO: Move this somewhere else
            current_app.logger.exception(e)
            return jsonify({"error": "Unexpected error", "message": str(e)}), 500
    return wrapper

def make_api_route(router):
    """
    Custom API route handler.
    """
    def api_route(rule: str, **options):
        def decorator(func):
            return router.route(rule, **options)(handle_response(func))
        return decorator
    return api_route

api_route = make_api_route(app)


####  API: Validations  ########################################################

def validate_workspace_id_match(body, workspace_id_from_url):
    """
    When updating documents, if a workspace_id is given in the request body,
    it must match the workspace_id from the URL.
    """
    if "workspace_id" in body and body["workspace_id"] != workspace_id_from_url:
        raise BadRequest("The workspace_id in the URL must match workspace_id in request body if given.")
    

####  API: Workspaces  #########################################################

@api_route("/api/workspaces/_search", methods=["POST"])
def workspaces_search():
    body = request.get_json() or {}
    return api.workspaces.search(**body)

@api_route("/api/workspaces/<string:_id>", methods=["GET"])
def workspaces_get(_id):
    return api.workspaces.get(_id)

@api_route("/api/workspaces", methods=["POST"])
def workspaces_create():
    doc = request.get_json()
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.workspaces.create(doc, _id)

@api_route("/api/workspaces/<string:_id>", methods=["PUT"])
def workspaces_update(_id):
    doc_partial = request.get_json()
    return api.workspaces.update(_id, doc_partial)

@api_route("/api/workspaces/<string:_id>", methods=["DELETE"])
def workspaces_delete(_id):
    return api.workspaces.delete(_id)


####  API: Displays  ###########################################################

@api_route("/api/workspaces/<string:workspace_id>/displays/_search", methods=["POST"])
def displays_search(workspace_id):
    body = request.get_json() or {}
    return api.displays.search(workspace_id, **body)

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["GET"])
def displays_get(workspace_id, _id):
    return api.displays.get(_id)

@api_route("/api/workspaces/<string:workspace_id>/displays", methods=["POST"])
def displays_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.displays.create(doc, _id)

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["PUT"])
def displays_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.displays.update(_id, doc_partial)

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["DELETE"])
def displays_delete(workspace_id, _id):
    return api.displays.delete(_id)


####  API: Scenarios  ##########################################################

@api_route("/api/workspaces/<string:workspace_id>/scenarios/_search", methods=["POST"])
def scenarios_search(workspace_id):
    body = request.get_json() or {}
    return api.scenarios.search(workspace_id, **body)

@api_route("/api/workspaces/<string:workspace_id>/scenarios/_tags", methods=["GET"])
def scenarios_tags(workspace_id):
    return api.scenarios.tags(workspace_id)

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["GET"])
def scenarios_get(workspace_id, _id):
    return api.scenarios.get(_id)

@api_route("/api/workspaces/<string:workspace_id>/scenarios", methods=["POST"])
def scenarios_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.scenarios.create(doc)

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["PUT"])
def scenarios_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.scenarios.update(_id, doc_partial)

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["DELETE"])
def scenarios_delete(workspace_id, _id):
    return api.scenarios.delete(_id)


####  API: Judgements  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/judgements/_search", methods=["POST"])
def judgements_search(workspace_id):
    body = request.get_json()
    body["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.judgements.search(**body)

@api_route("/api/workspaces/<string:workspace_id>/judgements", methods=["PUT"])
def judgements_set(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    doc.pop("_id", None) # _id is always generated from body
    return api.judgements.set(doc)

@api_route("/api/workspaces/<string:workspace_id>/judgements/<string:_id>", methods=["DELETE"])
def judgements_unset(workspace_id, _id):
    return api.judgements.unset(_id)


####  API: Strategies  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/strategies/_search", methods=["POST"])
def strategies_search(workspace_id):
    body = request.get_json() or {}
    return api.strategies.search(workspace_id, **body)

@api_route("/api/workspaces/<string:workspace_id>/strategies/_tags", methods=["GET"])
def strategies_tags(workspace_id):
    return api.strategies.tags(workspace_id)

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["GET"])
def strategies_get(workspace_id, _id):
    return api.strategies.get(_id)

@api_route("/api/workspaces/<string:workspace_id>/strategies", methods=["POST"])
def strategies_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.strategies.create(doc, _id)

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["PUT"])
def strategies_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.strategies.update(_id, doc_partial)

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["DELETE"])
def strategies_delete(workspace_id, _id):
    return api.strategies.delete(_id)


####  API: Benchmarks  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_search", methods=["POST"])
def benchmarks_search(workspace_id):
    body = request.get_json() or {}
    return api.benchmarks.search(workspace_id, **body)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_tags", methods=["GET"])
def benchmarks_tags(workspace_id):
    return api.benchmarks.tags(workspace_id)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_candidates", methods=["POST"])
def benchmarks_make_candidate_pool(workspace_id):
    body = request.get_json() or {}
    return api.benchmarks.make_candidate_pool(workspace_id, body)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["GET"])
def benchmarks_get(workspace_id, _id):
    return api.benchmarks.get(_id)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks", methods=["POST"])
def benchmarks_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.benchmarks.create(doc, _id)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["PUT"])
def benchmarks_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.benchmarks.update(_id, doc_partial)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["DELETE"])
def benchmarks_delete(workspace_id, _id):
    return api.benchmarks.delete(_id)


####  API: Evaluations  ########################################################

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/_search", methods=["POST"])
def evaluations_search(workspace_id, benchmark_id):
    body = request.get_json() or {}
    return api.evaluations.search(workspace_id, benchmark_id, **body)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["GET"])
def evaluations_get(workspace_id, benchmark_id, _id):
    return api.evaluations.get(_id)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations", methods=["POST"])
def evaluations_create(workspace_id, benchmark_id):
    task = request.get_json()
    return api.evaluations.create(workspace_id, benchmark_id, task)

@api_route("/api/workspaces/<string:workspace_id>/evaluations/_run", methods=["POST"])
def evaluations_run(workspace_id):
    body = request.get_json()
    validate_workspace_id_match(body, workspace_id)
    body["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.evaluations.run(body)

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["DELETE"])
def evaluations_delete(workspace_id, benchmark_id, _id):
    return api.evaluations.delete(_id)


####  API: Content  ############################################################

@api_route("/api/content/_search/<string:index_patterns>", methods=["POST"])
def content_search(index_patterns):
    body = request.get_json()
    return api.content.search(index_patterns, body)

@api_route("/api/content/mappings/<string:index_patterns>", methods=["GET"])
def content_mappings_browse(index_patterns):
    return api.content.mappings_browse(index_patterns)
    
    
####  API: Setup  ##############################################################

@api_route("/api/setup", methods=["GET"])
def setup_check():
    return api.setup.check()

@api_route("/api/setup", methods=["POST"])
def setup_run():
    return api.setup.run()


####  Health checks  ###########################################################

@api_route("/healthz", methods=["GET"])
def healthz():
    """
    Test if application is running.
    """
    return { "acknowledged": True }


####  Static routes  ###########################################################

@app.route("/<path:filepath>.png")
def send_png(filepath):
    return app.send_static_file(f"{filepath}.png")

@app.route("/<path:filepath>.css")
def send_css(filepath):
    return app.send_static_file(f"{filepath}.css")

@app.route("/<path:filepath>.js")
def send_js(filepath):
    return app.send_static_file(f"{filepath}.js")

@app.route("/")
def home():
    return app.send_static_file("index.html")


####  Main  ####################################################################

if __name__ == "__main__":
    app.run(port=4096, debug=True)