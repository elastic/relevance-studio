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

def validate_project_id_match(body, project_id_from_url):
    """
    When updating documents, if a project_id is given in the request body,
    it must match the project_id from the URL.
    """
    if body.get("project_id") and body["project_id"] != project_id_from_url:
        raise BadRequest("The project_id in the URL must match project_id in request body if given.")

def validate_id_match(body, _id_from_url):
    """
    When updating documents, if an _id is given in the request body, it must
    match the _id from the URL.
    """
    if body.get("_id") and body["_id"] != _id_from_url:
        raise BadRequest("The _id in the URL must match _id in request body if given.")
    

####  API: Projects  ###########################################################

@api_route("/api/projects/_search", methods=["POST"])
def projects_search():
    body = request.get_json() or {}
    return api.projects.search(**body)

@api_route("/api/projects/<string:project_id>/benchmarks/_tags", methods=["GET"])
def projects_tags(project_id):
    return api.projects.tags("projects")

@api_route("/api/projects/<string:_id>", methods=["GET"])
def projects_get(_id):
    return api.projects.get(_id)

@api_route("/api/projects", methods=["POST"])
def projects_create():
    body = request.get_json()
    _id = body.pop("_id", None) # accept an optional _id if given
    return api.projects.create(ProjectModel(**body), _id)

@api_route("/api/projects/<string:_id>", methods=["PUT"])
def projects_update(_id):
    body = request.get_json()
    validate_id_match(body, _id)
    return api.projects.update(_id, ProjectModel(**body))

@api_route("/api/projects/<string:_id>", methods=["DELETE"])
def projects_delete(_id):
    return api.projects.delete(_id)


####  API: Displays  ###########################################################

@api_route("/api/projects/<string:project_id>/displays/_search", methods=["POST"])
def displays_search(project_id):
    body = request.get_json() or {}
    return api.displays.search(project_id, **body)

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["GET"])
def displays_get(project_id, _id):
    return api.displays.get(_id)

@api_route("/api/projects/<string:project_id>/displays", methods=["POST"])
def displays_create(project_id):
    body = request.get_json()
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    _id = body.pop("_id", None) # accept an optional _id if given
    return api.displays.create(DisplayModel(**body), _id)

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["PUT"])
def displays_update(project_id, _id):
    body = request.get_json()
    validate_id_match(body, _id)
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    return api.displays.update(_id, DisplayModel(**body))

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["DELETE"])
def displays_delete(project_id, _id):
    return api.displays.delete(_id)


####  API: Scenarios  ###########################################################

@api_route("/api/projects/<string:project_id>/scenarios/_search", methods=["POST"])
def scenarios_search(project_id):
    body = request.get_json() or {}
    return api.scenarios.search(project_id, **body)

@api_route("/api/projects/<string:project_id>/scenarios/_tags", methods=["GET"])
def scenarios_tags(project_id):
    return api.scenarios.tags(project_id)

@api_route("/api/projects/<string:project_id>/scenarios/<string:_id>", methods=["GET"])
def scenarios_get(project_id, _id):
    return api.scenarios.get(_id)

@api_route("/api/projects/<string:project_id>/scenarios", methods=["POST"])
def scenarios_create(project_id):
    body = request.get_json()
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    body.pop("_id", None) # _id is always generated from body
    return api.scenarios.create(ScenarioModel(**body))

@api_route("/api/projects/<string:project_id>/scenarios/<string:_id>", methods=["PUT"])
def scenarios_update(project_id, _id):
    body = request.get_json()
    validate_id_match(body, _id)
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    return api.scenarios.update(_id, ScenarioModel(**body))

@api_route("/api/projects/<string:project_id>/scenarios/<string:_id>", methods=["DELETE"])
def scenarios_delete(project_id, _id):
    return api.scenarios.delete(_id)


####  API: Judgements  #########################################################

@api_route("/api/projects/<string:project_id>/judgements/_search", methods=["POST"])
def judgements_search(project_id):
    body = request.get_json()
    body["project_id"] = project_id # ensure project_id from path is in doc
    return api.judgements.search(**body)

@api_route("/api/projects/<string:project_id>/judgements", methods=["PUT"])
def judgements_set(project_id):
    body = request.get_json()
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    body.pop("_id", None) # _id is always generated from body
    return api.judgements.set(JudgementModel(**body))

@api_route("/api/projects/<string:project_id>/judgements/<string:_id>", methods=["DELETE"])
def judgements_unset(project_id, _id):
    return api.judgements.unset(_id)


####  API: Strategies  ###########################################################

@api_route("/api/projects/<string:project_id>/strategies/_search", methods=["POST"])
def strategies_search(project_id):
    body = request.get_json() or {}
    return api.strategies.search(project_id, **body)

@api_route("/api/projects/<string:project_id>/strategies/_tags", methods=["GET"])
def strategies_tags(project_id):
    return api.strategies.tags(project_id)

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["GET"])
def strategies_get(project_id, _id):
    return api.strategies.get(_id)

@api_route("/api/projects/<string:project_id>/strategies", methods=["POST"])
def strategies_create(project_id):
    body = request.get_json()
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    _id = body.pop("_id", None) # accept an optional _id if given
    return api.strategies.create(StrategyModel(**body), _id)

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["PUT"])
def strategies_update(project_id, _id):
    body = request.get_json()
    validate_id_match(body, _id)
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    return api.strategies.update(_id, StrategyModel(**body))

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["DELETE"])
def strategies_delete(project_id, _id):
    return api.strategies.delete(_id)


####  API: Benchmarks  #########################################################

@api_route("/api/projects/<string:project_id>/benchmarks/_search", methods=["POST"])
def benchmarks_search(project_id):
    body = request.get_json() or {}
    return api.benchmarks.search(project_id, **body)

@api_route("/api/projects/<string:project_id>/benchmarks/_tags", methods=["GET"])
def benchmarks_tags(project_id):
    return api.benchmarks.tags(project_id)

@api_route("/api/projects/<string:project_id>/benchmarks/_candidates", methods=["POST"])
def benchmarks_make_candidate_pool(project_id):
    return api.benchmarks.make_candidate_pool(project_id, request.get_json())

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["GET"])
def benchmarks_get(project_id, _id):
    return api.benchmarks.get(_id)

@api_route("/api/projects/<string:project_id>/benchmarks", methods=["POST"])
def benchmarks_create(project_id):
    body = request.get_json()
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    _id = body.pop("_id", None) # accept an optional _id if given
    return api.benchmarks.create(BenchmarkModel(**body), _id)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["PUT"])
def benchmarks_update(project_id, _id):
    body = request.get_json()
    validate_id_match(body, _id)
    validate_project_id_match(body, project_id)
    body["project_id"] = project_id # ensure project_id from path is in doc
    return api.benchmarks.update(_id, BenchmarkModel(**body))

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["DELETE"])
def benchmarks_delete(project_id, _id):
    return api.benchmarks.delete(_id)


####  API: Evaluations  ########################################################

@api_route("/api/projects/<string:project_id>/benchmarks/<string:benchmark_id>/evaluations/_search", methods=["POST"])
def evaluations_search(project_id, benchmark_id):
    body = request.get_json() or {}
    return api.evaluations.search(project_id, benchmark_id, **body)

@api_route("/api/projects/<string:project_id>//benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["GET"])
def evaluations_get(project_id, benchmark_id, _id):
    return api.evaluations.get(_id)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:benchmark_id>/evaluations", methods=["POST"])
def evaluations_create(project_id, benchmark_id):
    task = request.get_json()
    return api.evaluations.create(project_id, benchmark_id, task)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["DELETE"])
def evaluations_delete(project_id, benchmark_id, _id):
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

@api_route("/api/setup", methods=["POST"])
def setup():
    return api.setup.run()


####  Health checks  ###########################################################

@api_route("/healthz", methods=["GET"])
def healthz():
    """
    Test if application is running.
    """
    return { "acknowledged": True }


####  Static routes  ###########################################################

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