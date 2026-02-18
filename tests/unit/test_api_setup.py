import json

import pytest

from server.api import setup


class _Meta:
    def __init__(self, status=200):
        self.status = status


class _Response:
    def __init__(self, body=None, status=200):
        self.body = body or {}
        self.meta = _Meta(status=status)


def test_load_migration_manifest_requires_sorted_versions(tmp_path, monkeypatch):
    manifest_path = tmp_path / "index_templates.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "versions": [
                    {"version": "1.2.0", "steps": []},
                    {"version": "1.1.0", "steps": []},
                ],
            }
        )
    )
    monkeypatch.setattr(setup, "PATH_INDEX_TEMPLATE_MIGRATIONS", str(manifest_path))
    with pytest.raises(ValueError, match="sorted"):
        setup._load_migration_manifest()


def test_load_migration_manifest_rejects_unsupported_action(tmp_path, monkeypatch):
    manifest_path = tmp_path / "index_templates.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "versions": [
                    {
                        "version": "1.1.0",
                        "steps": [
                            {"template": "esrs-workspaces", "action": "reindex_template", "requires_reindex": False}
                        ],
                    }
                ],
            }
        )
    )
    monkeypatch.setattr(setup, "PATH_INDEX_TEMPLATE_MIGRATIONS", str(manifest_path))
    with pytest.raises(ValueError, match="Invalid migration action"):
        setup._load_migration_manifest()


def test_check_upgrade_state_is_noop_when_current(monkeypatch):
    manifest = {
        "schema_version": 1,
        "versions": [
            {
                "version": "1.1.0",
                "steps": [{"template": "esrs-workspaces", "action": "update_template", "requires_reindex": False}],
            }
        ],
    }
    monkeypatch.setattr(setup, "_load_migration_manifest", lambda: manifest)
    monkeypatch.setattr(setup, "_read_ledger", lambda: {"applied_versions": ["1.1.0"]})
    monkeypatch.setattr(setup, "_is_release_applied", lambda release: True)

    state = setup.check_upgrade_state()
    assert state["upgrade_needed"] is False
    assert state["pending_versions"] == []
    assert state["current_version"] == "1.1.0"


def test_check_upgrade_state_returns_incremental_pending_versions(monkeypatch):
    manifest = {
        "schema_version": 1,
        "versions": [
            {
                "version": "1.1.0",
                "steps": [{"template": "esrs-workspaces", "action": "update_template", "requires_reindex": False}],
            },
            {
                "version": "1.2.0",
                "steps": [{"template": "esrs-conversations", "action": "create_template", "requires_reindex": False}],
            },
        ],
    }
    monkeypatch.setattr(setup, "_load_migration_manifest", lambda: manifest)
    monkeypatch.setattr(setup, "_read_ledger", lambda: {"applied_versions": ["1.0.0"]})
    monkeypatch.setattr(setup, "_is_release_applied", lambda release: False)

    state = setup.check_upgrade_state()
    assert state["upgrade_needed"] is True
    assert state["pending_versions"] == ["1.1.0", "1.2.0"]
    assert state["target_version"] == "1.2.0"
    assert state["reindex_required"] is False


def test_run_upgrade_blocks_when_reindex_is_required(monkeypatch):
    manifest = {
        "schema_version": 1,
        "versions": [
            {
                "version": "1.1.0",
                "steps": [{"template": "esrs-workspaces", "action": "update_template", "requires_reindex": True}],
            }
        ],
    }
    monkeypatch.setattr(setup, "_load_migration_manifest", lambda: manifest)
    monkeypatch.setattr(setup, "_load_index_templates", lambda: {})
    monkeypatch.setattr(
        setup,
        "check_upgrade_state",
        lambda: {
            "pending_versions": ["1.1.0"],
            "upgrade_needed": True,
            "reindex_required": True,
            "blocking_reasons": ["requires reindex"],
        },
    )

    result = setup.run_upgrade(additive_only=True)
    assert result["upgrade"]["failures"] == 1
    assert result["upgrade"]["applied_versions"] == []
    assert result["upgrade"]["reindex_required"] is True


def test_run_upgrade_applies_put_mapping_for_additive_changes(monkeypatch):
    manifest = {
        "schema_version": 1,
        "versions": [
            {
                "version": "1.1.0",
                "steps": [
                    {
                        "template": "esrs-workspaces",
                        "action": "update_template",
                        "requires_reindex": False,
                        "mapping_additions": {"description": {"type": "text"}},
                    }
                ],
            }
        ],
    }
    template_def = {
        "esrs-workspaces": {
            "name": "esrs-workspaces",
            "index_name": "esrs-workspaces",
            "body": {"_meta": {"version": "1.1.0"}, "index_patterns": ["esrs-workspaces*"], "template": {"mappings": {}}},
            "version": "1.1.0",
        }
    }
    calls = {"put_mapping": 0}

    class _Indices:
        def put_index_template(self, name, body):
            return _Response({"acknowledged": True})

        def exists(self, index):
            return True

        def put_mapping(self, index, body):
            calls["put_mapping"] += 1
            assert index == "esrs-workspaces"
            assert body == {"properties": {"description": {"type": "text"}}}
            return _Response({"acknowledged": True})

    class _Client:
        def __init__(self):
            self.indices = _Indices()

    monkeypatch.setattr(setup, "_load_migration_manifest", lambda: manifest)
    monkeypatch.setattr(setup, "_load_index_templates", lambda: template_def)
    monkeypatch.setattr(setup, "_append_applied_version", lambda version: None)
    monkeypatch.setattr(
        setup,
        "check_upgrade_state",
        lambda: {
            "pending_versions": ["1.1.0"],
            "upgrade_needed": True,
            "reindex_required": False,
            "blocking_reasons": [],
        },
    )
    monkeypatch.setattr(setup, "es", lambda name: _Client())

    result = setup.run_upgrade(additive_only=True)
    assert result["upgrade"]["failures"] == 0
    assert calls["put_mapping"] == 1


def test_read_server_version_returns_stripped_value(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("1.2.3\n")
    monkeypatch.setattr(setup, "PATH_SERVER_VERSION", str(version_file))

    assert setup._read_server_version() == "1.2.3"


def test_read_server_version_returns_none_when_missing(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    monkeypatch.setattr(setup, "PATH_SERVER_VERSION", str(version_file))

    assert setup._read_server_version() is None


def test_read_server_version_returns_none_when_empty(tmp_path, monkeypatch):
    version_file = tmp_path / "VERSION"
    version_file.write_text("   \n")
    monkeypatch.setattr(setup, "PATH_SERVER_VERSION", str(version_file))

    assert setup._read_server_version() is None


def test_read_server_version_returns_none_on_os_error(tmp_path, monkeypatch):
    version_dir = tmp_path / "VERSION_DIR"
    version_dir.mkdir()
    monkeypatch.setattr(setup, "PATH_SERVER_VERSION", str(version_dir))

    assert setup._read_server_version() is None


def test_check_includes_server_version(monkeypatch):
    cluster_info = _Response({"version": {"build_flavor": "default"}})
    cluster_info.meta.headers = {}
    license_info = _Response({"license": {"type": "enterprise", "status": "active"}})

    monkeypatch.setattr(setup, "get_cluster_info", lambda: cluster_info)
    monkeypatch.setattr(setup, "get_license_info", lambda: license_info)
    monkeypatch.setattr(setup, "_read_server_version", lambda: "1.2.3")
    monkeypatch.setattr(setup, "check_setup_state", lambda: {"failures": 0, "requests": []})
    monkeypatch.setattr(setup, "check_upgrade_state", lambda: {"upgrade_needed": False})

    result = setup.check()
    assert result["version"] == "1.2.3"


def test_check_includes_null_server_version_when_unavailable(monkeypatch):
    cluster_info = _Response({"version": {"build_flavor": "default"}})
    cluster_info.meta.headers = {}
    license_info = _Response({"license": {"type": "enterprise", "status": "active"}})

    monkeypatch.setattr(setup, "get_cluster_info", lambda: cluster_info)
    monkeypatch.setattr(setup, "get_license_info", lambda: license_info)
    monkeypatch.setattr(setup, "_read_server_version", lambda: None)
    monkeypatch.setattr(setup, "check_setup_state", lambda: {"failures": 0, "requests": []})
    monkeypatch.setattr(setup, "check_upgrade_state", lambda: {"upgrade_needed": False})

    result = setup.check()
    assert result["version"] is None


def test_has_upgrade_only_setup_failures_true_when_all_failures_in_pending_upgrade_steps():
    setup_state = {
        "failures": 2,
        "requests": [
            {"index_template": "esrs-conversations", "response": {"status": 404}},
            {"index": "esrs-conversations", "response": {"status": 404}},
            {"index_template": "esrs-workspaces", "response": {"status": 200}},
        ],
    }
    upgrade_state = {
        "upgrade_needed": True,
        "pending_steps": [
            {"template": "esrs-conversations"},
            {"template": "esrs-workspaces"},
        ],
    }
    assert setup._has_upgrade_only_setup_failures(setup_state, upgrade_state) is True


def test_has_upgrade_only_setup_failures_false_when_any_failure_is_not_upgrade_related():
    setup_state = {
        "failures": 2,
        "requests": [
            {"index_template": "esrs-conversations", "response": {"status": 404}},
            {"index_template": "esrs-benchmarks", "response": {"status": 404}},
        ],
    }
    upgrade_state = {
        "upgrade_needed": True,
        "pending_steps": [{"template": "esrs-conversations"}],
    }
    assert setup._has_upgrade_only_setup_failures(setup_state, upgrade_state) is False


def test_check_includes_upgrade_only_setup_failures_flag(monkeypatch):
    cluster_info = _Response({"version": {"build_flavor": "default"}})
    cluster_info.meta.headers = {}
    license_info = _Response({"license": {"type": "enterprise", "status": "active"}})
    setup_state = {"failures": 1, "requests": [{"index_template": "esrs-conversations", "response": {"status": 404}}]}
    upgrade_state = {"upgrade_needed": True, "pending_steps": [{"template": "esrs-conversations"}]}

    monkeypatch.setattr(setup, "get_cluster_info", lambda: cluster_info)
    monkeypatch.setattr(setup, "get_license_info", lambda: license_info)
    monkeypatch.setattr(setup, "_read_server_version", lambda: "1.2.3")
    monkeypatch.setattr(setup, "check_setup_state", lambda: setup_state)
    monkeypatch.setattr(setup, "check_upgrade_state", lambda: upgrade_state)

    result = setup.check()
    assert result["setup"]["upgrade_only_failures"] is True
