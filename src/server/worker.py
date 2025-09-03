# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

# Standard packages
import logging
import os
import random
import time
from socket import gethostname
from uuid import uuid4

# Third-party packages
from dotenv import load_dotenv

# Elastic packages
from elasticsearch import NotFoundError

# App packages
from . import api, utils
from .client import es

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

# Conditionally instrument OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
OTEL_ENABLED = bool(OTEL_EXPORTER_OTLP_ENDPOINT)
if OTEL_ENABLED:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.elasticsearch import ElasticsearchInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import SpanKind

    # Set a default service name if not provided
    os.environ.setdefault("OTEL_SERVICE_NAME", "esrs-worker")
    
    # Ensure endpoint is correctly configured
    if not OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/").endswith("/v1/traces"):
        OTEL_EXPORTER_OTLP_ENDPOINT = OTEL_EXPORTER_OTLP_ENDPOINT.rstrip("/") + "/v1/traces"

    # Create tracer provider with resource attributes
    resource = Resource.create({ "service.name": os.environ["OTEL_SERVICE_NAME"].strip() })
    provider = TracerProvider(resource=resource)

    # Export traces via OTLP/HTTP
    exporter = OTLPSpanExporter(
        endpoint=OTEL_EXPORTER_OTLP_ENDPOINT,
        headers=dict(
            h.split("=", 1) for h in os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "").strip().split(",", 1) if "=" in h
        )
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))

    # Set global tracer provider
    trace.set_tracer_provider(provider)

    # Instrument Elasticsearch client
    ElasticsearchInstrumentor().instrument()

    # Get a tracer for manual spans
    tracer = trace.get_tracer(__name__)

WORKER_CLEANUP_INTERVAL = os.getenv("WORKER_CLEANUP_INTERVAL") or 60
WORKER_CLEANUP_TIME_RANGE = os.getenv("WORKER_CLEANUP_TIME_RANGE") or "2h"
WORKER_POLLING_INTERVAL = os.getenv("WORKER_POLLING_INTERVAL") or 5
WORKER_ID = f"{gethostname()}-{uuid4().hex[:8]}"

logger = logging.getLogger("esrs.worker")
formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d [%(process)-6d] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

def _cleanup():
    try:
        logger.info("Cleaning up any stale evaluations...")
        return api.evaluations.cleanup(WORKER_CLEANUP_TIME_RANGE)
    except NotFoundError as e:
        logger.debug(f"{e.meta.status} {e.body['error']['reason']}")
    except Exception as e:
        logger.exception(e)

def _run_evaluation(evaluation):
    """
    Execute api.evaluations.run()
    """
    _id = evaluation["_id"]
    logger.info(f"Running evaluation: {_id}")
    try:
        return api.evaluations.run(evaluation, store_results=True, started_by=WORKER_ID)
    finally:
        logger.info(f"Finished evaluation: {_id}")
        
def _claim_evaluation(evaluation):
    """
    Attempt to claim a pending evaluation.
    """
    
    # Handle pending evaluation
    logger.debug(f"Attempting to claim pending evaluation: {evaluation['_id']}")

    # Attempt to claim the pending evaluation (atomically)
    body = {
        "script": {
            "source": """
                if (ctx._source['@meta']?.status == 'pending') {
                    ctx._source['@meta'].status = 'running';
                    ctx._source['@meta'].started_at = params.now;
                    ctx._source['@meta'].started_by = params.started_by;
                } else {
                    ctx.op = 'none';
                }
            """,
            "params": {
                "now": utils.timestamp(),
                "started_by": WORKER_ID
            }
        }
    }
    response = es("studio").update(
        index="esrs-evaluations",
        id=evaluation['_id'],
        body=body
    )    
    if response.get("result") == "noop":
        logger.debug(f"{response.meta.status} failed to claim pending evaluation: {evaluation['_id']}") # another worker claimed it
    else:
        logger.debug(f"{response.meta.status} claimed pending evaluation: {evaluation['_id']}")
    return response

def _poll_evaluations():
    """
    Check for the oldest pending evaluation and claim it.
    """
    
    logger.debug("Checking for oldest pending evaluation...")
    
    # Find the oldest pending evaluation
    body = {
        "size": 1,
        "query": { "term": { "@meta.status": "pending" }},
        "sort": [{ "@meta.created_at": "asc" }]
    }
    response = es("studio").options(ignore_status=404).search(
        index="esrs-evaluations",
        body=body
    )
    
    # Handle unexpected responses
    if response.meta.status != 200:
        if response.body.get("error"):
            logger.debug(f"{response.meta.status} {response.body['error'].get('reason')}")
        else:
            logger.debug(f"{response.meta.status} {utils.serialize(response.body)}")
        return
    
    # Handle no hits
    hits = response.get("hits", {}).get("hits") or []
    if not hits:
        logger.debug(f"{response.meta.status} no hits")
        return
    
    # Return evaluation if found
    evaluation = hits[0]["_source"]
    evaluation["_id"] = hits[0]["_id"]
    logger.debug(f"{response.meta.status} found oldest pending evaluation: {evaluation['_id']}")
    return evaluation
    
def cleanup():
    if not OTEL_ENABLED:
        return _cleanup()
    with tracer.start_as_current_span("cleanup", kind=SpanKind.CONSUMER) as tx:
        tx.set_attribute("worker.id", WORKER_ID)
        return _cleanup()

def run_evaluation(evaluation):
    if not OTEL_ENABLED:
        return _run_evaluation(evaluation)
    with tracer.start_as_current_span("run_evaluation", kind=SpanKind.CONSUMER) as tx:
        tx.set_attribute("worker.id", WORKER_ID)
        return _run_evaluation(evaluation)

def claim_evaluation(evaluation):
    if not OTEL_ENABLED:
        return _claim_evaluation(evaluation)
    with tracer.start_as_current_span("claim_evaluation", kind=SpanKind.CONSUMER) as tx:
        tx.set_attribute("worker.id", WORKER_ID)
        return _claim_evaluation(evaluation)

def poll_evaluations():
    if not OTEL_ENABLED:
        return _poll_evaluations()
    with tracer.start_as_current_span("poll_evaluations", kind=SpanKind.CONSUMER) as tx:
        tx.set_attribute("worker.id", WORKER_ID)
        return _poll_evaluations()
        
        
####  Main  ####################################################################

def run_loop():
    logger.info(f"Running worker: {WORKER_ID}")
    
    # Jitter delay to prevent many workers from polling at the same time
    time.sleep(random.uniform(0, WORKER_POLLING_INTERVAL))
    
    # Track when the worker last cleaned up stale evaluations
    time_last_cleanup = None
    
    # Start main loop
    while True:
        
        # Check evaluations
        try:
            evaluation = poll_evaluations()
            if evaluation:
                # Attempt to claim and run a pending evaluation
                claim_evaluation(evaluation)
                run_evaluation(evaluation)
        except Exception as e:
            logger.exception(e)
        finally:
            time.sleep(WORKER_POLLING_INTERVAL)
            
        # Periodically clean up stale evaluations
        if not time_last_cleanup or time.time() - time_last_cleanup > WORKER_CLEANUP_INTERVAL:
            cleanup()
            time_last_cleanup = time.time()

if __name__ == "__main__":
    run_loop()