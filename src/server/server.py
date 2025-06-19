# Standard packages
import os
from functools import wraps

# Third-party packages
from dotenv import load_dotenv
from flask import Flask, current_app, jsonify, request
from flask_cors import CORS

# Elastic packages
from elasticsearch.exceptions import ApiError

# App packages
from . import api

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
            return jsonify(e.body), e.meta.status
        
        # Handle everything else
        except Exception as e: # TODO: Move this somewhere else
            current_app.logger.exception(f"Unexpected error: {e}")
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


####  API: Projects  #####################################################

@api_route("/api/projects", methods=["GET"])
def projects_browse():
    return api.projects.browse()

@api_route("/api/projects/<string:_id>", methods=["GET"])
def projects_get(_id):
    return api.projects.get(_id)

@api_route("/api/projects", methods=["POST"])
def projects_create():
    doc = request.get_json()
    return api.projects.create(doc)

@api_route("/api/projects/<string:_id>", methods=["PUT"])
def projects_update(_id):
    doc = request.get_json()
    return api.projects.update(_id, doc)

@api_route("/api/projects/<string:_id>", methods=["DELETE"])
def projects_delete(_id):
    return api.projects.delete(_id)


####  API: Displays  ###########################################################

@api_route("/api/projects/<string:project_id>/displays", methods=["GET"])
def displays_browse(project_id):
    return api.displays.browse(project_id)

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["GET"])
def displays_get(project_id, _id):
    return api.displays.get(_id)

@api_route("/api/projects/<string:project_id>/displays", methods=["POST"])
def displays_create(project_id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.displays.create(doc)

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["PUT"])
def displays_update(project_id, _id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.displays.update(_id, doc)

@api_route("/api/projects/<string:project_id>/displays/<string:_id>", methods=["DELETE"])
def displays_delete(project_id, _id):
    return api.displays.delete(_id)


####  API: Scenarios  ###########################################################

@api_route("/api/projects/<string:project_id>/scenarios", methods=["GET"])
def scenarios_browse(project_id):
    return api.scenarios.browse(project_id)

@api_route("/api/projects/<string:project_id>/scenarios/<string:_id>", methods=["GET"])
def scenarios_get(project_id, _id):
    return api.scenarios.get(_id)

@api_route("/api/projects/<string:project_id>/scenarios", methods=["POST"])
def scenarios_create(project_id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.scenarios.create(doc)

@api_route("/api/projects/<string:project_id>/scenarios/<string:_id>", methods=["PUT"])
def scenarios_update(project_id, _id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.scenarios.update(_id, doc)

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
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.judgements.set(**doc)

@api_route("/api/projects/<string:project_id>/judgements", methods=["DELETE"])
def judgements_unset(project_id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.judgements.unset(**doc)


####  API: Strategies  ###########################################################

@api_route("/api/projects/<string:project_id>/strategies", methods=["GET"])
def strategies_browse(project_id):
    return api.strategies.browse(project_id)

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["GET"])
def strategies_get(project_id, _id):
    return api.strategies.get(_id)

@api_route("/api/projects/<string:project_id>/strategies", methods=["POST"])
def strategies_create(project_id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.strategies.create(doc)

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["PUT"])
def strategies_update(project_id, _id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.strategies.update(_id, doc)

@api_route("/api/projects/<string:project_id>/strategies/<string:_id>", methods=["DELETE"])
def strategies_delete(project_id, _id):
    return api.strategies.delete(_id)


####  API: Benchmarks  #########################################################

@api_route("/api/projects/<string:project_id>/benchmarks", methods=["GET"])
def benchmarks_browse(project_id):
    return api.benchmarks.browse(project_id)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["GET"])
def benchmarks_get(project_id, _id):
    return api.benchmarks.get(_id)

@api_route("/api/projects/<string:project_id>/benchmarks", methods=["POST"])
def benchmarks_create(project_id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.benchmarks.create(doc)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["PUT"])
def benchmarks_update(project_id, _id):
    doc = request.get_json()
    doc["project_id"] = project_id # ensure project_id from path is in doc
    return api.benchmarks.update(_id, doc)

@api_route("/api/projects/<string:project_id>/benchmarks/<string:_id>", methods=["DELETE"])
def benchmarks_delete(project_id, _id):
    return api.benchmarks.delete(_id)


####  API: Evaluations  ########################################################

@api_route("/api/projects/<string:project_id>/evaluations", methods=["GET"])
def evaluations_browse(project_id):
    return api.evaluations.browse(project_id)

@api_route("/api/projects/<string:project_id>/evaluations/<string:_id>", methods=["GET"])
def evaluations_get(project_id, _id):
    return api.evaluations.get(_id)

@api_route("/api/projects/<string:project_id>/evaluations/<string:_id>", methods=["DELETE"])
def evaluations_delete(project_id, _id):
    return api.evaluations.delete(_id)

@api_route("/api/projects/<string:project_id>/evaluations", methods=["POST"])
def evaluations_run(project_id):
    body = request.get_json()
    if "store_results" in request.args:
        body["store_results"] = request.args["store_results"]
    body["project_id"] = project_id # ensure project_id from path is in body
    return api.evaluations.run(body)


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