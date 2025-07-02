# Standard packages
import json
import os

# Elastic packages
from elasticsearch.exceptions import ApiError, NotFoundError, RequestError

# App packages
from ..client import es

PATH_BASE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "elastic", "index_templates"
)
PATH_INDEX_TEMPLATES = [
    ( "esrs-projects", os.path.join(PATH_BASE, "projects.json") ),
    ( "esrs-displays", os.path.join(PATH_BASE, "displays.json") ),
    ( "esrs-scenarios", os.path.join(PATH_BASE, "scenarios.json") ),
    ( "esrs-judgements", os.path.join(PATH_BASE, "judgements.json") ),
    ( "esrs-strategies", os.path.join(PATH_BASE, "strategies.json") ),
    ( "esrs-benchmarks", os.path.join(PATH_BASE, "benchmarks.json") ),
    ( "esrs-evaluations", os.path.join(PATH_BASE, "evaluations.json") )
]

def check():
    """
    Check if the esrs-* index templates and indices have been created.
    """
    result = {
        "failures": 0,
        "requests": []
    }
    for index_template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = None
        with open(path_index_template) as file:
            body = json.loads(file.read())
        name = body["index_patterns"][0].replace("*", "")
        
        # Check index template
        try:
            response = es("studio").indices.get_index_template(name=name)
            result["requests"].append({
                "index_template": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except (ApiError, NotFoundError) as e:
            result["failures"] += 1
            result["requests"].append({
                "index_template": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
        
        # Check index
        try:
            exists = es("studio").indices.exists(index=name)
            result["requests"].append({
                "index": name,
                "response": {
                    "body": "OK" if exists else "Not Found",
                    "status": 200 if exists else 404
                }
            })
            result["failures"] += 0 if exists else 1
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
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
    """
    result = {
        "failures": 0,
        "requests": []
    }
    for index_template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = None
        with open(path_index_template) as file:
            body = json.loads(file.read())
        name = body["index_patterns"][0].replace("*", "")
        
        # Create index template
        try:
            response = es("studio").indices.put_index_template(name=name, body=body)
            result["requests"].append({
                "index_template": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index_template": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
        
        # Create index
        try:
            response = es("studio").indices.create(index=name)
            result["requests"].append({
                "index": name,
                "response": {
                    "body": response.body,
                    "status": response.meta.status
                }
            })
        except RequestError as e:
            result["requests"].append({
                    "index": name,
                    "response": {
                        "body": e.body,
                        "status": e.meta.status
                    }
                })
            if e.error != "resource_already_exists_exception":
                result["failures"] += 1
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index": name,
                "response": {
                    "body": e.body,
                    "status": e.meta.status
                }
            })
    return result