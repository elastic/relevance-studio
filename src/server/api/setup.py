# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

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
    ( "esrs-conversations", os.path.join(PATH_BASE, "conversations.json") ),
    ( "esrs-workspaces", os.path.join(PATH_BASE, "workspaces.json") ),
    ( "esrs-displays", os.path.join(PATH_BASE, "displays.json") ),
    ( "esrs-scenarios", os.path.join(PATH_BASE, "scenarios.json") ),
    ( "esrs-judgements", os.path.join(PATH_BASE, "judgements.json") ),
    ( "esrs-strategies", os.path.join(PATH_BASE, "strategies.json") ),
    ( "esrs-benchmarks", os.path.join(PATH_BASE, "benchmarks.json") ),
    ( "esrs-evaluations", os.path.join(PATH_BASE, "evaluations.json") )
]

def is_cloud(headers: Dict[str, Any]) -> bool:
    """Check if the Elasticsearch response headers indicate Elastic Cloud.

    Args:
        headers: A dictionary of response headers from Elasticsearch.

    Returns:
        True if the headers indicate an Elastic Cloud deployment, False otherwise.
    """
    return any(k.lower().startswith("x-found-") for k in headers)

def is_serverless(cluster_info_body: Dict[str, Any]) -> bool:
    """Check if the Elasticsearch deployment is serverless.

    Args:
        cluster_info_body: The body of the Elasticsearch info response.

    Returns:
        True if the deployment is serverless, False otherwise.
    """
    return cluster_info_body.get("version", {}).get("build_flavor") == "serverless"

def get_license_info():
    """Get license information from Elasticsearch.

    Returns:
        The response from the Elasticsearch license API.
    """
    return es("studio").license.get()


def get_cluster_info():
    """Get cluster information from Elasticsearch.

    Returns:
        The response from the Elasticsearch info API.
    """
    return es("studio").info()

def check():
    """Check if the required index templates and indices have been created.

    Returns:
        A dictionary containing deployment info and setup status with any failures.
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

    # Get license info
    license_info = get_license_info()
    result["deployment"]["license"] = {
        "type": license_info.body.get("license", {}).get("type") or "unknown",
        "status": license_info.body.get("license", {}).get("status") or "unknown"
    }

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
            result["setup"]["failures"] += 1
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
    """Setup the required index templates and indices for Relevance Studio.

    Returns:
        A dictionary containing the results of each setup request and the failure count.
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