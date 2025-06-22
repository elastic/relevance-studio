# Standard packages
import logging
import random
import time

# Third-party packages
from dotenv import load_dotenv

# App packages
from . import api, utils
from .client import es

####  Configuration  ###########################################################

# Parse environment variables
load_dotenv()

POLL_INTERVAL = 5

logger = logging.getLogger('esrs.worker')
formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d [%(process)-6d] %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(handler)

def run_evaluation(evaluation):
    """
    Execute api.evaluations.run()
    """
    _id = evaluation['_id']
    logger.info(f"Running evaluation: {_id}")
    try:
        api.evaluations.run(evaluation, store_results=True)
    finally:
        logger.info(f"Finished evaluation: {_id}")

def claim_next_evaluation():
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
    
    # Handle pending evaluation
    evaluation = hits[0]["_source"]
    evaluation["_id"] = hits[0]["_id"]
    logger.debug(f"{response.meta.status} attempting to claim pending evaluation: {evaluation['_id']}")

    # Attempt to claim the pending evaluation (atomically)
    body = {
        "script": {
            "source": """
                if (ctx._source['@meta']?.status == 'pending' || ctx._source['@meta']?.status == 'pending') {
                    ctx._source['@meta'].status = 'running';
                    ctx._source['@meta'].started_at = params.now;
                } else {
                    ctx.op = 'none';
                }
            """,
            "params": {
                "now": utils.timestamp()
            }
        }
    }
    response = es("studio").options(ignore_status=404).update(
        index="esrs-evaluations",
        id=evaluation['_id'],
        body=body
    )
    
    # Handle failure to claim the pending evaluation (another worker claimed it)
    if response.get("result") == "noop":
        logger.debug(f"{response.meta.status} failed to claim pending evaluation: {evaluation['_id']}")
        return
    
    # Handle successful claim
    logger.debug(f"{response.meta.status} claimed pending evaluation: {evaluation['_id']}")
    return evaluation
        
        
####  Main  ####################################################################

def run_loop():
    logger.info("Running worker...")
    
    # Jitter delay to prevent many workers from polling at the same time
    time.sleep(random.uniform(0, POLL_INTERVAL))
    
    # Start main loop
    while True:
        evaluation = claim_next_evaluation()
        if evaluation:
            run_evaluation(evaluation)
        else:
            time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    run_loop()
