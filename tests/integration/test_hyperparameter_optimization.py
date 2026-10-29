import json
import time

import pytest
import requests

pytestmark = pytest.mark.integration_run

WORKSPACE_ID = "hpo-ws"
INDEX = "hpo-products"
WORDS = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet"]

# The `operator` search space includes a value that Elasticsearch rejects, so one
# variant fails to render a valid query.
TEMPLATE = json.dumps({
    "query": {
        "match": {
            "name": {
                "query": "{{ text }}",
                "operator": "{{ hp.operator }}",
                "boost": "{{ hp.boost }}",
            }
        }
    }
}).replace('"{{ hp.boost }}"', "{{ hp.boost }}")


def call(services, method, path, **kwargs):
    response = requests.request(method, f"{services['esrs']}{path}", timeout=120, **kwargs)
    return response.status_code, response.json()


def api(services, method, path, body=None, **params):
    return call(services, method, f"/api/workspaces/{WORKSPACE_ID}{path}", json=body, params=params)


def wait_for_run(services, benchmark_id, run_id, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        status, run = api(services, "GET", f"/benchmarks/{benchmark_id}/runs/{run_id}")
        assert status == 200, run
        state = run["_source"]["@meta"]["status"]
        if state in ("completed", "failed", "skipped"):
            return run["_source"]
        time.sleep(2)
    raise AssertionError("run did not finish in time")


@pytest.fixture(scope="module")
def workspace(services):
    es = services["es"]
    requests.post(f"{services['esrs']}/api/setup", timeout=120)
    es.options(ignore_status=[404]).indices.delete(index=INDEX)
    for i, word in enumerate(WORDS):
        es.index(index=INDEX, id=f"{word}-1", document={"name": f"{word} shirt cotton"})
        es.index(index=INDEX, id=f"{word}-2", document={"name": f"{word} shoes"})
        es.index(index=INDEX, id=f"other-{i}", document={"name": "cotton socks"})
    es.indices.refresh(index=INDEX)

    status, body = call(services, "POST", "/api/workspaces", json={
        "_id": WORKSPACE_ID, "name": "HPO", "index_pattern": INDEX, "params": ["text"],
        "rating_scale": { "min": 0, "max": 3 }, "tags": [],
    })
    assert status in (200, 201), body
    for word in WORDS:
        status, body = api(services, "POST", "/scenarios", {
            "name": word, "values": { "text": word }, "tags": [],
        })
        assert status in (200, 201), body
        scenario_id = body["_id"]
        for doc_id, rating in ((f"{word}-1", 3), (f"{word}-2", 1)):
            status, body = api(services, "PUT", "/judgements", {
                "scenario_id": scenario_id, "index": INDEX, "doc_id": doc_id, "rating": rating,
            })
            assert status in (200, 201), body
    status, body = api(services, "POST", "/strategies", {
        "_id": "hpo-strategy", "name": "HPO", "tags": ["hpo"],
        "template": { "lang": "mustache", "source": TEMPLATE },
        "hyperparameters": [
            { "name": "operator", "type": "string", "promoted_value": "or",
              "testable_values": { "type": "set", "values": ["or", "and", "xor"] }},
            { "name": "boost", "type": "number", "promoted_value": 1.0,
              "testable_values": { "type": "range", "min": 1, "max": 3 }},
        ],
    })
    assert status in (200, 201), body
    yield
    es.options(ignore_status=[404]).indices.delete(index=INDEX)


def task(**optimization):
    return {
        "k": 10,
        "metrics": ["ndcg", "recall"],
        "scenarios": { "_ids": [], "tags": [], "sample_size": 1000 },
        "strategies": { "_ids": ["hpo-strategy"], "tags": [], "docs": [] },
        "optimization": {
            "algorithm": "grid",
            "values_to_test": [
                { "name": "boost", "values": { "type": "range", "min": 1, "max": 3, "step": 1 }},
            ],
            "objective": { "metric": "ndcg", "aggregation": "mean" },
            "holdout": { "ratio": 0.3 },
            **optimization,
        },
    }


def test_render_and_estimate(services, workspace):
    status, rendered = api(services, "POST", "/strategies/_render", {
        "_id": "hpo-strategy", "values": { "operator": "and", "boost": 2 },
    })
    assert status == 200, rendered
    assert '"operator": "and"' in rendered["source"]
    assert "{{ text }}" in rendered["source"]

    status, estimate = api(services, "POST", "/benchmarks/_estimate", { "task": task(), "probe": True })
    assert status == 200, estimate
    assert estimate["errors"] == []
    assert estimate["variants"] == 9  # 3 operators x 3 boosts, baseline included
    assert estimate["scenarios"]["tuning"] + estimate["scenarios"]["holdout"] == 10
    assert estimate["scenarios"]["holdout"] == 3
    assert estimate["duration"]["high_ms"] > 0


def test_dry_run_creates_no_run(services, workspace):
    status, benchmark = api(services, "POST", "/benchmarks", {
        "_id": "hpo-benchmark", "name": "HPO", "tags": [], "task": task(),
    })
    assert status in (200, 201), benchmark
    status, estimate = api(services, "POST", "/benchmarks/hpo-benchmark/runs", task(), dry_run="true")
    assert status == 200, estimate
    assert estimate["variants"] == 9
    status, runs = api(services, "POST", "/benchmarks/hpo-benchmark/runs/_search", { "size": 10 })
    assert runs["hits"]["total"]["value"] == 0


def test_run_picks_winner_isolates_invalid_variant_and_promotes(services, workspace):
    status, created = api(services, "POST", "/benchmarks/hpo-benchmark/runs", task())
    assert status in (200, 201), created
    run_id = created["_id"]
    run = wait_for_run(services, "hpo-benchmark", run_id)
    assert run["@meta"]["status"] == "completed", run.get("error")

    base = f"/benchmarks/hpo-benchmark/runs/{run_id}"
    status, variants = api(services, "GET", f"{base}/variants", strategy_id="hpo-strategy", size=50)
    assert status == 200, variants
    assert variants["total"] == 9
    items = variants["items"]
    invalid = [v for v in items if v["values"]["operator"] == "xor"]
    valid = [v for v in items if v["values"]["operator"] != "xor"]

    # The invalid variants fail alone. The rest still get scores.
    assert len(invalid) == 3 and all(v["score"] is None for v in invalid)
    assert len(valid) == 6 and all(v["score"] is not None for v in valid)
    winners = [v for v in items if v["is_winner"]]
    assert len(winners) == 1 and winners[0]["values"]["operator"] != "xor"
    assert winners[0]["rank"] == 1

    # Only the winner and the baseline variant run on the holdout.
    status, holdout = api(services, "GET", f"{base}/results", split="holdout", strategy_id="hpo-strategy")
    assert status == 200
    holdout_variants = { r["variant_id"] for r in holdout["items"] }
    expected = { winners[0]["variant_id"], *[v["variant_id"] for v in items if v["is_baseline"]] }
    assert holdout_variants == expected
    assert holdout["total"] == len(expected) * 3

    status, summary = api(services, "GET", f"{base}/optimization_summary")
    assert status == 200, summary
    assert summary["score_basis"] == "holdout"
    assert summary["strategies"][0]["winner"]["variant_id"] == winners[0]["variant_id"]

    # Promote the winner into the promoted values of the strategy.
    status, promoted = api(services, "POST", "/strategies/_promote", {
        "run_id": run_id, "variant_id": winners[0]["variant_id"], "mode": "update_values",
    })
    assert status == 200, promoted
    status, strategy = api(services, "GET", "/strategies/hpo-strategy")
    promoted_values = { h["name"]: h["promoted_value"] for h in strategy["_source"]["hyperparameters"] }
    assert promoted_values == winners[0]["values"]
    assert strategy["_source"]["promoted_from"]["run_id"] == run_id


def test_random_search_without_holdout(services, workspace):
    status, created = api(services, "POST", "/benchmarks/hpo-benchmark/runs", task(
        algorithm="random", sample_size=4, seed="s1", holdout={ "ratio": 0 },
        latency_constraint={ "stat": "p90", "max_ms": 60000 },
    ))
    assert status in (200, 201), created
    run = wait_for_run(services, "hpo-benchmark", created["_id"])
    assert run["@meta"]["status"] == "completed", run.get("error")
    status, variants = api(
        services, "GET", f"/benchmarks/hpo-benchmark/runs/{created['_id']}/variants",
        strategy_id="hpo-strategy",
    )
    assert variants["total"] == 4
    assert run["task"]["optimization"]["seed"] == "s1"
