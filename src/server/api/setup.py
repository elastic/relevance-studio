# Standard packages
import json
import os

# Elastic packages
from elasticsearch.exceptions import ApiError

# App packages
from ..client import es

def run():
    """
    Setup index templates.
    
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
            ...
        ]
    }
    """
    path_base = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "elastic", "index_templates"
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
            response = es("studio").indices.put_template(name=name, body=body)
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
    return result