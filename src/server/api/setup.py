# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License
# 2.0; you may not use this file except in compliance with the Elastic License
# 2.0.

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# Elastic packages
from elasticsearch.exceptions import ApiError, NotFoundError, RequestError

# App packages
from ..client import es

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
    ("esrs-benchmarks", os.path.join(PATH_INDEX_TEMPLATE_DIR, "benchmarks.json")),
    ("esrs-evaluations", os.path.join(PATH_INDEX_TEMPLATE_DIR, "evaluations.json")),
]
VALID_STEP_ACTIONS = set(["create_template", "update_template"])
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
    return es("studio").license.get()


def get_cluster_info():
    """Get cluster information from Elasticsearch.

    Returns:
        The response from the Elasticsearch info API.
    """
    return es("studio").info()


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
    templates = {}
    for template_name, path_index_template in PATH_INDEX_TEMPLATES:
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

    ordered = sorted(versions, key=_version_sort_key)
    if [v["version"] for v in ordered] != [v["version"] for v in versions]:
        raise ValueError("Migration versions must be sorted in ascending semantic version order.")
    return manifest


def _read_ledger() -> Dict[str, Any]:
    try:
        if not es("studio").indices.exists(index=LEDGER_INDEX):
            return {"applied_versions": []}
        response = es("studio").get(index=LEDGER_INDEX, id=LEDGER_DOC_ID)
        source = response.body.get("_source", {}) if response and response.body else {}
        versions = source.get("applied_versions", [])
        if not isinstance(versions, list):
            versions = []
        return {"applied_versions": [v for v in versions if isinstance(v, str)]}
    except (ApiError, NotFoundError):
        return {"applied_versions": []}


def _write_ledger(applied_versions: List[str]):
    try:
        es("studio").indices.create(index=LEDGER_INDEX)
    except RequestError as e:
        if e.error != "resource_already_exists_exception":
            raise

    document = {
        "applied_versions": sorted(set(applied_versions), key=_parse_semver),
        "@meta": {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": "system",
        },
    }
    return es("studio").index(index=LEDGER_INDEX, id=LEDGER_DOC_ID, document=document, refresh=True)


def _append_applied_version(version: str):
    ledger = _read_ledger()
    versions = ledger.get("applied_versions", [])
    if version in versions:
        return None
    return _write_ledger(versions + [version])


def _get_deployed_template_version(template_name: str):
    try:
        response = es("studio").indices.get_index_template(name=template_name)
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


def check_setup_state():
    result = {"failures": 0, "requests": []}
    for _, path_index_template in PATH_INDEX_TEMPLATES:
        body = _load_json(path_index_template)
        index_name = body["index_patterns"][0].replace("*", "")

        try:
            response = es("studio").indices.get_index_template(name=index_name)
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
            exists = es("studio").indices.exists(index=index_name)
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
            if requires_reindex:
                reindex_required = True
                blocking_reasons.append(
                    f"Version {release['version']} step for '{step['template']}' requires reindex."
                )
            pending_steps.append({
                "version": release["version"],
                "template": step["template"],
                "action": step["action"],
                "requires_reindex": requires_reindex,
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
        },
    }


def run_setup():
    result = {"failures": 0, "requests": []}
    for _, path_index_template in PATH_INDEX_TEMPLATES:
        body = _load_json(path_index_template)
        index_name = body["index_patterns"][0].replace("*", "")
        try:
            response = es("studio").indices.put_index_template(name=index_name, body=body)
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
            response = es("studio").indices.create(index=index_name)
            result["requests"].append({
                "index": index_name,
                "response": {"body": response.body, "status": response.meta.status},
            })
        except RequestError as e:
            result["requests"].append({
                "index": index_name,
                "response": {"body": e.body, "status": e.meta.status},
            })
            if e.error != "resource_already_exists_exception":
                result["failures"] += 1
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

    response = es("studio").indices.put_index_template(name=template_name, body=template["body"])
    requests.append({
        "index_template": template_name,
        "action": "put_index_template",
        "response": {"body": response.body, "status": response.meta.status},
    })

    if step["action"] == "create_template":
        try:
            response = es("studio").indices.create(index=template["index_name"])
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
        if mapping_additions and es("studio").indices.exists(index=template["index_name"]):
            response = es("studio").indices.put_mapping(
                index=template["index_name"],
                body={"properties": mapping_additions},
            )
            requests.append({
                "index": template["index_name"],
                "action": "put_mapping",
                "response": {"body": response.body, "status": response.meta.status},
            })
    else:
        raise ValueError(f"Unsupported upgrade action '{step['action']}'.")
    return requests


def run_upgrade(additive_only: bool = True):
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
            if additive_only and step.get("requires_reindex"):
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

        _append_applied_version(release["version"])
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

    pending_steps = upgrade_state.get("pending_steps", [])
    upgrade_targets = set()
    for step in pending_steps:
        template_name = step.get("template") if isinstance(step, dict) else None
        if template_name:
            upgrade_targets.add(template_name)
    if not upgrade_targets:
        return False

    for request in setup_state.get("requests", []):
        if not isinstance(request, dict):
            continue
        response = request.get("response", {})
        status = response.get("status") if isinstance(response, dict) else None
        if status is None or status < 400:
            continue
        target = request.get("index_template") or request.get("index")
        if target not in upgrade_targets:
            return False
    return True


def check():
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


def run():
    return {"setup": run_setup()}


def upgrade():
    return run_upgrade(additive_only=True)