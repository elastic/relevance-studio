# Standard packages
import datetime
import hashlib
import itertools
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone

# Elastic packages
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ApiError

# Third-party packages
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

def es_client():
    """
    Create two Elasticsearch clients:
    - "studio" connects to the deployment with esrs-* indices
    - "content" connects to the deployment with source indices
    """

    ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID", "").strip()
    ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "").strip()
    ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY", "").strip()
    ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "").strip()
    ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "").strip()
    CONTENT_ELASTIC_CLOUD_ID = os.getenv("CONTENT_ELASTIC_CLOUD_ID", "").strip()
    CONTENT_ELASTICSEARCH_URL = os.getenv("CONTENT_ELASTICSEARCH_URL", "").strip()
    CONTENT_ELASTICSEARCH_API_KEY = os.getenv("CONTENT_ELASTICSEARCH_API_KEY", "").strip()
    CONTENT_ELASTICSEARCH_USERNAME = os.getenv("CONTENT_ELASTICSEARCH_USERNAME", "").strip()
    CONTENT_ELASTICSEARCH_PASSWORD = os.getenv("CONTENT_ELASTICSEARCH_PASSWORD", "").strip()
    ELASTICSEARCH_TIMEOUT = int(os.getenv("ELASTICSEARCH_TIMEOUT", "60000").strip())

    # Validate configuration
    if not ELASTIC_CLOUD_ID and not ELASTICSEARCH_URL:
        raise ValueError("You must configure either ELASTIC_CLOUD_ID or ELASTICSEARCH_URL in .env")
    if (ELASTICSEARCH_USERNAME and not ELASTICSEARCH_PASSWORD) or (not ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD):
        raise ValueError("You must configure either ELASTICSEARCH_API_KEY or both of ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD in .env")
    if CONTENT_ELASTIC_CLOUD_ID or CONTENT_ELASTICSEARCH_URL:
        if not CONTENT_ELASTICSEARCH_API_KEY and not (CONTENT_ELASTICSEARCH_USERNAME and CONTENT_ELASTICSEARCH_PASSWORD):
            raise ValueError(f"When using {CONTENT_ELASTIC_CLOUD_ID or CONTENT_ELASTICSEARCH_URL}, you must configure either CONTENT_ELASTICSEARCH_API_KEY or both of CONTENT_ELASTICSEARCH_USERNAME and CONTENT_ELASTICSEARCH_PASSWORD in .env")

    # Setup Elasticsearch clients
    es = {
        "studio": None, # for the deployment with the esrs-* indices
        "content": None # for the deployment with the source content to be judged and evaluated
    }

    # Setup client for deployment with Elasticsearch Relevance Studio
    es_studio_kwargs = {
        "request_timeout": ELASTICSEARCH_TIMEOUT,
        "max_retries": 4,
        "retry_on_timeout": True
    }
    if ELASTIC_CLOUD_ID:
        es_studio_kwargs["cloud_id"] = ELASTIC_CLOUD_ID
    else:
        es_studio_kwargs["hosts"] = [ ELASTICSEARCH_URL ]
    if ELASTICSEARCH_API_KEY:
        es_studio_kwargs["api_key"] = ELASTICSEARCH_API_KEY
    else:
        es_studio_kwargs["basic_auth"] = (
            ELASTICSEARCH_USERNAME,
            ELASTICSEARCH_PASSWORD
        )
    es["studio"] = Elasticsearch(**es_studio_kwargs)

    # Setup client for deployment with source content
    if not CONTENT_ELASTIC_CLOUD_ID and not CONTENT_ELASTICSEARCH_URL:
        es["content"] = es["studio"]
    else:
        es_content_kwargs = {
            "request_timeout": ELASTICSEARCH_TIMEOUT,
            "max_retries": 4,
            "retry_on_timeout": True
        }
        if CONTENT_ELASTIC_CLOUD_ID:
            es_content_kwargs["cloud_id"] = CONTENT_ELASTIC_CLOUD_ID
        else:
            es_content_kwargs["hosts"] = [ CONTENT_ELASTICSEARCH_URL ]
        if CONTENT_ELASTICSEARCH_API_KEY:
            es_content_kwargs["api_key"] = CONTENT_ELASTICSEARCH_API_KEY
        else:
            es_content_kwargs["basic_auth"] = (
                CONTENT_ELASTICSEARCH_USERNAME,
                CONTENT_ELASTICSEARCH_PASSWORD
            )
        es["content"] = Elasticsearch(**es_content_kwargs)
    return es

es = es_client()

# Pre-compiled regular expressions
RE_PARAMS = re.compile(r"{{\s*([\w.]+)\s*}}")

def timestamp(t=None):
    """
    Generate a @timestamp value.
    """
    t = t or time.time()
    return datetime.fromtimestamp(t, tz=timezone.utc).isoformat().replace("+00:00", "Z")

def extract_params(obj):
    """
    Extract Mustache variable params from an object serialized as json.
    """
    return list(set(re.findall(RE_PARAMS, json.dumps(obj))))

def doc_from_search_as_get(response, index_searched, id_searched):
    """
    When fetching a single doc with POST _search instead of GET _doc,
    return the response in the format used by GET _doc.
    """
    if not response.body["hits"]["hits"]:
        return {
            "_index": index_searched,
            "_id": id_searched,
            "found": False
        }
    return {
        "_index": response.body["hits"]["hits"][0]["_index"],
        "_id": response.body["hits"]["hits"][0]["_id"],
        "_source": response.body["hits"]["hits"][0]["_source"],
        "found": True,
    }


####  Application  #############################################################

DEFAULT_STATIC_PATH = os.path.abspath(os.path.join(__file__, "..", "..", "..", "dist"))

app = Flask(__name__, static_folder=os.environ.get("STATIC_PATH") or DEFAULT_STATIC_PATH)
CORS(app)


####  API Helpers  #############################################################

def make_index_relevance_fingerprints(es, index_pattern):
    """
    Generate a relevance fingerprint for all indices in a given index pattern.
    
    Structure of the output object:
    
    {
        INDEX_NAME: {
            "fingerprint": STRING,
            "shards": [
                {
                    "id": SHARD_ID,
                    "max_seq_no": MAX_SEQ_NO
                },
                ...
            ],
            "uuid": INDEX_UUID
        },
        ...
    }
    
    Example output for an index pattern "products-*":
     
    {
        "products-2025": {
            "fingerprint": "c1d9b14ae26538325d2bb56471497844",
            "shards": [
                { "id": 0, "max_seq_no": 111 },
                { "id": 1, "max_seq_no": 112 }
            ],
            "uuid": "abc123..."
        },
        "products-2024": {
            "fingerprint": "03f758f51a1bae0ce87125ea295785a4",
            "shards": [
                { "id": 0, "max_seq_no": 301 }
            ],
            "uuid": "def456..."
        }
    }
    """
    
    # Create a fingerprint for each index in the given index pattern
    settings = es["content"].indices.get_settings(index=index_pattern)
    stats = es["content"].indices.stats(index=index_pattern, level="shards")
    fingerprints = {}
    for index_name in settings.keys():
        if index_name not in stats["indices"]:
            continue
        index_uuid = settings[index_name]["settings"]["index"]["uuid"]

        # Collect and deduplicate max_seq_no by shard
        shard_seq_nos = []
        shards = stats["indices"][index_name]["shards"]
        for shard_id, shard_copies in shards.items():
            for copy in shard_copies:
                max_seq_no = copy.get("seq_no", {}).get("max_seq_no")
                shard_seq_nos.append((int(shard_id), max_seq_no))

        shard_maxes = {}
        for shard_id, seq_no in shard_seq_nos:
            shard_maxes[shard_id] = max(seq_no, shard_maxes.get(shard_id, -1))

        # Prepare the data for hashing
        shard_list = [
            {"id": shard_id, "max_seq_no": seq_no}
            for shard_id, seq_no in sorted(shard_maxes.items())
        ]
        fingerprint_obj = {
            "index": index_name,
            "uuid": index_uuid,
            "shards": shard_list
        }

        # Deterministrically serialize the object and hash it
        fingerprint_json = json.dumps(fingerprint_obj, sort_keys=True)
        fingerprint_digest = hashlib.blake2s(fingerprint_json.encode(), digest_size=16).hexdigest()

        # Include the digest in the result
        fingerprints[index_name] = {
            **fingerprint_obj,
            "fingerprint": fingerprint_digest
        }
    return fingerprints

def update_project_asset(index, project_id, _id, doc):
    body = {
        "query": {
            "bool": {
                "filter": [
                    { "term": { "_id": _id} },
                    { "term": { "project_id": project_id }}
                ]
            }
        },
        "script": {
            "source": "ctx._source = params.doc",
            "lang": "painless",
            "params": {
                "doc": doc
            }
        }
    }
    response = es["studio"].update_by_query(
        index=index,
        body=body,
        refresh=True,
        conflicts="proceed"
    )
    return response

def delete_project_asset(index, project_id, _id):
    body = {
        "query": {
            "bool": {
                "filter": [
                    { "term": { "_id": _id }},
                    { "term": { "project_id": project_id }}
                ]
            }
        }
    }
    response = es["studio"].delete_by_query(
        index=index,
        body=body,
        refresh=True,
        conflicts="proceed"
    )
    return response


####  API: Elasticsearch APIs  #################################################

@app.route("/_search/<string:index_patterns>", methods=["POST"])
def post_search(index_patterns):
    """
    Submit a search request to the content deployment.
    """
    try:
        response = es["content"].search(index=index_patterns, body=request.get_json())
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500
    

@app.route("/indices/<string:index_patterns>", methods=["GET"])
def get_indices(index_patterns):
    """
    Given a comma-separated string of index patterns for the content deployment,
    return the matching indices with their fields and types in a flattened format.
    """
    
    # Get matching indices and their mappings
    mappings = {}
    try:
        mappings = es["content"].indices.get_mapping(index=index_patterns).body
    except ApiError as e:
        if e.meta.status == 404:
            return {}
        else:
            return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500
    
    # Flatten the fields in each mapping
    def _flatten_fields(properties, parent_key=""):
        """
        Recursively flattens the field mapping, ignoring multi-fields which
        aren"t visible in _source and therefore not needed for configuring
        the display of documents.
        """
        fields = {}
        for key, value in properties.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            if "properties" in value:
                fields.update(_flatten_fields(value["properties"], full_key))
            elif "type" in value:
                fields[full_key] = value["type"]
            # Ignore multi-fields
            #elif "fields" in value:
            #    if "type" in value:
            #        fields[full_key] = value["type"]
            #    for subfield, subvalue in value["fields"].items():
            #        sub_key = f"{full_key}.{subfield}"
            #        fields[sub_key] = subvalue.get("type", "object")
            else:
                fields[full_key] = "object"
        return fields
    indices = {}
    for index, mapping in mappings.items():
        fields = mapping["mappings"].get("properties", {})
        fields_flattened = _flatten_fields(fields)
        indices[index] = { "fields": fields_flattened }
    return indices


####  API: Evaluations  ########################################################

@app.route("/projects/<string:project_id>/evaluations/<string:evaluation_id>", methods=["DELETE"])
def delete_evaluation(project_id, evaluation_id):
    """
    Delete an evaluation for a given project.
    """
    try:
        response = delete_project_asset("esrs-evaluations", project_id, evaluation_id)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/evaluations", methods=["POST"])
def run_evaluation(project_id):
    """
    Expected structure of the request payload:
    
    {
        "strategies": [
            STRATEGY_ID,
            ...
        ],
        "scenarios": [
            SCENARIO_ID,
            ...
        ],
        "metrics": [
            METRIC_NAME,
            ...
        ],
        "k": INTEGER
    }
    
    Example:
    
    {
        "strategies": [
            "classical-name-match",
            "classical-name-match-fuzzy",
            "classical-multifield-match",
            "classical-multifield-match-boosts",
            "classical-multifield-match-signals-boosts",
            "elser-name-match",
            "elser-multifield-match",
            "elser-multifield-match-boosts",
            "elser-multifield-match-signals-boosts"
        ],
        "scenarios": [
            "cae18e7a-a4be-495f-a13b-69fdc1463ccb"
        ],
        "metrics": [
            "ndcg",
            "precision",
            "recall"
        ],
        "k": 10
    }
    
    Structure of the response payload:
    
    {
        "@timestamp": DATE,
        "project_id": KEYWORD,
        "strategy_id": [ KEYWORD, ... ],
        "scenario_id": [ KEYWORD, ... ],
        "config": {
            "metrics": [ KEYWORD, ... ],
            "k": INTEGER
        },
        "results": [
            {
                "strategy_id": KEYWORD,
                "searches": [
                    {
                        "scenario_id": KEYWORD,
                        "metrics": {
                            "ndcg": FLOAT,
                            "precision": FLOAT,
                            "recall": FLOAT
                        },
                        "hits": [
                            {
                                "hit": {
                                    "_id": KEYWORD,
                                    "_index": KEYWORD,
                                    "_score": FLOAT
                                },
                                "rating": INTEGER
                            }
                        ]
                    }
                ]
            }
        ],
        "runtime": {
            "indices": {
                INDEX_NAME: {
                    "fingerprint": KEYWORD,
                    "shards": [
                        {
                            "id": KEYWORD,
                            "max_seq_no": KEYWORD
                        },
                        ...
                    ],
                    "uuid": KEYWORD
                },
                ...
            },
            "strategies": {
                STRATEGY_ID: {
                    "name": KEYWORD,
                    "params": [ KEYWORD, ...],
                    "tags": [ KEYWORD, ...],
                    "template": OBJECT,
                },
                ...
            },
            "scenarios": {
                SCENARIO_ID: {
                    "name": KEYWORD,
                    "params": [ KEYWORD, ...],
                    "tags": [ KEYWORD, ...],
                },
                ...
            }
        },
        "unrated_docs": [
            {
                "_id": KEYWORD,
                "_index": KEYWORD
            },
            ...
        ],
        "took": INTEGER
    }
    """
    
    # Start timer
    start_time = time.time()
    
    # Parse and validate request
    task = request.get_json()
    task["k"] = int(task.get("k")) or 10
    task["metrics"] = task.get("metrics") or [ "ndcg", "precision", "recall" ]
    metrics_config = {
        # TODO: Support other types of metrics (commented out below)
        #"dcg": {
        #    "name": "dcg",
        #    "config": {
        #        "k": task["k"]
        #    }
        #},
        #"err": {
        #    "name": "expected_reciprocal_rank",
        #    "config": {
        #        "k": k,
        #        "maximum_relevance": rating_scale_max
        #    }
        #},
        #"mrr": {
        #    "name": "mean_reciprocal_rank",
        #    "config": {
        #        "k": task["k"]
        #    }
        #},
        "ndcg": {
            "name": "dcg",
            "config": {
                "k": task["k"],
                "normalize": True
            }
        },
        "precision": {
            "name": "precision",
            "config": {
                "k": task["k"],
                "ignore_unlabeled": False
            }
        },
        "recall": {
            "name": "recall",
            "config": {
                "k": task["k"]
            }
        }
    }
    valid_metrics = metrics_config.keys()
    if not set(task["metrics"]).issubset(set(valid_metrics)):
        raise Exception(f"\"metrics\" only supports these values: {', '.join(sorted(valid_metrics))}")
    if not task["k"] > 0:
        raise Exception("\"k\" must be greater than 0.")
    if not task.get("strategies"):
        raise Exception("\"strategies\" must have one or more strategy_id values.")
    if not task.get("scenarios"):
        raise Exception("\"scenarios\" must have one or more scenario_id values.")
    if "store_results" in request.args:
        if request.args["store_results"] in ( "", None ):
            task["store_results"] = True
        elif str(request.args["store_results"]).lower() in ( "true", "false" ):
            task["store_results"] = True if request.args["store_results"].lower() == "true" else False
        else:
            raise Exception("\"store_results\" must be true or false (or not given).")
    else:
        task["store_results"] = False
    
    # Prepare _rank_eval request
    _rank_eval = {
        "templates": [],
        "requests": [],
        "metric": {}
    }
    
    # Store the contents of the assets used at runtime in this evaluation
    runtime_indices = {}
    runtime_strategies = {}
    runtime_scenarios = {}
    runtime_judgements = {}
    
    # Set a default size of 10,000 hits per request when retrieving
    # strategies, scenarios, or judgements
    size = 10000
    
    # Get project
    es_response = None
    try:
        es_response = es["studio"].get(index="esrs-projects", id=project_id)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    index_pattern = es_response.body["_source"]["index_pattern"]
    rating_scale_max = es_response.body["_source"]["rating_scale"]["max"]
    
    # Get strategies and convert them to templates in _rank_eval
    es_response = None
    try:
        body = {
            "query": { "ids": { "values": task["strategies"] }},
            "size": size,
            "version": True
        }
        es_response = es["studio"].search(index="esrs-strategies", body=body)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    for hit in es_response.body["hits"]["hits"]:
        _rank_eval["templates"].append({
            "id": hit["_id"],
            "template": hit["_source"]["template"]
        })
        runtime_strategies[hit["_id"]] = {
            "_version": hit["_version"],
            "name": hit["_source"]["name"],
            "params": hit["_source"]["params"],
            "tags": hit["_source"]["tags"],
            "template": hit["_source"]["template"]
        }
    
    # Get judgements and convert them to ratings in _rank_eval.
    # Keep track of which scenarios had judgements, in case the request
    # includes scenarios that have no judgements.
    es_response = None
    scenarios_with_judgements = set()
    try:
        body = {
            "query": { "terms": { "scenario_id": task["scenarios"] }},
            "size": size,
            "version": True
        }
        es_response = es["studio"].search(index="esrs-judgements", body=body)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    ratings = {}
    for hit in es_response.body["hits"]["hits"]:
        scenario_id = hit["_source"]["scenario_id"]
        scenarios_with_judgements.add(scenario_id)
        if scenario_id not in ratings:
            ratings[scenario_id] = []
        ratings[scenario_id].append({
            "_index": hit["_source"]["index"],
            "_id": hit["_source"]["doc_id"],
            "rating": hit["_source"]["rating"],
        })
        runtime_judgements[hit["_id"]] = {
            "_version": hit["_version"],
            "@timestamp": hit["_source"]["@timestamp"],
            "@author": hit["_source"]["@author"],
            "scenario_id": hit["_source"]["scenario_id"],
            "index": hit["_source"]["index"],
            "doc_id": hit["_source"]["doc_id"],
            "rating": hit["_source"]["rating"]
        }
    scenarios_with_judgements = list(scenarios_with_judgements)
    
    # Store results by strategy and scenarios
    _results = {}
    for strategy_id in task["strategies"]:
        _results[strategy_id] = {}
        for scenario_id in scenarios_with_judgements:
            _results[strategy_id][scenario_id] = {
                "metrics": {},
                "hits": []
            }
    
    # Get scenarios
    scenarios = {}
    es_response = None
    try:
        body = {
            "query": { "ids": { "values": scenarios_with_judgements }},
            "size": size,
            "version": True
        }
        es_response = es["studio"].search(index="esrs-scenarios", body=body)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    for hit in es_response.body["hits"]["hits"]:
        scenarios[hit["_id"]] = hit["_source"]["values"]
        runtime_scenarios[hit["_id"]] = {
            "_version": hit["_version"],
            "name": hit["_source"]["name"],
            "values": hit["_source"]["params"],
            "values": hit["_source"]["values"],
            "tags": hit["_source"]["tags"]
        }
        
    # Store index relevance fingerprints
    runtime_indices = make_index_relevance_fingerprints(es, index_pattern)
    
    # Store any unrated docs found in the evaluation
    _unrated_docs = {}
    
    # Create a set of requests for each evaluation metric
    for m in task["metrics"]:
        
        # Reset the metric and requests for this iterartion
        _rank_eval["metric"] = {}
        _rank_eval["requests"] = []
        
        # Define the metric for this iteration
        metric_name = metrics_config[m]["name"]
        _rank_eval["metric"][metric_name] = metrics_config[m]["config"]
        
        # Define requests for each combination of strategies and scenarios
        grid = list(itertools.product(task["strategies"], scenarios_with_judgements))
        for strategy_id, scenario_id in grid:
            _rank_eval["requests"].append({
                "id": f"{strategy_id}~{scenario_id}",
                "template_id": strategy_id,
                "params": scenarios[scenario_id],
                "ratings": ratings[scenario_id]
            })
            
        # Run _rank_eval on the content deployment and accumulate the results
        try:
            body = {
                "metric": _rank_eval["metric"],
                "requests": _rank_eval["requests"],
                "templates": _rank_eval["templates"]
            }
            es_response = es["content"].rank_eval(
                index=index_pattern,
                body=body
            )
        except ApiError as e:
            return jsonify(e.body), e.meta.status
        
        # Store results
        for request_id, details in es_response.body["details"].items():
            strategy_id, scenario_id = request_id.split("~", 1)
            _results[strategy_id][scenario_id]["metrics"][m] = details["metric_score"]
            if not len(_results[strategy_id][scenario_id]["hits"]):
                _results[strategy_id][scenario_id]["hits"] = details["hits"]
                # Find unrated docs
                for hit in details["hits"]:
                    if hit["rating"] is not None:
                        continue
                    _index = hit["hit"]["_index"]
                    _id = hit["hit"]["_id"]
                    if _index not in _unrated_docs:
                        _unrated_docs[_index] = {}
                    if _id not in _unrated_docs[_index]:
                        _unrated_docs[_index][_id] = {
                            "count": 0,
                            "strategies": set(),
                            "scenarios": set()
                        }
                    _unrated_docs[_index][_id]["count"] += 1
                    _unrated_docs[_index][_id]["strategies"].add(strategy_id)
                    _unrated_docs[_index][_id]["scenarios"].add(scenario_id)
        
    # Restructure results for response
    results = []
    for strategy_id, _strategy_results in _results.items():
        strategy_results = {
            "strategy_id": strategy_id,
            "searches": []
        }
        for scenario_id, _scenario_results in _strategy_results.items():
            scenario_results = {
                "scenario_id": scenario_id,
                "metrics": _scenario_results["metrics"],
                "hits": _scenario_results["hits"]
            }
            strategy_results["searches"].append(scenario_results)
        results.append(strategy_results)
    unrated_docs = []
    for _index in sorted(_unrated_docs.keys()):
        for _id in sorted(_unrated_docs[_index].keys()):
            doc = _unrated_docs[_index][_id]
            strategies = sorted(list(doc["strategies"]))
            scenarios = sorted(list(doc["scenarios"]))
            unrated_docs.append({
                "_index": _index,
                "_id": _id,
                "count": doc["count"],
                "strategies": strategies,
                "scenarios": scenarios
            })
    unrated_docs = sorted(unrated_docs, key=lambda doc: doc["count"], reverse=True)
    
    # Create final response
    response = {
        "@timestamp": timestamp(start_time),
        "project_id": project_id,
        "strategy_id": task["strategies"],
        "scenario_id": scenarios_with_judgements,
        "config": {
            "metrics": task["metrics"],
            "k": task["k"]
        },
        "results": results,
        "runtime": {
            "indices": runtime_indices,
            "strategies": runtime_strategies,
            "scenarios": runtime_scenarios,
            "judgements": runtime_judgements
        },
        "unrated_docs": unrated_docs
    }
    response["took"] = int((time.time() - start_time) * 1000)
    
    # Store results
    if task["store_results"]:
        evaluation_id = uuid.uuid4()
        try:
            es_response = es["studio"].index(
                index="esrs-evaluations",
                id=evaluation_id,
                document=response,
                refresh=True
            )
            return jsonify(es_response.body), es_response.meta.status
        except ApiError as e:
            return jsonify(e.body), e.meta.status
        except Exception as e:
            app.logger.exception(f"Unexpected error: {e}")
            return jsonify({ "error": "Unexpected error", "message": str(e) }), 500
    return jsonify(response)

@app.route("/projects/<string:project_id>/evaluations/<string:evaluation_id>", methods=["GET"])
def get_evaluation(project_id, evaluation_id):
    """
    Get an evaluation for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": evaluation_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-evaluations"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, evaluation_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/evaluations", methods=["GET"])
def get_evaluations(project_id):
    """
    Get all evaluations for a given project.
    """
    try:
        body={
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "size": 10000
        }
        response = es["studio"].search(
            index="esrs-evaluations",
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Benchmarks  #########################################################

@app.route("/projects/<string:project_id>/benchmarks/<string:benchmark_id>", methods=["DELETE"])
def delete_benchmark(project_id, benchmark_id):
    """
    Delete a benchmark for a given project, and delete all evaluations related
    to the benchmark.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-benchmarks" }},
                                    { "term": { "_id": benchmark_id }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-evaluations" }},
                                    { "term": { "benchmark_id": benchmark_id }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        response = es["studio"].delete_by_query(
            index="esrs-benchmarks,esrs-evaluations",
            body=body,
            refresh=True,
            conflicts="proceed",
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/benchmarks/<string:benchmark_id>", methods=["PUT"])
def update_benchmark(project_id, benchmark_id):
    """
    Update a benchmark for a given project.
    """
    doc = request.get_json()
    doc.pop("_id", None)
    doc["project_id"] = project_id
    try:
        response = update_project_asset("esrs-benchmarks", project_id, benchmark_id, doc)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/benchmarks", methods=["POST"])
def create_benchmark(project_id):
    """
    Create a benchmark for a given project.
    """
    doc = request.get_json()
    doc["project_id"] = project_id
    benchmark_id = uuid.uuid4()
    try:
        response = es["studio"].index(
            index="esrs-benchmarks",
            id=benchmark_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/benchmarks/<string:benchmark_id>", methods=["GET"])
def get_benchmark(project_id, benchmark_id):
    """
    Get a benchmark for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": benchmark_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-benchmarks"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, benchmark_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/benchmarks", methods=["GET"])
def get_benchmarks(project_id):
    """
    Get all benchmarks for a given project.
    """
    try:
        body = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "post_filter": {
                "term": {
                    "_index": "esrs-benchmarks"
                }
            },
            "aggs": {
                "counts": {
                    "terms": {
                        "field": "scenario_id",
                        "size": 10000
                    },
                    "aggs": {
                        "judgements": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-evaluations"
                                }
                            }
                        }
                    }
                }
            }
        }
        index = ",".join([
            "esrs-benchmarks",
            "esrs-evaluations"
        ])
        response = es["studio"].search(
            index=index,
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Strategies  #########################################################

@app.route("/projects/<string:project_id>/strategies/<string:strategy_id>", methods=["DELETE"])
def delete_strategy(project_id, strategy_id):
    """
    Delete a strategy for a given project.
    """
    try:
        response = delete_project_asset("esrs-strategies", project_id, strategy_id)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    return jsonify(response.body), response.meta.status

@app.route("/projects/<string:project_id>/strategies/<string:strategy_id>", methods=["PUT"])
def update_strategy(project_id, strategy_id):
    """
    Update a strategy for a given project.
    """
    doc = request.get_json()
    doc.pop("_id", None)
    doc["project_id"] = project_id
    doc["params"] = extract_params(doc["template"]["source"])
    try:
        response = update_project_asset("esrs-strategies", project_id, strategy_id, doc)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/strategies", methods=["POST"])
def create_strategy(project_id):
    """
    Create a strategy for a given project.
    """
    doc = request.get_json()
    doc["project_id"] = project_id
    strategy_id = uuid.uuid4()
    try:
        response = es["studio"].index(
            index="esrs-strategies",
            id=strategy_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/strategies/<string:strategy_id>", methods=["GET"])
def get_strategy(project_id, strategy_id):
    """
    Get a strategy for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": strategy_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-strategies"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, strategy_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/strategies", methods=["GET"])
def get_strategies(project_id):
    """
    Get all strategies for a given project.
    """
    try:
        body={
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "size": 10000
        }
        response = es["studio"].search(
            index="esrs-strategies",
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Judgements  #########################################################

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>/judgements", methods=["DELETE"])
def unset_judgement(project_id, scenario_id):
    """
    Delete a judgement for a given project.
    """
    data = request.get_json()
    judgement_id = ":".join([ project_id, scenario_id, data["index"], data["doc_id"] ])
    try:
        response = delete_project_asset("esrs-judgements", project_id, judgement_id)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>/judgements", methods=["PUT"])
def set_judgement(project_id, scenario_id):
    """
    Create or update a judgement for a given project.
    """
    data = request.get_json()
    doc = {
        "@timestamp": timestamp(),
        "@author": "human",
        "project_id": project_id,
        "scenario_id": scenario_id,
        "index": data["index"],
        "doc_id": data["doc_id"],
        "rating": data["rating"],
    }
    judgement_id = ":".join([ project_id, scenario_id, data["index"], data["doc_id"] ])
    try:
        response = es["studio"].index(
            index="esrs-judgements",
            id=judgement_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/judgements/<string:judgement_id>", methods=["GET"])
def get_judgement(project_id, judgement_id):
    """
    Get a judgement for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": judgement_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-judgements"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, judgement_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/judgements", methods=["GET"])
def get_judgements(project_id):
    """
    Get all judgements for a given project.
    """
    try:
        body={
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "size": 10000
        }
        response = es["studio"].search(
            index="esrs-judgements",
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>/judgements/_docs", methods=["GET","POST"])
def get_judgements_docs(project_id, scenario_id):
    """
    Get documents from the content deployment with ratings joined to them.
    
    Expected structure of the request:
    
    {
        "index_pattern": STRING,        # Required
        "query_string": STRING,         # Optional
        "filter": STRING,               # Optional: "rated", "rated-ai", "rated-human", "unrated" (or omitted for no filter)
        "sort": STRING,                 # Optional: "match", "rating-newest", "rating-oldest"
        "_source": {}                   # Optional
    }
    """
    data = request.get_json()
    index_pattern = data["index_pattern"]
    query_string = data.get("query_string") or "*"
    filter = data.get("filter")
    sort = data.get("sort")
    _source = data.get("_source", True)
    response = {}
    try:
        
        # Get judgements for scenario
        judgements = {}
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "project_id": project_id }},
                        { "term": { "scenario_id": scenario_id }}
                    ]
                }
            },
            "size": 10000
        }
        if filter == "rated-human":
            body["query"]["bool"]["filter"].append({
                "term": { "@author": "human"}
            })
        elif filter == "rated-ai":
            body["query"]["bool"]["filter"].append({
                "term": { "@author": "ai"}
            })
        if sort == "rating-newest":
            body["sort"] = [{
                "@timestamp": "desc"
            }]
        elif sort == "rating-oldest":
            body["sort"] = [{
                "@timestamp": "asc"
            }]
        es_response = es["studio"].search(index="esrs-judgements", body=body)
        for hit in es_response.body["hits"]["hits"]:
            _index = hit["_source"]["index"]
            _id = hit["_source"]["doc_id"]
            if _index not in judgements:
                judgements[_index] = {}
            judgements[_index][_id] = {
                "@timestamp": hit["_source"].get("@timestamp"),
                "@author": hit["_source"].get("@author"),
                "rating": hit["_source"].get("rating")
            }
            
        # Search docs on the content deployment
        body = {
            "size": 48,
            "query": {
                "bool": {
                    "must": {
                        "query_string": {
                            "query": query_string,
                            "default_operator": "AND"
                        }
                    }
                }
            },
            "_source": _source
        }
        
        # Filter docs by judgements
        if filter and filter != "all":
            filter_clauses = []
            for _index in judgements.keys():
                filter_clauses.append({
                    "bool": {
                        "filter": [
                            { "term": { "_index": _index }},
                            { "ids": { "values": list(judgements[_index].keys()) }}
                        ]
                    }
                })
            if filter == "unrated":
                body["query"]["bool"]["must_not"] = filter_clauses
            else:
                body["query"]["bool"]["should"] = filter_clauses
                body["query"]["bool"]["minimum_should_match"] = 1
        if sort == "match":
            body["sort"] = [{
                "_score": "desc"
            }]
        es_response = es["content"].search(index=index_pattern, body=body)
        
        # Merge docs and ratings
        response["hits"] = es_response.body["hits"]
        for i, hit in enumerate(response["hits"]["hits"]):
            response["hits"]["hits"][i] = {
                "@timestamp": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@timestamp", None),
                "@author": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("@author", None),
                "rating": judgements.get(hit["_index"], {}).get(hit["_id"], {}).get("rating", None),
                "doc": hit
            }
        if response["hits"]["hits"] and sort in ( "rating-newest", "rating-oldest" ):
            reverse = True if sort == "rating-newest" else False
            fallback = "0000-01-01T00:00:00Z" if not reverse else "9999-12-31T23:59:59Z"
            response["hits"]["hits"] = sorted(response["hits"]["hits"], key=lambda hit: hit.get("@timestamp") or fallback, reverse=reverse)
        return jsonify(response)
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Scenarios  ###########################################################

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>", methods=["DELETE"])
def delete_scenario(project_id, scenario_id):
    """
    Delete a scenario for a given project, and delete all judgements related to
    the scenario.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-scenarios" }},
                                    { "term": { "_id": scenario_id }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-judgements" }},
                                    { "term": { "scenario_id": scenario_id }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        response = es["studio"].delete_by_query(
            index="esrs-scenarios,esrs-judgements",
            body=body,
            refresh=True,
            conflicts="proceed",
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>", methods=["PUT"])
def update_scenario(project_id, scenario_id):
    """
    Update a scenario for a given project.
    """
    doc = request.get_json()
    doc.pop("_id", None)
    doc["project_id"] = project_id
    try:
        response = update_project_asset("esrs-scenarios", project_id, scenario_id, doc)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios", methods=["POST"])
def create_scenario(project_id):
    """
    Create a scenario for a given project.
    """
    doc = request.get_json()
    doc["project_id"] = project_id
    scenario_id = uuid.uuid4()
    try:
        response = es["studio"].index(
            index="esrs-scenarios",
            id=scenario_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios/<string:scenario_id>", methods=["GET"])
def get_scenario(project_id, scenario_id):
    """
    Get a scenario for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": scenario_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-scenarios"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, scenario_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/scenarios", methods=["GET"])
def get_scenarios(project_id):
    """
    Get all scenarios for a given project.
    """
    try:
        body = {
            "size": 10000,
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "post_filter": {
                "term": {
                    "_index": "esrs-scenarios"
                }
            },
            "aggs": {
                "counts": {
                    "terms": {
                        "field": "scenario_id",
                        "size": 10000
                    },
                    "aggs": {
                        "judgements": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-judgements"
                                }
                            }
                        }
                    }
                }
            }
        }
        index = ",".join([
            "esrs-scenarios",
            "esrs-judgements"
        ])
        response = es["studio"].search(
            index=index,
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Displays  #####################################################

@app.route("/projects/<string:project_id>/displays/<string:display_id>", methods=["DELETE"])
def delete_display(project_id, display_id):
    """
    Delete a display for a given project.
    """
    try:
        response = delete_project_asset("esrs-displays", project_id, display_id)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/displays/<string:display_id>", methods=["PUT"])
def update_display(project_id, display_id):
    """
    Update a display for a given project.
    """
    doc = request.get_json()
    doc.pop("_id", None)
    doc["project_id"] = project_id
    doc["fields"] = [ x for x in extract_params(doc["template"]["body"]) if not x.startswith("_") ]
    try:
        response = update_project_asset("esrs-displays", project_id, display_id, doc)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/displays", methods=["POST"])
def create_display(project_id):
    """
    Create a display for a given project.
    """
    doc = request.get_json()
    doc["project_id"] = project_id
    doc["fields"] = [ x for x in extract_params(doc["template"]["body"]) if not x.startswith("_") ]
    display_id = uuid.uuid4()
    try:
        response = es["studio"].index(
            index="esrs-displays",
            id=display_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/displays/<string:display_id>", methods=["GET"])
def get_display(project_id, display_id):
    """
    Get a display for a given project.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "filter": [
                        { "term": { "_id": display_id }},
                        { "term": { "project_id": project_id }}
                    ]
                }
            },
            "size": 1
        }
        index = "esrs-displays"
        response = es["studio"].search(index=index, body=body)
        doc = doc_from_search_as_get(response, index, display_id)
        if not doc["found"]:
            return jsonify(doc), 404
        return jsonify(doc), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>/displays", methods=["GET"])
def get_displays(project_id):
    """
    Get all displays for a given project.
    """
    try:
        body={
            "query": {
                "bool": {
                    "filter": {
                        "term": {
                            "project_id": project_id
                        }
                    }
                }
            },
            "size": 10000
        }
        response = es["studio"].search(
            index="esrs-displays",
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500


####  API: Projects  #####################################################

@app.route("/projects/<string:project_id>", methods=["DELETE"])
def delete_project(project_id):
    """
    Delete a project and all assets related to it.
    """
    try:
        body = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-projects" }},
                                    { "term": { "_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-displays" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-scenarios" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-judgements" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-strategies" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-benchmarks" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        },
                        {
                            "bool": {
                                "filter": [
                                    { "term": { "_index": "esrs-evaluations" }},
                                    { "term": { "project_id": project_id }}
                                ]
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            }
        }
        response = es["studio"].delete_by_query(
            index=",".join([
                "esrs-projects",
                "esrs-displays",
                "esrs-scenarios",
                "esrs-judgements",
                "esrs-strategies",
                "esrs-benchmarks",
                "esrs-evaluations",
            ]),
            body=body,
            refresh=True,
            conflicts="proceed",
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>", methods=["PUT"])
def update_project(project_id):
    """
    Update a project.
    """
    doc = request.get_json()
    doc.pop("_id", None)
    try:
        response = es["studio"].update(
            index="esrs-projects",
            id=project_id,
            doc=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects", methods=["POST"])
def create_project():
    """
    Create a project.
    """
    doc = request.get_json()
    project_id = uuid.uuid4()
    try:
        response = es["studio"].index(
            index="esrs-projects",
            id=project_id,
            document=doc,
            refresh=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects/<string:project_id>", methods=["GET"])
def get_project(project_id):
    """
    Get a project.
    """
    try:
        response = es["studio"].get(index="esrs-projects", id=project_id)
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500

@app.route("/projects", methods=["GET"])
def get_projects():
    """
    Get all projects.
    """
    try:
        body = {
            "size": 10000,
            "post_filter": {
                "term": {
                    "_index": "esrs-projects"
                }
            },
            "aggs": {
                "counts": {
                    "terms": {
                        "field": "project_id",
                        "size": 10000
                    },
                    "aggs": {
                        "displays": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-displays"
                                }
                            }
                        },
                        "scenarios": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-scenarios"
                                }
                            }
                        },
                        "judgements": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-judgements"
                                }
                            }
                        },
                        "strategies": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-strategies"
                                }
                            }
                        },
                        "benchmarks": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-benchmarks"
                                }
                            }
                        },
                        "evaluations": {
                            "filter": {
                                "term": {
                                    "_index": "esrs-evaluations"
                                }
                            }
                        }
                    }
                }
            }
        }
        index = ",".join([
            "esrs-projects",
            "esrs-displays",
            "esrs-scenarios",
            "esrs-judgements",
            "esrs-strategies",
            "esrs-benchmarks",
            "esrs-evaluations",
        ])
        response = es["studio"].search(
            index=index,
            body=body,
            ignore_unavailable=True
        )
        return jsonify(response.body), response.meta.status
    except ApiError as e:
        return jsonify(e.body), e.meta.status
    except Exception as e:
        app.logger.exception(f"Unexpected error: {e}")
        return jsonify({ "error": "Unexpected error", "message": str(e) }), 500
    
    
####  API: Setup  ##############################################################

@app.route("/setup", methods=["POST"])
def setup():
    """
    Setup index templates.
    """
    path_base = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "elastic", "index_templates"
    )
    path_index_templates = [
        ( "esrs-projects", os.path.join(path_base, "projects.json") ),
        ( "esrs-displays", os.path.join(path_base, "displays.json") ),
        ( "esrs-scenarios", os.path.join(path_base, "scenarios.json") ),
        ( "esrs-judgements", os.path.join(path_base, "judgements.json") ),
        ( "esrs-strategies", os.path.join(path_base, "strategies.json") ),
        ( "esrs-benchmarks", os.path.join(path_base, "benchmarks.json") ),
        ( "esrs-evaluations", os.path.join(path_base, "evaluations.json") )
    ]
    result = {
        "failures": 0,
        "requests": []
    }
    for index_template_name, path_index_template in path_index_templates:
        body = None
        with open(path_index_template) as file:
            body = json.loads(file.read())
        name = body["index_patterns"][0].replace("*", "")
        try:
            response = es["studio"].indices.put_template(name=name, body=body)
            result["requests"].append({
                "index_template": index_template_name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index_template": index_template_name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
    return jsonify(result)


####  API: Tests  ##############################################################

@app.route("/healthz", methods=["GET"])
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