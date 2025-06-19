# Standard packages
import os
import subprocess
import time
from typing import Any, Dict, Generator, Union

# Third-party packages
import pytest
import requests

# Elastic packages
from elasticsearch import Elasticsearch, ConnectionError

# Config
DOCKER_COMPOSE_FILE = os.path.join("tests", "docker-compose.yml")
ES_URL = "http://localhost:9200"
ESRS_URL = "http://localhost:4096"
ESRS_INDICES = [
    "esrs-projects",
    "esrs-displays",
    "esrs-scenarios",
    "esrs-judgements",
    "esrs-strategies",
    "esrs-benchmarks",
    "esrs-evaluations",
] 

def wait_for_es(url, attempts=30):
    """
    Start Elasticsearch test cluster.
    """
    es_client = Elasticsearch(url, request_timeout=4000)
    for _ in range(attempts):
        try:
            if es_client.ping():
                return es_client
        except ConnectionError:
            pass
        time.sleep(1)
    raise RuntimeError("Elasticsearch did not start in time")

def wait_for_esrs(url, attempts=30):
    """
    Start the Elasticsearch Relevance Studio test server.
    """
    for _ in range(attempts):
        try:
            r = requests.get(url)
            if r.status_code == 200:
                return ESRS_URL
        except requests.exceptions.ConnectionError:
            time.sleep(1)
    raise RuntimeError("Server did not start in time")

@pytest.fixture(scope="session")
def services() -> Generator[Dict[str, Union[Elasticsearch, str]], None, None]:
    """
    Setup and teardown the Elasticsearch Relevance Studio test server and the
    Elasticsearch test cluster with docker compose.
    """
    subprocess.run(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "up", "--build", "-d"], check=True)
    try:
        yield {
            "es": wait_for_es(ES_URL),
            "esrs": wait_for_esrs(ESRS_URL),
        }
    finally:
        subprocess.run(["docker", "compose", "-f", DOCKER_COMPOSE_FILE, "down", "-v"], check=True)
        
@pytest.fixture(scope="session")
def constants() -> Dict[str, Any]:
    """
    Constant values available to each test. 
    """
    return {
        "index_templates": ESRS_INDICES
    }
    
def delete_index_templates(es, index_templates):
    """
    Delete esrs-* indices and index templates.
    """
    es.options(ignore_status=[404]).indices.delete(index="esrs-*")
    for name in index_templates:
        es.options(ignore_status=[404]).indices.delete_template(name=name)
        
@pytest.fixture(scope="session")
def wipe_data(services, constants, request):
    """
    Fixture to delete esrs-* indices and index templates.
    """
    # Skip if test is marked with @pytest.mark.no_wipe_data
    if request.node.get_closest_marker("no_wipe_data"):
        yield
        return
    delete_index_templates(services["es"], constants["index_templates"])
    yield
        
@pytest.fixture(scope="session")
def clean_data(services, constants, request):
    """
    Fixture to delete esrs-* indices and index templates, and then setup
    esrs-* index templates.
    """
    # Skip if test is marked with @pytest.mark.no_wipe_data
    if request.node.get_closest_marker("no_wipe_data"):
        yield
        return
    delete_index_templates(services["es"], constants["index_templates"])
    requests.post(f"{services['esrs']}/setup")
    yield