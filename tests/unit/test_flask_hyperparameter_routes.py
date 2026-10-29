# Third-party packages
import pytest

# App packages
from server import auth
from server.flask import app

WS = "58278355-f4f3-56d2-aa81-498250f27798"
SOURCE = '{"q":"{{text}}","boost":{{hp.boost}}}'
HPS = [{ "name": "boost", "type": "number", "promoted_value": 2.0, "testable_values": { "type": "range", "min": 0 }}]


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(auth, "AUTH_ENABLED", False)
    monkeypatch.setattr("server.flask.es", lambda _: object())
    return app.test_client()


def test_render_route_applies_values(client):
    r = client.post(f"/api/workspaces/{WS}/strategies/_render", json={
        "template": { "source": SOURCE }, "hyperparameters": HPS, "values": { "boost": 5 },
    })
    assert r.status_code == 200
    assert r.get_json()["source"] == '{"q":"{{text}}","boost":5}'


def test_render_route_invalid_input_is_a_400(client):
    r = client.post(f"/api/workspaces/{WS}/strategies/_render", json={
        "template": { "source": SOURCE }, "hyperparameters": [],
    })
    assert r.status_code == 400
    assert "undefined" in r.get_json()["message"]


def test_promote_route_requires_run_and_variant(client):
    r = client.post(f"/api/workspaces/{WS}/strategies/_promote", json={ "run_id": "r" })
    assert r.status_code == 400
    assert "variant_id" in r.get_json()["message"]


def test_promote_route_passes_arguments_through(client, monkeypatch):
    seen = {}
    def fake_promote(run_id, variant_id, **kwargs):
        seen.update(run_id=run_id, variant_id=variant_id, **kwargs)
        return { "strategy_id": "s1" }
    monkeypatch.setattr("server.flask.api.strategies.promote", fake_promote)
    r = client.post(f"/api/workspaces/{WS}/strategies/_promote", json={
        "run_id": "r", "variant_id": "v", "mode": "fork", "name": "N", "strategy_id": "s",
    })
    assert r.status_code == 200
    assert seen["mode"] == "fork" and seen["name"] == "N" and seen["strategy_id"] == "s"
    assert seen["via"] == "server"


def test_estimate_route_validates_the_task(client):
    r = client.post(f"/api/workspaces/{WS}/benchmarks/_estimate", json={
        "task": { "optimization": { "algorithm": "bayesian" }},
    })
    assert r.status_code == 400


def test_estimate_route_returns_the_estimate(client, monkeypatch):
    monkeypatch.setattr("server.flask.api.runs.estimate", lambda ws, task, probe=False: {
        "workspace": ws, "probe": probe, "task": task,
    })
    r = client.post(f"/api/workspaces/{WS}/benchmarks/_estimate", json={ "task": { "k": 5 }, "probe": True })
    assert r.get_json() == { "workspace": WS, "probe": True, "task": { "k": 5 }}


def test_variants_route_builds_the_objective_from_query_params(client, monkeypatch):
    seen = {}
    def fake(run_id, strategy_id, **kwargs):
        seen.update(run_id=run_id, strategy_id=strategy_id, **kwargs)
        return { "items": [] }
    monkeypatch.setattr("server.flask.api.runs.get_variants", fake)
    url = f"/api/workspaces/{WS}/benchmarks/b/runs/r/variants"
    assert client.get(url).status_code == 400  # strategy_id is required
    r = client.get(url + "?strategy_id=s&objective_metric=mrr&constraint_max_ms=50&sort=hp:boost&descending=true&size=5")
    assert r.status_code == 200
    assert seen["objective"] == { "metric": "mrr", "aggregation": "mean" }
    assert seen["latency_constraint"] == { "stat": "median", "max_ms": 50.0 }
    assert seen["sort"] == "hp:boost" and seen["descending"] is True and seen["size"] == 5
    assert client.get(url + "?strategy_id=s&constraint_max_ms=abc").status_code == 400


def test_optimization_summary_route(client, monkeypatch):
    monkeypatch.setattr("server.flask.api.runs.get_optimization_summary", lambda run_id, top_n=5: {
        "run_id": run_id, "top_n": top_n,
    })
    r = client.get(f"/api/workspaces/{WS}/benchmarks/b/runs/r/optimization_summary?top_n=3")
    assert r.get_json() == { "run_id": "r", "top_n": 3 }


def test_create_run_dry_run_flag(client, monkeypatch):
    seen = {}
    def fake(ws, benchmark_id, task, user=None, via=None, dry_run=False):
        seen["dry_run"] = dry_run
        return { "ok": True }
    monkeypatch.setattr("server.flask.api.runs.create", fake)
    client.post(f"/api/workspaces/{WS}/benchmarks/b/runs?dry_run=true", json={ "metrics": ["ndcg"] })
    assert seen["dry_run"] is True
    client.post(f"/api/workspaces/{WS}/benchmarks/b/runs", json={ "metrics": ["ndcg"] })
    assert seen["dry_run"] is False
