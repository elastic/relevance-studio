# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
from typing import Dict, Optional, Union
import os
from contextvars import ContextVar

# Third-party packages
from dotenv import load_dotenv

# Elastic packages
from elasticsearch import Elasticsearch

# Parse environment variables
load_dotenv()
ELASTIC_CLOUD_ID = os.getenv("ELASTIC_CLOUD_ID", "").strip()
ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "").strip()
ELASTICSEARCH_API_KEY = os.getenv("ELASTICSEARCH_API_KEY", "").strip()
ELASTICSEARCH_USERNAME = os.getenv("ELASTICSEARCH_USERNAME", "").strip()
ELASTICSEARCH_PASSWORD = os.getenv("ELASTICSEARCH_PASSWORD", "").strip()
AUTH_ENABLED = os.getenv("AUTH_ENABLED", "true").strip().lower() in ("true", "1", "yes")
CONTENT_ELASTIC_CLOUD_ID = os.getenv("CONTENT_ELASTIC_CLOUD_ID", "").strip()
CONTENT_ELASTICSEARCH_URL = os.getenv("CONTENT_ELASTICSEARCH_URL", "").strip()
CONTENT_ELASTICSEARCH_API_KEY = os.getenv("CONTENT_ELASTICSEARCH_API_KEY", "").strip()
CONTENT_ELASTICSEARCH_USERNAME = os.getenv("CONTENT_ELASTICSEARCH_USERNAME", "").strip()
CONTENT_ELASTICSEARCH_PASSWORD = os.getenv("CONTENT_ELASTICSEARCH_PASSWORD", "").strip()
ELASTICSEARCH_MAX_RETRIES = int(os.getenv("ELASTICSEARCH_MAX_RETRIES", "3").strip())
ELASTICSEARCH_TIMEOUT = int(os.getenv("ELASTICSEARCH_TIMEOUT", "10").strip()) # seconds

# Singleton Elasticsearch clients
_es_clients = None
_valid_es_clients = set([ "studio", "content", ])

# Request-scoped client overrides for multi-user authentication
_request_studio_client: ContextVar[Optional[Elasticsearch]] = ContextVar("_request_studio_client", default=None)
_request_content_client: ContextVar[Optional[Elasticsearch]] = ContextVar("_request_content_client", default=None)


def set_request_clients(studio_client: Optional[Elasticsearch], content_client: Optional[Elasticsearch] = None) -> None:
    """
    Set the Elasticsearch clients for the current request context.
    If content_client is not provided, it will be determined based on whether
    the content deployment is separate from the studio deployment.
    """
    _request_studio_client.set(studio_client)
    
    if content_client:
        _request_content_client.set(content_client)
    elif studio_client:
        # If no explicit content client is provided, we use the studio client
        # ONLY if the deployments are shared.
        global _es_clients
        
        # Check if they are shared. We prefer checking the already-initialized 
        # singletons if available, to support mocking in tests.
        if _es_clients is not None:
            is_shared = (_es_clients["studio"] == _es_clients["content"])
        else:
            # Otherwise check environment variables directly to avoid eager 
            # initialization of singletons (which might fail if config is missing).
            is_shared = (not CONTENT_ELASTIC_CLOUD_ID and not CONTENT_ELASTICSEARCH_URL)
            
        if is_shared:
            _request_content_client.set(studio_client)
        else:
            _request_content_client.set(None) # Fall back to content singleton
    else:
        _request_studio_client.set(None)
        _request_content_client.set(None)


def _validate_endpoint_configuration() -> None:
    if ELASTIC_CLOUD_ID and ELASTICSEARCH_URL:
        raise ValueError("Configure either ELASTIC_CLOUD_ID or ELASTICSEARCH_URL, not both.")
    if CONTENT_ELASTIC_CLOUD_ID and CONTENT_ELASTICSEARCH_URL:
        raise ValueError("Configure either CONTENT_ELASTIC_CLOUD_ID or CONTENT_ELASTICSEARCH_URL, not both.")


def es_studio_endpoint() -> Dict[str, Union[str, list]]:
    """
    Return endpoint configuration for the studio deployment without credentials.
    Prefers cloud_id when available, else url (hosts).
    """
    _validate_endpoint_configuration()
    if ELASTIC_CLOUD_ID:
        return {"cloud_id": ELASTIC_CLOUD_ID}
    if ELASTICSEARCH_URL:
        return {"hosts": [ELASTICSEARCH_URL]}
    raise ValueError("You must configure either ELASTIC_CLOUD_ID or ELASTICSEARCH_URL in .env")


def es_from_credentials(
    *,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    password: Optional[str] = None,
    cloud_id: Optional[str] = None,
    url: Optional[str] = None,
) -> Elasticsearch:
    """
    Construct an Elasticsearch client for the studio endpoint using the given credentials.
    Prefers cloud_id when available, else url.
    Raises ValueError when no credentials are provided.
    """
    if api_key and (username or password):
        raise ValueError("Provide either api_key or username/password, not both.")
    if not api_key and not (username and password):
        raise ValueError("You must provide either api_key or both username and password.")
    if not cloud_id and not url:
        endpoint = es_studio_endpoint()
        cloud_id = endpoint.get("cloud_id")
        url = endpoint.get("hosts", [None])[0] if endpoint.get("hosts") else None
    if not cloud_id and not url:
        raise ValueError("You must configure either ELASTIC_CLOUD_ID or ELASTICSEARCH_URL (or pass cloud_id/url).")
    kwargs = {
        "headers": {
            "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
            "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
        },
        "max_retries": ELASTICSEARCH_MAX_RETRIES,
        "retry_on_timeout": True,
        "request_timeout": ELASTICSEARCH_TIMEOUT
    }
    if cloud_id:
        kwargs["cloud_id"] = cloud_id
    else:
        kwargs["hosts"] = [url]
    if api_key:
        kwargs["api_key"] = api_key
    else:
        kwargs["basic_auth"] = (username, password)
    return Elasticsearch(**kwargs)


def es(client_name: str) -> Elasticsearch:
    """
    Return the appropriate Elasticsearch client for the given name.
    Prefers the request-scoped client if available, otherwise returns the singleton.
    """
    if client_name not in _valid_es_clients:
        raise Exception(f"'{client_name}' is not a valid Elasticsearch client.")
    
    # Check for request-scoped override
    if client_name == "studio":
        req = _request_studio_client.get()
        if req: return req
    elif client_name == "content":
        req = _request_content_client.get()
        if req: return req

    # Fall back to singletons
    global _es_clients
    if _es_clients is None:
        _es_clients = _setup_clients()
    return _es_clients[client_name]

def _setup_clients() -> Dict[str, Elasticsearch]:
    """
    Create two Elasticsearch clients:
    
        1. "studio" connects to the deployment with esrs-* indices
        2. "content" connects to the deployment with source indices
        
    This function is called automatically by es(). es() is intended to be the
    only way to access the clients, including for their initial setup.
    """

    # Validate configuration
    _validate_endpoint_configuration()
    if not ELASTIC_CLOUD_ID and not ELASTICSEARCH_URL:
        raise ValueError("You must configure either ELASTIC_CLOUD_ID or ELASTICSEARCH_URL in .env")
    if ELASTICSEARCH_API_KEY and (ELASTICSEARCH_USERNAME or ELASTICSEARCH_PASSWORD):
        raise ValueError("Configure either ELASTICSEARCH_API_KEY or ELASTICSEARCH_USERNAME/ELASTICSEARCH_PASSWORD, not both.")
    if (ELASTICSEARCH_USERNAME and not ELASTICSEARCH_PASSWORD) or (not ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD):
        raise ValueError("You must configure both of ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD in .env")
    if (CONTENT_ELASTICSEARCH_USERNAME and not CONTENT_ELASTICSEARCH_PASSWORD) or (not CONTENT_ELASTICSEARCH_USERNAME and CONTENT_ELASTICSEARCH_PASSWORD):
        raise ValueError("You must configure both of CONTENT_ELASTICSEARCH_USERNAME and CONTENT_ELASTICSEARCH_PASSWORD in .env")
    if CONTENT_ELASTIC_CLOUD_ID or CONTENT_ELASTICSEARCH_URL:
        if CONTENT_ELASTICSEARCH_API_KEY and (CONTENT_ELASTICSEARCH_USERNAME or CONTENT_ELASTICSEARCH_PASSWORD):
            raise ValueError(f"When using {CONTENT_ELASTIC_CLOUD_ID or CONTENT_ELASTICSEARCH_URL}, configure either CONTENT_ELASTICSEARCH_API_KEY or CONTENT_ELASTICSEARCH_USERNAME/CONTENT_ELASTICSEARCH_PASSWORD, not both.")

    # Setup Elasticsearch clients
    es_clients = {
        "studio": None, # for the deployment with the esrs-* indices
        "content": None # for the deployment with the source content to be judged and evaluated
    }

    # Setup client for deployment with Elasticsearch Relevance Studio
    es_studio_kwargs = {
        "headers": {
            "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
            "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
        },
        "max_retries": ELASTICSEARCH_MAX_RETRIES,
        "retry_on_timeout": True,
        "request_timeout": ELASTICSEARCH_TIMEOUT
    }
    if ELASTIC_CLOUD_ID:
        es_studio_kwargs["cloud_id"] = ELASTIC_CLOUD_ID
    else:
        es_studio_kwargs["hosts"] = [ ELASTICSEARCH_URL ]
    if ELASTICSEARCH_API_KEY:
        es_studio_kwargs["api_key"] = ELASTICSEARCH_API_KEY
    elif ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD:
        es_studio_kwargs["basic_auth"] = (
            ELASTICSEARCH_USERNAME,
            ELASTICSEARCH_PASSWORD
        )
    es_clients["studio"] = Elasticsearch(**es_studio_kwargs)

    # Setup client for deployment with source content
    if not CONTENT_ELASTIC_CLOUD_ID and not CONTENT_ELASTICSEARCH_URL:
        es_clients["content"] = es_clients["studio"]
    else:
        es_content_kwargs = {
            "headers": {
                "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
                "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8"
            },
            "max_retries": ELASTICSEARCH_MAX_RETRIES,
            "retry_on_timeout": True,
            "request_timeout": ELASTICSEARCH_TIMEOUT
        }
        if CONTENT_ELASTIC_CLOUD_ID:
            es_content_kwargs["cloud_id"] = CONTENT_ELASTIC_CLOUD_ID
        else:
            es_content_kwargs["hosts"] = [ CONTENT_ELASTICSEARCH_URL ]
        if CONTENT_ELASTICSEARCH_API_KEY:
            es_content_kwargs["api_key"] = CONTENT_ELASTICSEARCH_API_KEY
        elif CONTENT_ELASTICSEARCH_USERNAME and CONTENT_ELASTICSEARCH_PASSWORD:
            es_content_kwargs["basic_auth"] = (
                CONTENT_ELASTICSEARCH_USERNAME,
                CONTENT_ELASTICSEARCH_PASSWORD
            )
        es_clients["content"] = Elasticsearch(**es_content_kwargs)
    return es_clients