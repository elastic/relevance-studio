# Standard packages
from types import SimpleNamespace

# Third-party packages
import pytest

# App packages
from server.api import benchmarks


class FakeClient:
    def __init__(self):
        self.operations = None

    def bulk(self, operations, refresh=True):
        self.operations = operations
        items = [{ "update": { "_id": op["update"]["_id"], "status": 200 }} for op in operations[::2]]
        return SimpleNamespace(body={ "took": 0, "errors": False, "items": items })


@pytest.fixture
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(benchmarks, "es", lambda _name: fake)
    monkeypatch.setattr(benchmarks.utils, "merge_bulk_results", lambda r, s, n: r)
    return fake


def update_doc(client, task):
    benchmarks.update([{ "_id": "b1", "workspace_id": "w1", "task": task }])
    return client.operations[1]["doc"]["task"]


def test_a_null_optimization_clears_the_stored_value(client):
    task = update_doc(client, { "optimization": None })
    assert "optimization" in task
    assert task["optimization"] is None


def test_null_latency_constraint_and_seeds_clear_stored_values(client):
    task = update_doc(client, { "optimization": {
        "algorithm": "grid",
        "latency_constraint": None,
        "seed": None,
        "holdout": { "ratio": 0.2, "seed": None },
    }})
    opt = task["optimization"]
    assert opt["latency_constraint"] is None
    assert opt["seed"] is None
    assert opt["holdout"] == { "ratio": 0.2, "seed": None }


def test_unset_fields_stay_unset(client):
    task = update_doc(client, { "optimization": { "algorithm": "random", "sample_size": 10 }})
    opt = task["optimization"]
    assert opt["algorithm"] == "random"
    assert "latency_constraint" not in opt
    assert "seed" not in opt


def test_an_update_without_optimization_leaves_it_alone(client):
    task = update_doc(client, { "requests": 5 })
    assert "optimization" not in task
