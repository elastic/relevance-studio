# Standard packages
import json
import os
from typing import Any, Dict

# Elastic packages
from elasticsearch.exceptions import ApiError, NotFoundError, RequestError

# App packages
from ..client import es

PATH_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "elastic", "index_templates"
)
PATH_INDEX_TEMPLATES = [
    ( "esrs-workspaces", os.path.join(PATH_BASE, "workspaces.json") ),
    ( "esrs-displays", os.path.join(PATH_BASE, "displays.json") ),
    ( "esrs-scenarios", os.path.join(PATH_BASE, "scenarios.json") ),
    ( "esrs-judgements", os.path.join(PATH_BASE, "judgements.json") ),
    ( "esrs-strategies", os.path.join(PATH_BASE, "strategies.json") ),
    ( "esrs-benchmarks", os.path.join(PATH_BASE, "benchmarks.json") ),
    ( "esrs-evaluations", os.path.join(PATH_BASE, "evaluations.json") )
]

def is_cloud(headers: Dict[str, Any]) -> bool:
    """
    Given the response headers from Elasticsearch, check if it contains any
    headers that would indicates that it's from Elastic Cloud.
    """
    return any(k.lower().startswith("x-found-") for k in headers)

def is_serverless(cluster_info_body: Dict[str, Any]) -> bool:
    """
    Given the contents of es.info().body, check if the deployment is serverless.
    """
    return cluster_info_body.get("version", {}).get("build_flavor") == "serverless"

def get_cluster_info():
    """
    Get cluster info from Elasticsearch.
    """
    return es("studio").info()

def check():
    """
    Check if the esrs-* index templates and indices have been created.
    """

    # Initialize result
    result = {
        "deployment": {
            "cluster_info": {},
            "mode": None,
        },
        "setup": {
            "failures": 0,
            "requests": [],
        }
    }
    
    # Get deployment info
    cluster_info = get_cluster_info()
    result["deployment"]["cluster_info"] = cluster_info.body
    if is_serverless(cluster_info.body):
        result["deployment"]["mode"] = "serverless"
    elif is_cloud(cluster_info.meta.headers):
        result["deployment"]["mode"] = "cloud"
    else:
        result["deployment"]["mode"] = "standard"
    
    # Check setup
    for index_template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = None
        with open(path_index_template) as file:
            body = json.loads(file.read())
        name = body["index_patterns"][0].replace("*", "")
        
        # Check index template
        try:
            response = es("studio").indices.get_index_template(name=name)
            result["setup"]["requests"].append({
                "index_template": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except (ApiError, NotFoundError) as e:
            result["setup"]["failures]"] += 1
            result["setup"]["requests"].append({
                "index_template": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
        
        # Check index
        try:
            exists = es("studio").indices.exists(index=name)
            result["setup"]["requests"].append({
                "index": name,
                "response": {
                    "body": "OK" if exists else "Not Found",
                    "status": 200 if exists else 404
                }
            })
            result["setup"]["failures"] += 0 if exists else 1
        except ApiError as e:
            result["setup"]["failures"] += 1
            result["setup"]["requests"].append({
                "index": index_template_name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
    return result

def run():
    """
    Setup the esrs-* index templates and indices.
    
    Structure of the returned object:
    
    {
        "setup": {
            "failures": NUM_FAILED_REQUESTS,
            "requests": [
                {
                    "index_template": INDEX_TEMPLATE_NAME,
                    "response": {
                        "body": HTTP_RESPONSE_BODY,
                        "status": HTTP_STATUS_CODE
                    }
                },
                {
                    "index": INDEX_NAME,
                    "response": {
                        "body": HTTP_RESPONSE_BODY,
                        "status": HTTP_STATUS_CODE
                    }
                },
                ...
            ]
        }
    }
    """
    
    # Initialize result
    result = {
        "setup": {
            "failures": 0,
            "requests": [],
        }
    }
    
    # Check setup
    for index_template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = None
        with open(path_index_template) as file:
            body = json.loads(file.read())
        name = body["index_patterns"][0].replace("*", "")
        
        # Create index template
        try:
            response = es("studio").indices.put_index_template(name=name, body=body)
            result["setup"]["requests"].append({
                "index_template": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except ApiError as e:
            result["setup"]["failures"] += 1
            result["setup"]["requests"].append({
                "index_template": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
        
        # Create index
        try:
            response = es("studio").indices.create(index=name)
            result["setup"]["requests"].append({
                "index": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except RequestError as e:
            result["setup"]["requests"].append({
                    "index": name,
                    "response": {
                        "body": e.body,
                        "status": e.meta.status
                    }
                })
            if e.error != "resource_already_exists_exception":
                result["setup"]["failures"] += 1
        except ApiError as e:
            result["setup"]["failures"] += 1
            result["setup"]["requests"].append({
                "index": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
    return result