# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import os
import sys
from functools import wraps

# Third-party packages
import jwt
from dotenv import load_dotenv
from flask import Flask, current_app, g, jsonify, make_response, request, Response, stream_with_context
from flask_cors import CORS
from werkzeug.exceptions import BadRequest

# Elastic packages
from elasticsearch.exceptions import ApiError, AuthenticationException

# App packages
from . import api
from . import auth
from .client import es, es_from_credentials
from .models import *
from .tls import get_tls_config

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

# Auth
AUTH_COOKIE_NAME = "relevance_studio_session"

####  Application  #############################################################

DEFAULT_STATIC_PATH = os.path.abspath(os.path.join(__file__, "..", "..", "..", "dist"))

app = Flask(__name__, static_folder=os.environ.get("STATIC_PATH") or DEFAULT_STATIC_PATH)
app.config["SECRET_KEY"] = os.getenv("JWT_SECRET", "dev-secret")
CORS(app, supports_credentials=True)

# Pre-load MCP tools
import asyncio
try:
    asyncio.run(api.agent._get_mcp_tools())
except Exception as e:
    app.logger.error(f"Failed to pre-load MCP tools: {e}")


####  Auth middleware  ########################################################

@app.before_request
def auth_middleware():
    """Attach g.user and g.es_client for /api/* routes (except login). Skip /healthz."""
    path = request.path
    if path == "/healthz":
        return
    if not path.startswith("/api/"):
        return

    if path == "/api/auth/login" or path == "/api/auth/logout":
        return

    if not auth.AUTH_ENABLED:
        g.user = {"username": "system", "roles": ["superuser"]}
        g.es_client = es("studio")
        return

    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return jsonify({"error": "Unauthorized", "message": "No session cookie"}), 401

    try:
        payload = auth.decode_jwt(token)
    except jwt.InvalidTokenError:
        return jsonify({"error": "Unauthorized", "message": "Invalid or expired session"}), 401

    user_metadata = payload.get("user", {})
    api_key_encoded = payload.get("api_key")
    if not api_key_encoded:
        return jsonify({"error": "Unauthorized", "message": "Invalid session payload"}), 401

    g.user = user_metadata
    g.es_client = es_from_credentials(api_key=api_key_encoded)


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
            if e.meta.status == 404:
                current_app.logger.warning(f"Resource not found: {e}")
            else:
                current_app.logger.exception(e)
            return jsonify(e.body), e.meta.status

        # Handle auth errors
        except AuthenticationException as e:
            body = getattr(e, "body", {"error": "Unauthorized", "message": str(e)})
            status = getattr(getattr(e, "meta", None), "status", 401)
            return jsonify(body if isinstance(body, dict) else {"error": "Unauthorized", "message": str(e)}), status

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

def _request_user():
    user = getattr(g, "user", None)
    if isinstance(user, dict):
        return user.get("username")
    return user


def _request_es_client():
    return getattr(g, "es_client", None)


def validate_workspace_id_match(body, workspace_id_from_url):
    """
    When updating documents, if a workspace_id is given in the request body,
    it must match the workspace_id from the URL.
    """
    if "workspace_id" in body and body["workspace_id"] != workspace_id_from_url:
        raise BadRequest("The workspace_id in the URL must match workspace_id in request body if given.")


####  API: Auth  ################################################################

@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticate credentials and create session (JWT cookie)."""
    if not auth.AUTH_ENABLED:
        return jsonify({"user": {"username": "system", "roles": ["superuser"]}}), 200

    body = request.get_json() or {}
    credentials = {}
    if body.get("api_key"):
        credentials["api_key"] = body["api_key"]
    elif body.get("username") and body.get("password"):
        credentials["username"] = body["username"]
        credentials["password"] = body["password"]
    else:
        return jsonify({"error": "Bad request", "message": "Provide api_key or username and password"}), 400

    try:
        user = auth.validate_credentials(credentials)
    except AuthenticationException:
        return jsonify({"error": "Unauthorized", "message": "Invalid credentials"}), 401

    # API-key login cannot always create a derived API key; reuse provided key.
    # Username/password login still creates a scoped session API key.
    if credentials.get("api_key"):
        session_api_key_encoded = credentials["api_key"]
    else:
        api_key_result = auth.create_session_api_key(credentials)
        session_api_key_encoded = api_key_result["encoded"]

    token = auth.encode_jwt(user, session_api_key_encoded)

    resp = make_response(jsonify({"user": user}))
    resp.set_cookie(
        AUTH_COOKIE_NAME,
        token,
        httponly=True,
        secure=os.getenv("FLASK_ENV") == "production",
        samesite="Lax",
        max_age=86400 * 7,  # 7 days
    )
    return resp, 200


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Clear session cookie."""
    resp = make_response(jsonify({"acknowledged": True}))
    resp.delete_cookie(AUTH_COOKIE_NAME)
    return resp, 200


@api_route("/api/auth/session", methods=["GET"])
def auth_session():
    """Return current session user. Requires auth (or AUTH_ENABLED=false)."""
    if not auth.AUTH_ENABLED:
        return {"user": {"username": "system", "roles": ["superuser"]}}
    user = getattr(g, "user", None)
    if not user:
        return jsonify({"error": "Unauthorized", "message": "No session"}), 401
    return {"user": user}


####  API: Agent  ##############################################################

@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json() or {}
    return Response(
        stream_with_context(api.agent.chat(**body)),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Content-Type": "text/event-stream; charset=utf-8",
            "X-Accel-Buffering": "no"
        }
    )

@api_route("/api/chat/endpoints", methods=["GET"])
def chat_endpoints():
    return api.agent.endpoints()

@app.route("/api/chat/cancel/<string:session_id>", methods=["POST"])
def chat_cancel(session_id):
    """Cancel an ongoing chat session."""
    api.agent.request_cancellation(session_id)
    return jsonify({"status": "cancellation_requested"})


####  API: Conversations  ######################################################

@api_route("/api/conversations/_search", methods=["POST"])
def conversations_search():
    body = request.get_json() or {}
    return api.conversations.search(**body, es_client=_request_es_client())

@api_route("/api/conversations/<string:_id>", methods=["GET"])
def conversations_get(_id):
    return api.conversations.get(_id, es_client=_request_es_client())

@api_route("/api/conversations", methods=["POST"])
def conversations_create():
    doc = request.get_json()
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.conversations.create(doc, _id, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/conversations/<string:_id>", methods=["PUT"])
def conversations_update(_id):
    doc_partial = request.get_json()
    return api.conversations.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/conversations/<string:_id>", methods=["DELETE"])
def conversations_delete(_id):
    return api.conversations.delete(_id, es_client=_request_es_client())


####  API: Workspaces  #########################################################

@api_route("/api/workspaces/_search", methods=["POST"])
def workspaces_search():
    body = request.get_json() or {}
    return api.workspaces.search(**body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:_id>", methods=["GET"])
def workspaces_get(_id):
    return api.workspaces.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces", methods=["POST"])
def workspaces_create():
    doc = request.get_json()
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.workspaces.create(doc, _id, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:_id>", methods=["PUT"])
def workspaces_update(_id):
    doc_partial = request.get_json()
    return api.workspaces.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:_id>", methods=["DELETE"])
def workspaces_delete(_id):
    return api.workspaces.delete(_id, es_client=_request_es_client())


####  API: Displays  ###########################################################

@api_route("/api/workspaces/<string:workspace_id>/displays/_search", methods=["POST"])
def displays_search(workspace_id):
    body = request.get_json() or {}
    return api.displays.search(workspace_id, **body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["GET"])
def displays_get(workspace_id, _id):
    return api.displays.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/displays", methods=["POST"])
def displays_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.displays.create(doc, _id, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["PUT"])
def displays_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.displays.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/displays/<string:_id>", methods=["DELETE"])
def displays_delete(workspace_id, _id):
    return api.displays.delete(_id, es_client=_request_es_client())


####  API: Scenarios  ##########################################################

@api_route("/api/workspaces/<string:workspace_id>/scenarios/_search", methods=["POST"])
def scenarios_search(workspace_id):
    body = request.get_json() or {}
    return api.scenarios.search(workspace_id, **body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/scenarios/_tags", methods=["GET"])
def scenarios_tags(workspace_id):
    return api.scenarios.tags(workspace_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["GET"])
def scenarios_get(workspace_id, _id):
    return api.scenarios.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/scenarios", methods=["POST"])
def scenarios_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.scenarios.create(doc, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["PUT"])
def scenarios_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.scenarios.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/scenarios/<string:_id>", methods=["DELETE"])
def scenarios_delete(workspace_id, _id):
    return api.scenarios.delete(_id, es_client=_request_es_client())


####  API: Judgements  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/judgements/_search", methods=["POST"])
def judgements_search(workspace_id):
    body = request.get_json()
    body["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.judgements.search(**body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/judgements", methods=["PUT"])
def judgements_set(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc.pop("_id", None) # _id is always generated from body
    return api.judgements.set(
        workspace_id=workspace_id,
        scenario_id=doc["scenario_id"],
        index=doc["index"],
        doc_id=doc["doc_id"],
        rating=doc["rating"],
        user=_request_user(),
        via="server",
        es_client=_request_es_client(),
    )

@api_route("/api/workspaces/<string:workspace_id>/judgements/<string:_id>", methods=["DELETE"])
def judgements_unset(workspace_id, _id):
    return api.judgements.unset(_id, es_client=_request_es_client())


####  API: Strategies  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/strategies/_search", methods=["POST"])
def strategies_search(workspace_id):
    body = request.get_json() or {}
    return api.strategies.search(workspace_id, **body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/strategies/_tags", methods=["GET"])
def strategies_tags(workspace_id):
    return api.strategies.tags(workspace_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["GET"])
def strategies_get(workspace_id, _id):
    return api.strategies.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/strategies", methods=["POST"])
def strategies_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.strategies.create(doc, _id, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["PUT"])
def strategies_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    return api.strategies.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/strategies/<string:_id>", methods=["DELETE"])
def strategies_delete(workspace_id, _id):
    return api.strategies.delete(_id, es_client=_request_es_client())


####  API: Benchmarks  #########################################################

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_search", methods=["POST"])
def benchmarks_search(workspace_id):
    body = request.get_json() or {}
    return api.benchmarks.search(workspace_id, **body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_tags", methods=["GET"])
def benchmarks_tags(workspace_id):
    return api.benchmarks.tags(workspace_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/_candidates", methods=["POST"])
def benchmarks_make_candidate_pool(workspace_id):
    body = request.get_json() or {}
    return api.benchmarks.make_candidate_pool(workspace_id, body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["GET"])
def benchmarks_get(workspace_id, _id):
    return api.benchmarks.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks", methods=["POST"])
def benchmarks_create(workspace_id):
    doc = request.get_json()
    validate_workspace_id_match(doc, workspace_id)
    doc["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    _id = doc.pop("_id", None) # accept an optional _id if given
    return api.benchmarks.create(doc, _id, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["PUT"])
def benchmarks_update(workspace_id, _id):
    doc_partial = request.get_json()
    validate_workspace_id_match(doc_partial, workspace_id)
    doc_partial["workspace_id"] = workspace_id # ensure workspace_id from path is in doc_partial
    return api.benchmarks.update(_id, doc_partial, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:_id>", methods=["DELETE"])
def benchmarks_delete(workspace_id, _id):
    return api.benchmarks.delete(_id, es_client=_request_es_client())


####  API: Evaluations  ########################################################

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/_search", methods=["POST"])
def evaluations_search(workspace_id, benchmark_id):
    body = request.get_json() or {}
    return api.evaluations.search(workspace_id, benchmark_id, **body, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["GET"])
def evaluations_get(workspace_id, benchmark_id, _id):
    return api.evaluations.get(_id, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations", methods=["POST"])
def evaluations_create(workspace_id, benchmark_id):
    task = request.get_json()
    return api.evaluations.create(workspace_id, benchmark_id, task, user=_request_user(), via="server", es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/evaluations/_run", methods=["POST"])
def evaluations_run(workspace_id):
    body = request.get_json()
    validate_workspace_id_match(body, workspace_id)
    body["workspace_id"] = workspace_id # ensure workspace_id from path is in doc
    user = _request_user()
    started_by = user or "unknown"
    return api.evaluations.run(body, started_by=started_by, es_client=_request_es_client())

@api_route("/api/workspaces/<string:workspace_id>/benchmarks/<string:benchmark_id>/evaluations/<string:_id>", methods=["DELETE"])
def evaluations_delete(workspace_id, benchmark_id, _id):
    return api.evaluations.delete(_id, es_client=_request_es_client())


####  API: Content  ############################################################

@api_route("/api/content/_search/<string:index_patterns>", methods=["POST"])
def content_search(index_patterns):
    body = request.get_json()
    return api.content.search(index_patterns, body, es_client=_request_es_client())

@api_route("/api/content/mappings/<string:index_patterns>", methods=["GET"])
def content_mappings_browse(index_patterns):
    return api.content.mappings_browse(index_patterns, es_client=_request_es_client())
    
    
####  API: Setup  ##############################################################

@api_route("/api/setup", methods=["GET"])
def setup_check():
    return api.setup.check(es_client=_request_es_client())

@api_route("/api/setup", methods=["POST"])
def setup_run():
    return api.setup.run(via="server", es_client=_request_es_client())

@api_route("/api/upgrade", methods=["POST"])
def upgrade_run():
    return api.setup.upgrade(via="server", es_client=_request_es_client())


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
    tls = get_tls_config()
    if tls["error"]:
        print(tls["error"], file=sys.stderr)
        sys.exit(1)
    host = os.environ.get("FLASK_RUN_HOST") or "0.0.0.0"
    port = int(os.environ.get("FLASK_RUN_PORT") or "4096")
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(
        host=host,
        port=port,
        debug=debug,
        ssl_context=tls["ssl_context"],
    )