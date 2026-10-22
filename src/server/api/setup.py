# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

# Elastic packages
from elasticsearch.exceptions import ApiError, NotFoundError, RequestError

# App packages
from ..client import es

if TYPE_CHECKING:
    from elasticsearch import Elasticsearch

PATH_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "elastic")
PATH_INDEX_TEMPLATE_DIR = os.path.join(PATH_BASE, "index_templates")
PATH_INDEX_TEMPLATE_MIGRATIONS = os.path.join(PATH_BASE, "migrations", "index_templates.json")
PATH_SERVER_VERSION = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "VERSION")
PATH_INDEX_TEMPLATES = [
    ("esrs-conversations", os.path.join(PATH_INDEX_TEMPLATE_DIR, "conversations.json")),
    ("esrs-workspaces", os.path.join(PATH_INDEX_TEMPLATE_DIR, "workspaces.json")),
    ("esrs-displays", os.path.join(PATH_INDEX_TEMPLATE_DIR, "displays.json")),
    ("esrs-scenarios", os.path.join(PATH_INDEX_TEMPLATE_DIR, "scenarios.json")),
    ("esrs-judgements", os.path.join(PATH_INDEX_TEMPLATE_DIR, "judgements.json")),
    ("esrs-strategies", os.path.join(PATH_INDEX_TEMPLATE_DIR, "strategies.json")),
    ("esrs-benchmark-configs", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-configs.json")),
    ("esrs-benchmark-runs", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-runs.json")),
    ("esrs-benchmark-results", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-results.json")),
    ("esrs-benchmark-runtime-indices", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-runtime-indices.json")),
    ("esrs-benchmark-runtime-strategies", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-runtime-strategies.json")),
    ("esrs-benchmark-runtime-scenarios", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-runtime-scenarios.json")),
    ("esrs-benchmark-runtime-judgements", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-runtime-judgements.json")),
    ("esrs-benchmark-unrated-docs", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-unrated-docs.json")),
    ("esrs-benchmark-failures", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmark-failures.json")),
]

# Legacy v1 templates. Intentionally NOT in PATH_INDEX_TEMPLATES, so fresh v2.0
# installs do not recreate these indices and the setup-state check does not
# require them. They remain loadable for the migration runner because pending
# pre-2.0 manifest steps (e.g. 1.2.0 mapping additions) still reference them,
# and because they are the reindex sources for the 2.0.0 split. The migration
# never deletes them (additive-and-copy only).
PATH_LEGACY_INDEX_TEMPLATES = [
    ("esrs-benchmarks", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmarks.json")),
    ("esrs-evaluations", os.path.join(PATH_INDEX_TEMPLATE_DIR, "evaluations.json")),
]

# Data-stream-backed templates (created via create_data_stream, not indices.create)
# and immutable (op_type: create only). The "index_name" derived from their
# index_patterns is the data stream name.
DATA_STREAM_TEMPLATES = set([
    "esrs-benchmark-results",
    "esrs-benchmark-runtime-indices",
    "esrs-benchmark-runtime-strategies",
    "esrs-benchmark-runtime-scenarios",
    "esrs-benchmark-runtime-judgements",
    "esrs-benchmark-unrated-docs",
    "esrs-benchmark-failures",
])
VALID_STEP_ACTIONS = set(["create_template", "update_template", "reindex_and_cutover"])
LEDGER_INDEX = "esrs-system"
LEDGER_DOC_ID = "index-template-migrations"


def is_cloud(headers: Dict[str, Any]) -> bool:
    """Check if the Elasticsearch response headers indicate Elastic Cloud.

    Args:
        headers: A dictionary of response headers from Elasticsearch.

    Returns:
        True if the headers indicate an Elastic Cloud deployment, False otherwise.
    """
    return any(k.lower().startswith("x-found-") for k in headers)


def is_serverless(cluster_info_body: Dict[str, Any]) -> bool:
    """Check if the Elasticsearch deployment is serverless.

    Args:
        cluster_info_body: The body of the Elasticsearch info response.

    Returns:
        True if the deployment is serverless, False otherwise.
    """
    return cluster_info_body.get("version", {}).get("build_flavor") == "serverless"

def get_license_info():
    """Get license information from Elasticsearch.

    Returns:
        The response from the Elasticsearch license API.
    """
    client = es("studio")
    return client.license.get()


def get_cluster_info():
    """Get cluster information from Elasticsearch.

    Returns:
        The response from the Elasticsearch info API.
    """
    client = es("studio")
    return client.info()


def _is_additive_reindex_step(step: Dict[str, Any]) -> bool:
    """True if a step is an additive-and-copy reindex that may run under
    additive-only upgrades.

    ``reindex_and_cutover`` only ever creates new templates/indices/data streams
    and copies data from a source it never mutates or deletes, so it is safe to
    execute during the normal additive upgrade. The relaxation is scoped to this
    action plus an explicit ``additive_reindex: true`` flag, so a hypothetical
    future *destructive* reindex (requires_reindex without this flag/action)
    still blocks exactly as before.
    """
    return bool(step.get("additive_reindex")) or step.get("action") == "reindex_and_cutover"


def _step_blocks_additive_upgrade(step: Dict[str, Any]) -> bool:
    """True if a step requires a reindex that is NOT additive-and-copy."""
    return bool(step.get("requires_reindex")) and not _is_additive_reindex_step(step)


def _parse_semver(version: str) -> Tuple[int, int, int]:
    parts = version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Invalid semantic version '{version}'. Expected MAJOR.MINOR.PATCH.")
    return tuple(int(v) for v in parts)


def _version_gte(version_a: str, version_b: str) -> bool:
    return _parse_semver(version_a) >= _parse_semver(version_b)


def _version_sort_key(release: Dict[str, Any]) -> Tuple[int, int, int]:
    return _parse_semver(release["version"])


def _load_json(path: str) -> Dict[str, Any]:
    with open(path) as file:
        return json.loads(file.read())


def _read_server_version() -> Optional[str]:
    try:
        with open(PATH_SERVER_VERSION) as file:
            version = file.read().strip()
            return version or None
    except OSError:
        return None


def _load_index_templates() -> Dict[str, Dict[str, Any]]:
    # Include the legacy templates so the migration runner can resolve pending
    # pre-2.0 steps that still target them; fresh-setup/check paths iterate
    # PATH_INDEX_TEMPLATES directly and never see the legacy entries.
    templates = {}
    for template_name, path_index_template in (PATH_INDEX_TEMPLATES + PATH_LEGACY_INDEX_TEMPLATES):
        body = _load_json(path_index_template)
        index_name = body["index_patterns"][0].replace("*", "")
        templates[template_name] = {
            "name": template_name,
            "index_name": index_name,
            "body": body,
            "version": body.get("_meta", {}).get("version"),
        }
    return templates


def _load_migration_manifest() -> Dict[str, Any]:
    manifest = _load_json(PATH_INDEX_TEMPLATE_MIGRATIONS)
    schema_version = manifest.get("schema_version")
    versions = manifest.get("versions")
    if not isinstance(schema_version, int):
        raise ValueError("Migration manifest must include integer 'schema_version'.")
    if not isinstance(versions, list):
        raise ValueError("Migration manifest must include list 'versions'.")

    seen = set()
    for release in versions:
        version = release.get("version")
        steps = release.get("steps")
        if not isinstance(version, str):
            raise ValueError("Each migration version must define string 'version'.")
        _parse_semver(version)
        if version in seen:
            raise ValueError(f"Duplicate migration version '{version}' in manifest.")
        seen.add(version)
        if not isinstance(steps, list):
            raise ValueError(f"Migration version '{version}' must define list 'steps'.")

        for step in steps:
            action = step.get("action")
            template = step.get("template")
            requires_reindex = step.get("requires_reindex")
            if action not in VALID_STEP_ACTIONS:
                raise ValueError(f"Invalid migration action '{action}' in version '{version}'.")
            if not isinstance(template, str) or not template:
                raise ValueError(f"Migration step in '{version}' must define string 'template'.")
            if not isinstance(requires_reindex, bool):
                raise ValueError(
                    f"Migration step for template '{template}' in '{version}' must define boolean 'requires_reindex'."
                )
            if "mapping_additions" in step and not isinstance(step["mapping_additions"], dict):
                raise ValueError(
                    f"'mapping_additions' for template '{template}' in '{version}' must be an object."
                )
            if "additive_reindex" in step and not isinstance(step["additive_reindex"], bool):
                raise ValueError(
                    f"'additive_reindex' for template '{template}' in '{version}' must be a boolean."
                )
            if action == "reindex_and_cutover":
                reindex = step.get("reindex")
                if not isinstance(reindex, dict):
                    raise ValueError(
                        f"'reindex_and_cutover' step for template '{template}' in '{version}' must define object 'reindex'."
                    )
                if not isinstance(reindex.get("source"), str) or not reindex.get("source"):
                    raise ValueError(
                        f"'reindex.source' for template '{template}' in '{version}' must be a non-empty string."
                    )
                valid_modes = (
                    "copy", "runs", "results",
                    "runtime_indices", "runtime_strategies", "runtime_scenarios",
                    "runtime_judgements", "unrated_docs", "failures",
                )
                if reindex.get("mode") not in valid_modes:
                    raise ValueError(
                        f"'reindex.mode' for template '{template}' in '{version}' must be one of {'|'.join(valid_modes)}."
                    )

    ordered = sorted(versions, key=_version_sort_key)
    if [v["version"] for v in ordered] != [v["version"] for v in versions]:
        raise ValueError("Migration versions must be sorted in ascending semantic version order.")
    return manifest


def _read_ledger() -> Dict[str, Any]:
    client = es("studio")
    try:
        if not client.indices.exists(index=LEDGER_INDEX):
            return {"applied_versions": []}
        response = client.get(index=LEDGER_INDEX, id=LEDGER_DOC_ID)
        source = response.body.get("_source", {}) if response and response.body else {}
        versions = source.get("applied_versions", [])
        if not isinstance(versions, list):
            versions = []
        return {"applied_versions": [v for v in versions if isinstance(v, str)]}
    except (ApiError, NotFoundError):
        return {"applied_versions": []}


def _write_ledger(applied_versions: List[str], via: str = "api"):
    client = es("studio")
    try:
        client.indices.create(index=LEDGER_INDEX)
    except RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise

    document = {
        "applied_versions": sorted(set(applied_versions), key=_parse_semver),
        "@meta": {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "system",
            "updated_via": via,
        },
    }
    return client.index(index=LEDGER_INDEX, id=LEDGER_DOC_ID, document=document, refresh=True)


def _append_applied_version(version: str, via: str = "api"):
    ledger = _read_ledger()
    versions = ledger.get("applied_versions", [])
    if version in versions:
        return None
    return _write_ledger(versions + [version], via=via)


def _get_deployed_template_version(template_name: str):
    client = es("studio")
    try:
        response = client.indices.get_index_template(name=template_name)
        templates = response.body.get("index_templates", [])
        if not templates:
            return None
        return templates[0].get("index_template", {}).get("_meta", {}).get("version")
    except (ApiError, NotFoundError):
        return None


def _is_release_applied(release: Dict[str, Any]) -> bool:
    required_version = release["version"]
    for step in release["steps"]:
        deployed_version = _get_deployed_template_version(step["template"])
        if not deployed_version or not _version_gte(deployed_version, required_version):
            return False
    return True


def _effective_current_version(applied_versions: List[str], manifest_versions: List[Dict[str, Any]]):
    if applied_versions:
        return sorted(applied_versions, key=_parse_semver)[-1]

    current = None
    for release in manifest_versions:
        if _is_release_applied(release):
            current = release["version"]
        else:
            break
    return current


def _index_or_data_stream_exists(client, template_name: str, index_name: str) -> bool:
    """Existence check that understands data streams.

    ``indices.exists`` returns False for a data stream (it is not a concrete
    index), so data-stream-backed templates are checked with
    ``indices.exists_index_template`` + the data-stream API instead.
    """
    if template_name in DATA_STREAM_TEMPLATES:
        try:
            client.indices.get_data_stream(name=index_name)
            return True
        except NotFoundError:
            return False
    return bool(client.indices.exists(index=index_name))


def check_setup_state():
    result = {"failures": 0, "requests": []}
    for template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = _load_json(path_index_template)
        index_name = body["index_patterns"][0].replace("*", "")

        client = es("studio")
        try:
            response = client.indices.get_index_template(name=index_name)
            result["requests"].append({
                "index_template": index_name,
                "response": {"body": response.body, "status": response.meta.status},
            })
        except (ApiError, NotFoundError) as e:
            result["failures"] += 1
            result["requests"].append({
                "index_template": index_name,
                "response": {"body": e.body, "status": e.meta.status},
            })

        try:
            exists = _index_or_data_stream_exists(client, template_name, index_name)
            result["requests"].append({
                "index": index_name,
                "response": {"body": "OK" if exists else "Not Found", "status": 200 if exists else 404},
            })
            if not exists:
                result["failures"] += 1
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index": index_name,
                "response": {"body": e.body, "status": e.meta.status},
            })
    return result


def check_upgrade_state():
    manifest = _load_migration_manifest()
    versions = manifest["versions"]
    ledger = _read_ledger()
    applied_versions = sorted(set(ledger.get("applied_versions", [])), key=_parse_semver)

    pending_releases = []
    for release in versions:
        version = release["version"]
        if version in applied_versions:
            continue
        if _is_release_applied(release):
            continue
        pending_releases.append(release)

    pending_steps = []
    reindex_required = False
    blocking_reasons = []
    for release in pending_releases:
        for step in release["steps"]:
            requires_reindex = step.get("requires_reindex", False)
            additive_reindex = _is_additive_reindex_step(step)
            # Only a *blocking* (non-additive) reindex sets reindex_required,
            # which is what gates the additive-only upgrade path. Additive
            # reindex_and_cutover steps execute through the normal upgrade.
            if _step_blocks_additive_upgrade(step):
                reindex_required = True
                blocking_reasons.append(
                    f"Version {release['version']} step for '{step['template']}' requires reindex."
                )
            pending_steps.append({
                "version": release["version"],
                "template": step["template"],
                "action": step["action"],
                "requires_reindex": requires_reindex,
                "additive_reindex": additive_reindex,
                "description": step.get("description", ""),
                "mapping_additions": step.get("mapping_additions", {}),
            })

    current_version = _effective_current_version(applied_versions, versions)
    target_version = versions[-1]["version"] if versions else None
    return {
        "schema_version": manifest.get("schema_version"),
        "current_version": current_version,
        "target_version": target_version,
        "applied_versions": applied_versions,
        "pending_versions": [release["version"] for release in pending_releases],
        "pending_steps": pending_steps,
        "upgrade_needed": len(pending_releases) > 0,
        "reindex_required": reindex_required,
        "blocking_reasons": sorted(set(blocking_reasons)),
        "impact_summary": {
            "versions_pending": len(pending_releases),
            "steps_pending": len(pending_steps),
            "templates_pending": len(set(step["template"] for step in pending_steps)),
            "reindex_steps": len([step for step in pending_steps if step["requires_reindex"]]),
            "additive_reindex_steps": len([step for step in pending_steps if step.get("additive_reindex")]),
        },
    }


def _create_index_or_data_stream(client, template_name: str, index_name: str) -> Dict[str, Any]:
    """Create a plain index, or a data stream when the template declares one.

    Data-stream-backed templates (a top-level ``data_stream`` block) cannot be
    created with ``indices.create`` — Elasticsearch rejects it because the name
    matches a data-stream template — so they are created with
    ``indices.create_data_stream``. Returns a request record; swallows
    ``resource_already_exists_exception`` so setup/upgrade stay idempotent.
    """
    is_data_stream = template_name in DATA_STREAM_TEMPLATES
    action = "create_data_stream" if is_data_stream else "create_index"
    try:
        if is_data_stream:
            response = client.indices.create_data_stream(name=index_name)
        else:
            response = client.indices.create(index=index_name)
        return {
            "index": index_name,
            "action": action,
            "response": {"body": response.body, "status": response.meta.status},
            "ok": True,
        }
    except RequestError as e:
        already_exists = getattr(e, "error", None) == "resource_already_exists_exception"
        return {
            "index": index_name,
            "action": action,
            "response": {"body": e.body, "status": e.meta.status},
            "ok": already_exists,
        }


def run_setup():
    client = es("studio")
    result = {"failures": 0, "requests": []}
    for template_name, path_index_template in PATH_INDEX_TEMPLATES:
        body = _load_json(path_index_template)
        index_name = body["index_patterns"][0].replace("*", "")
        try:
            response = client.indices.put_index_template(name=index_name, body=body)
            result["requests"].append({
                "index_template": index_name,
                "response": {"body": response.body, "status": response.meta.status},
            })
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index_template": index_name,
                "response": {"body": e.body, "status": e.meta.status},
            })

        try:
            record = _create_index_or_data_stream(client, template_name, index_name)
            if not record.pop("ok", False):
                result["failures"] += 1
            result["requests"].append(record)
        except ApiError as e:
            result["failures"] += 1
            result["requests"].append({
                "index": index_name,
                "response": {"body": e.body, "status": e.meta.status},
            })
    return result


def _execute_upgrade_step(step: Dict[str, Any], index_templates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    requests = []
    template_name = step["template"]
    if template_name not in index_templates:
        raise ValueError(f"Template '{template_name}' from migration manifest is not present in index templates.")
    template = index_templates[template_name]
    client = es("studio")

    response = client.indices.put_index_template(name=template_name, body=template["body"])
    requests.append({
        "index_template": template_name,
        "action": "put_index_template",
        "response": {"body": response.body, "status": response.meta.status},
    })

    if step["action"] == "create_template":
        try:
            response = client.indices.create(index=template["index_name"])
            requests.append({
                "index": template["index_name"],
                "action": "create_index",
                "response": {"body": response.body, "status": response.meta.status},
            })
        except RequestError as e:
            requests.append({
                "index": template["index_name"],
                "action": "create_index",
                "response": {"body": e.body, "status": e.meta.status},
            })
            if e.error != "resource_already_exists_exception":
                raise
    elif step["action"] == "update_template":
        mapping_additions = step.get("mapping_additions", {})
        if mapping_additions and client.indices.exists(index=template["index_name"]):
            response = client.indices.put_mapping(
                index=template["index_name"],
                body={"properties": mapping_additions},
            )
            requests.append({
                "index": template["index_name"],
                "action": "put_mapping",
                "response": {"body": response.body, "status": response.meta.status},
            })
    elif step["action"] == "reindex_and_cutover":
        requests.extend(_execute_reindex_and_cutover(step, template))
    else:
        raise ValueError(f"Unsupported upgrade action '{step['action']}'.")
    return requests


def _execute_reindex_and_cutover(step: Dict[str, Any], template: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Create the destination index/data stream, copy/split data into it, and
    verify the destination count. Never deletes the source (additive-only).

    The destination template was already registered by the shared
    ``put_index_template`` prelude in ``_execute_upgrade_step``.
    """
    from .migrations import run_reindex_transform

    requests: List[Dict[str, Any]] = []
    client = es("studio")
    dest = template["index_name"]
    template_name = template["name"]
    source = step["reindex"]["source"]
    mode = step["reindex"]["mode"]

    # 1. Create destination (data-stream-aware), idempotently.
    record = _create_index_or_data_stream(client, template_name, dest)
    created_ok = record.pop("ok", False)
    requests.append(record)
    if not created_ok:
        raise ValueError(f"Failed to create destination '{dest}' for reindex_and_cutover.")

    # 2. Copy/split source -> dest.
    summary = run_reindex_transform(source, dest, mode)
    requests.append({
        "index": dest,
        "action": "reindex_transform",
        "response": {"status": 200, "body": {"source": source, "mode": mode, **summary}},
    })
    if summary.get("error_count"):
        raise ValueError(
            f"reindex_and_cutover for '{dest}' had {summary['error_count']} write errors: {summary.get('errors')}"
        )

    # 3. Verify destination count (fan-out aware: 'expected' is the number of
    #    docs the transform intended to write). Refresh first so the count is
    #    current; data streams refresh their backing indices.
    try:
        client.indices.refresh(index=dest)
    except (ApiError, RequestError):
        pass
    actual = client.count(index=dest).body.get("count", 0)
    expected = summary.get("expected", 0)
    requests.append({
        "index": dest,
        "action": "verify_count",
        "response": {"status": 200, "body": {"expected": expected, "actual": actual}},
    })
    if actual < expected:
        raise ValueError(
            f"reindex_and_cutover count mismatch for '{dest}': expected >= {expected}, found {actual}."
        )
    return requests


def run_upgrade(additive_only: bool = True, via: str = "api"):
    manifest = _load_migration_manifest()
    index_templates = _load_index_templates()
    upgrade_state = check_upgrade_state()

    result = {
        "upgrade": {
            "failures": 0,
            "requests": [],
            "applied_versions": [],
            "pending_versions": list(upgrade_state["pending_versions"]),
            "upgrade_needed": upgrade_state["upgrade_needed"],
            "reindex_required": upgrade_state["reindex_required"],
            "blocking_reasons": list(upgrade_state["blocking_reasons"]),
        }
    }
    if not upgrade_state["upgrade_needed"]:
        return result
    if additive_only and upgrade_state["reindex_required"]:
        result["upgrade"]["failures"] += 1
        return result

    pending_versions = set(upgrade_state["pending_versions"])
    versions = [release for release in manifest["versions"] if release["version"] in pending_versions]
    for release in versions:
        release_failed = False
        for step in release["steps"]:
            if additive_only and _step_blocks_additive_upgrade(step):
                release_failed = True
                result["upgrade"]["failures"] += 1
                result["upgrade"]["requests"].append({
                    "version": release["version"],
                    "template": step["template"],
                    "action": step["action"],
                    "response": {
                        "status": 409,
                        "body": {"error": "reindex_required", "message": "Step requires reindex and additive-only mode is enabled."},
                    },
                })
                break

            try:
                step_requests = _execute_upgrade_step(step, index_templates)
                for request in step_requests:
                    request["version"] = release["version"]
                    request["template"] = step["template"]
                result["upgrade"]["requests"].extend(step_requests)
            except (ApiError, RequestError, ValueError) as e:
                release_failed = True
                result["upgrade"]["failures"] += 1
                status = getattr(getattr(e, "meta", None), "status", 500)
                body = getattr(e, "body", {"error": "upgrade_step_failed", "message": str(e)})
                result["upgrade"]["requests"].append({
                    "version": release["version"],
                    "template": step["template"],
                    "action": step["action"],
                    "response": {"status": status, "body": body},
                })
                break

        if release_failed:
            break

        _append_applied_version(release["version"], via=via)
        result["upgrade"]["applied_versions"].append(release["version"])

    latest = check_upgrade_state()
    result["upgrade"]["upgrade_needed"] = latest["upgrade_needed"]
    result["upgrade"]["pending_versions"] = latest["pending_versions"]
    result["upgrade"]["reindex_required"] = latest["reindex_required"]
    result["upgrade"]["blocking_reasons"] = latest["blocking_reasons"]
    return result


def _has_upgrade_only_setup_failures(setup_state: Dict[str, Any], upgrade_state: Dict[str, Any]) -> bool:
    failures = setup_state.get("failures", 0) if isinstance(setup_state, dict) else 0
    if failures <= 0:
        return False
    if not isinstance(upgrade_state, dict) or not upgrade_state.get("upgrade_needed"):
        return False

    pending_steps = upgrade_state.get("pending_steps", []) or []
    # Any pending step calls put_index_template, so a missing template is
    # fixable by the upgrade flow if any pending step targets that template.
    template_fixable: set = set()
    # Only `create_template` steps create the underlying index; `update_template`
    # only writes mappings if the index already exists. So a missing index is
    # only fixable by the upgrade flow if a `create_template` step targets it.
    index_fixable: set = set()
    for step in pending_steps:
        if not isinstance(step, dict):
            continue
        template_name = step.get("template")
        if not template_name:
            continue
        template_fixable.add(template_name)
        # Both create_template and reindex_and_cutover create the destination
        # index/data stream, so a missing index for either is fixable by upgrade.
        if step.get("action") in ("create_template", "reindex_and_cutover"):
            index_fixable.add(template_name)

    if not template_fixable:
        return False

    for request in setup_state.get("requests", []):
        if not isinstance(request, dict):
            continue
        response = request.get("response", {})
        status = response.get("status") if isinstance(response, dict) else None
        if status is None or status < 400:
            continue
        if "index_template" in request:
            if request.get("index_template") not in template_fixable:
                return False
        elif "index" in request:
            if request.get("index") not in index_fixable:
                return False
        else:
            return False
    return True


def check():
    """Return deployment, setup, and upgrade status for the server.

    This is the status payload shown by setup/upgrade checks and is used by
    MCP tool metadata for `setup_check`.
    """
    cluster_info = get_cluster_info()
    license_info = get_license_info()
    deployment_mode = "standard"
    if is_serverless(cluster_info.body):
        deployment_mode = "serverless"
    elif is_cloud(cluster_info.meta.headers):
        deployment_mode = "cloud"
    setup_state = check_setup_state()
    upgrade_state = check_upgrade_state()
    setup_state["upgrade_only_failures"] = _has_upgrade_only_setup_failures(setup_state, upgrade_state)
    return {
        "version": _read_server_version(),
        "deployment": {
            "cluster_info": cluster_info.body,
            "mode": deployment_mode,
            "license": {
                "type": license_info.body.get("license", {}).get("type") or "unknown",
                "status": license_info.body.get("license", {}).get("status") or "unknown",
            },
        },
        "setup": setup_state,
        "upgrade": upgrade_state,
    }


def run(via: str = "api"):
    """Create or update required index templates and indices.

    Returns:
        Dict[str, Any]: A dictionary with setup execution details under `setup`.
    """
    return {"setup": run_setup()}


def upgrade(via: str = "api"):
    """Apply additive index-template upgrade steps from the migration manifest.

    Returns:
        Dict[str, Any]: A dictionary with upgrade execution details under
        `upgrade`.
    """
    return run_upgrade(additive_only=True, via=via)
