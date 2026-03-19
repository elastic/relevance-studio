import json

import pytest
import requests

from server.api import setup as setup_api

pytestmark = pytest.mark.integration_setup

# Placeholder roadmap for future integration suites.
# Suggested follow-up files:
# - tests/integration/test_workspaces_flow.py
# - tests/integration/test_displays_flow.py
# - tests/integration/test_scenarios_flow.py
# - tests/integration/test_strategies_flow.py
# - tests/integration/test_judgements_flow.py
# - tests/integration/test_benchmarks_flow.py
# - tests/integration/test_evaluations_flow.py
# - tests/integration/test_conversations_flow.py
#
# Suggested progression:
# 1) setup/upgrade (this file)
# 2) workspaces
# 3) displays
# 4) scenarios
# 5) strategies
# 6) judgements
# 7) benchmarks
# 8) evaluations
# Parallel from setup: conversations


def reset_esrs(es):
    """Reset all studio state used by setup/upgrade flows."""
    es.options(ignore_status=[404]).indices.delete(index="esrs-*")
    es.options(ignore_status=[404]).indices.delete(index="esrs-system")
    for template_name, _ in setup_api.PATH_INDEX_TEMPLATES:
        es.options(ignore_status=[404]).indices.delete_index_template(name=template_name)


def load_template(path):
    with open(path) as file:
        return json.loads(file.read())


def seed_legacy_v1_state(es):
    """Seed a v1.0-like deployment state before the v1.1 additive upgrade."""
    for template_name, path in setup_api.PATH_INDEX_TEMPLATES:
        if template_name == "esrs-conversations":
            # New in v1.1.0; legacy state should not have this template/index.
            continue

        body = load_template(path)
        body.setdefault("_meta", {}).pop("version", None)

        if template_name == "esrs-workspaces":
            properties = body["template"]["mappings"]["properties"]
            properties.pop("description", None)
            search_properties = properties.get("_search", {}).get("properties", {})
            search_properties.pop("description", None)

        index_name = body["index_patterns"][0].replace("*", "")
        es.indices.put_index_template(name=template_name, body=body)
        es.indices.create(index=index_name)


def setup_check(services):
    response = requests.get(f"{services['esrs']}/api/setup")
    assert response.status_code == 200, response.text
    return response.json()


def run_setup(services):
    response = requests.post(f"{services['esrs']}/api/setup")
    assert response.status_code == 200, response.text
    return response.json()


def run_upgrade(services):
    response = requests.post(f"{services['esrs']}/api/upgrade")
    assert response.status_code == 200, response.text
    return response.json()


def test_setup_bootstrap_then_no_upgrade_needed(services):
    reset_esrs(services["es"])

    setup_result = run_setup(services)
    assert setup_result["setup"]["failures"] == 0

    state = setup_check(services)
    assert state["setup"]["failures"] == 0
    assert state["setup"]["upgrade_only_failures"] is False
    assert state["upgrade"]["upgrade_needed"] is False


def test_legacy_state_reports_upgrade_required_not_setup_required(services):
    reset_esrs(services["es"])
    seed_legacy_v1_state(services["es"])

    state = setup_check(services)
    assert state["setup"]["failures"] > 0
    assert state["setup"]["upgrade_only_failures"] is True
    assert state["upgrade"]["upgrade_needed"] is True

    pending_templates = {step["template"] for step in state["upgrade"]["pending_steps"]}
    assert "esrs-conversations" in pending_templates
    assert "esrs-workspaces" in pending_templates


def test_upgrade_run_is_idempotent_and_clears_pending_upgrades(services):
    reset_esrs(services["es"])
    seed_legacy_v1_state(services["es"])

    first_upgrade = run_upgrade(services)
    assert first_upgrade["upgrade"]["failures"] == 0

    second_upgrade = run_upgrade(services)
    assert second_upgrade["upgrade"]["failures"] == 0

    state = setup_check(services)
    assert state["setup"]["failures"] == 0
    assert state["upgrade"]["upgrade_needed"] is False
    assert state["upgrade"]["pending_steps"] == []


def test_upgrade_applies_workspace_mapping_additions(services):
    reset_esrs(services["es"])
    seed_legacy_v1_state(services["es"])
    run_upgrade(services)

    mapping_response = services["es"].indices.get_mapping(index="esrs-workspaces")
    body = mapping_response.body if hasattr(mapping_response, "body") else mapping_response
    properties = body["esrs-workspaces"]["mappings"]["properties"]

    assert properties["description"]["type"] == "text"
    assert properties["_search"]["properties"]["description"]["type"] == "text"
