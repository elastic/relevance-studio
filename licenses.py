# Copyright Elasticsearch B.V. and/or licensed to Elasticsearch B.V. under one
# or more contributor license agreements. Licensed under the Elastic License;
# you may not use this file except in compliance with the Elastic License.

# Standard packages
import json
import subprocess
import tempfile
import venv
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path
import csv
import io

# Third-party packages
import click

NOTICE_HEADER = f"""Elasticsearch Relevance Studio
Copyright 2012-{datetime.now().year} Elasticsearch B.V.
"""

def run_command(cmd, cwd=None):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout

def parse_requirements_file(filepath):
    pkgs = set()
    if not Path(filepath).exists():
        return pkgs
    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                name = line.split("==")[0].split(">")[0].split("<")[0].strip()
                if name:
                    pkgs.add(name)
    return pkgs

def get_declared_python_packages(requirements_files):
    declared = set()
    for req in requirements_files:
        declared |= parse_requirements_file(req)
    return declared

def get_declared_node_packages(package_file, include_dev):
    if not Path(package_file).exists():
        return set()
    with open(package_file) as f:
        pkg_json = json.load(f)
    declared = set(pkg_json.get("dependencies", {}).keys())
    if include_dev:
        declared |= set(pkg_json.get("devDependencies", {}).keys())
    return declared

def get_python_licenses(requirements_files, include_transitive):
    declared = get_declared_python_packages(requirements_files)
    results = []
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir)
        venv.create(env_path, with_pip=True)
        pip_path = env_path / "bin" / "pip"
        python_path = env_path / "bin" / "python"

        for req in requirements_files:
            if Path(req).exists():
                run_command([str(pip_path), "install", "-r", req])
        run_command([str(pip_path), "install", "pip-licenses", "pipdeptree"])

        licenses_json = run_command([
            str(python_path), "-m", "piplicenses", "--format=json"
        ])
        licenses_data = json.loads(licenses_json)

        tree_output = run_command([
            str(python_path), "-m", "pipdeptree", "--json"
        ])
        tree_data = json.loads(tree_output)
        child_to_parents = defaultdict(set)
        for entry in tree_data:
            parent = entry["package"]["key"].lower()
            for dep in entry.get("dependencies", []):
                child = dep["key"].lower()
                child_to_parents[child].add(parent)

        def is_top_level(pkg):
            return pkg.lower() in {p.lower() for p in declared}

        for pkg in licenses_data:
            name = pkg["Name"]
            version = pkg["Version"]
            license_type = pkg["License"]
            top_level = is_top_level(name)
            if include_transitive or top_level:
                results.append({
                    "name": name,
                    "version": version,
                    "license": license_type,
                    "source": "python",
                    "transitive": not top_level
                })
    return results

def get_python_license_texts(requirements_files, include_transitive):
    declared = get_declared_python_packages(requirements_files)
    licenses = []
    with tempfile.TemporaryDirectory() as tmpdir:
        env_path = Path(tmpdir)
        venv.create(env_path, with_pip=True)
        pip_path = env_path / "bin" / "pip"
        python_path = env_path / "bin" / "python"

        for req in requirements_files:
            if Path(req).exists():
                run_command([str(pip_path), "install", "-r", req])
        run_command([str(pip_path), "install", "pip-licenses"])

        output_json = run_command([
            str(python_path), "-m", "piplicenses",
            "--format=json",
            "--with-license-file",
            "--with-authors"
        ])
        data = json.loads(output_json)

        for item in data:
            name = item["Name"]
            version = item["Version"]
            license_text = item.get("LicenseText") or ""
            is_transitive = name.lower() not in {pkg.lower() for pkg in declared}
            if include_transitive or not is_transitive:
                licenses.append((f"{name}=={version}", license_text.strip()))
    return licenses

def get_node_licenses(package_file, include_transitive, include_dev):
    declared = get_declared_node_packages(package_file, include_dev)
    license_data_raw = run_command(["license-checker", "--json"], cwd=Path.cwd())
    data = json.loads(license_data_raw)
    results = []
    for full_key, meta in data.items():
        name, version = full_key.rsplit("@", 1) if "@" in full_key else (full_key, "unknown")
        is_top_level = name in declared
        if include_transitive or is_top_level:
            results.append({
                "name": name,
                "version": version,
                "license": meta.get("licenses", "UNKNOWN"),
                "source": package_file,
                "transitive": not is_top_level
            })
    return results

def get_node_license_texts(package_file, include_transitive, include_dev):
    declared = get_declared_node_packages(package_file, include_dev)
    license_data_raw = run_command(["license-checker", "--json"], cwd=Path.cwd())
    data = json.loads(license_data_raw)
    licenses = []
    for full_key, meta in data.items():
        name, version = full_key.rsplit("@", 1) if "@" in full_key else (full_key, "unknown")
        is_transitive = name not in declared
        if include_transitive or not is_transitive:
            license_path = meta.get("licenseFile")
            license_text = ""
            if license_path and Path(license_path).exists():
                try:
                    license_text = Path(license_path).read_text(encoding="utf-8", errors="ignore").strip()
                except Exception as e:
                    license_text = f"[Could not read license from {license_path}: {e}]"
            licenses.append((f"{name}@{version}", license_text))
    return licenses

def format_output(data, format):
    if format == "json":
        return json.dumps(data, indent=2)
    elif format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    elif format == "markdown":
        headers = list(data[0].keys())
        lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
        for row in data:
            lines.append("| " + " | ".join(str(row[h]) for h in headers) + " |")
        return "\n".join(lines)
    else:
        raise ValueError("Unsupported format")

@click.group()
def cli():
    """License inspection tool for Python and Node.js dependencies."""
    pass

@cli.command("list")
@click.option("--output", "-o", type=click.Path(writable=True), help="Save output to file")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "markdown"], case_sensitive=False), default="json", help="Output format")
@click.option("--transitive", is_flag=True, default=False, help="Include transitive dependencies")
@click.option("--dev", is_flag=True, default=False, help="Include dev dependencies")
def list_licenses(output, format, transitive, dev):
    requirements_files = ["requirements.txt", "requirements-mcp.txt"]
    if dev:
        requirements_files.append("requirements-dev.txt")
    package_file = "package.json"

    click.echo(f"🔍 Getting Python licenses (transitive: {transitive}, dev: {dev})...")
    python_licenses = get_python_licenses(requirements_files, include_transitive=transitive)

    click.echo(f"🔍 Getting Node.js licenses (transitive: {transitive}, dev: {dev})...")
    node_licenses = get_node_licenses(package_file, include_transitive=transitive, include_dev=dev)

    all_licenses = sorted(python_licenses + node_licenses, key=lambda x: x["name"].lower())
    output_text = format_output(all_licenses, format)

    if output:
        with open(output, "w") as f:
            f.write(output_text)
        click.echo(f"✅ License info written to {output}")
    else:
        click.echo(output_text)

@cli.command("generate-notice")
@click.option("--output", "-o", type=click.Path(writable=True), default="NOTICE.txt", show_default=True, help="Path to NOTICE file")
@click.option("--transitive", is_flag=True, default=False, help="Include transitive dependencies")
@click.option("--dev", is_flag=True, default=False, help="Include dev dependencies")
def generate_notice(output, transitive, dev):
    requirements_files = ["requirements.txt", "requirements-mcp.txt"]
    if dev:
        requirements_files.append("requirements-dev.txt")
    package_file = "package.json"

    click.echo("🔍 Getting Python license contents (transitive: {transitive}, dev: {dev})...")
    python_licenses = get_python_license_texts(requirements_files, include_transitive=transitive)

    click.echo("🔍 Getting Node.js license contents (transitive: {transitive}, dev: {dev})...")
    node_licenses = get_node_license_texts(package_file, include_transitive=transitive, include_dev=dev)

    click.echo(f"📝 Writing {output} ...")
    seen = set()
    with open(output, "w", encoding="utf-8") as f:
        f.write(NOTICE_HEADER + "\n")
        for name, text in sorted(python_licenses + node_licenses):
            if (name, text) in seen:
                continue
            seen.add((name, text))
            f.write(f"{'=' * 80}\n")
            f.write(f"{name}\n")
            f.write(f"{'-' * 80}\n")
            f.write(f"{text}\n\n")

    click.echo(f"✅ NOTICE file written to {output}")

@cli.command("summarize")
@click.option("--format", "-f", type=click.Choice(["json", "csv", "markdown"], case_sensitive=False), default="json", help="Output format")
@click.option("--transitive", is_flag=True, default=False, help="Include transitive dependencies")
@click.option("--dev", is_flag=True, default=False, help="Include dev dependencies")
def summarize(format, transitive, dev):
    requirements_files = ["requirements.txt", "requirements-mcp.txt"]
    if dev:
        requirements_files.append("requirements-dev.txt")
    package_file = "package.json"

    click.echo(f"🔍 Getting Python licenses (transitive: {transitive}, dev: {dev})...")
    python_licenses = get_python_licenses(requirements_files, include_transitive=transitive)
    click.echo(f"🔍 Getting Node.js licenses (transitive: {transitive}, dev: {dev})...")
    node_licenses = get_node_licenses(package_file, include_transitive=transitive, include_dev=dev)
    all_licenses = python_licenses + node_licenses

    counter = Counter(pkg["license"] for pkg in all_licenses)
    summary = [{"license": lic, "count": count} for lic, count in counter.most_common()]
    output_text = format_output(summary, format)
    click.echo(output_text)

if __name__ == "__main__":
    cli()