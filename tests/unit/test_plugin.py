"""Tests for the `relevance-studio` Claude plugin.

Guards against drift between the plugin's skills (`src/skills/`), its manifest
(`.claude-plugin/marketplace.json`), and the MCP tool surface it documents
(`src/server/fastmcp.py`). See `src/skills/AGENTS.md` for the conventions these
checks enforce.

Catalog note: the plugin is being built in phases (see the project's plugin
plan). `EXPECTED_FINAL_CATALOG` lists the full, eventual set of 28 skills.
Until every phase lands, the skills actually present on disk are a *subset* of
that list — `test_catalog_is_subset_of_final_catalog` enforces that subset
relationship (catching typos or unexpected directories) without requiring every
skill to exist yet. A future finishing touch (tracked in `src/skills/AGENTS.md`)
should tighten this to an equality check once all 28 skills exist.
"""

import ast
import json
import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
MARKETPLACE_PATH = REPO_ROOT / ".claude-plugin" / "marketplace.json"
SKILLS_DIR = REPO_ROOT / "src" / "skills"
FASTMCP_PATH = REPO_ROOT / "src" / "server" / "fastmcp.py"
VERSION_PATH = REPO_ROOT / "src" / "server" / "VERSION"
PACKAGE_JSON_PATH = REPO_ROOT / "package.json"

SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_SKILL_NAME_LEN = 64
MAX_DESCRIPTION_LEN = 1024
MAX_SKILL_MD_LINES = 500

# The eventual full catalog across all 5 build phases. See module docstring.
EXPECTED_FINAL_CATALOG = {
    "studio-fundamentals",
    "tagging-conventions",
    "connect-and-verify",
    "upgrade-and-maintenance",
    "workspace-bootstrap",
    "judgement-rubric",
    "content-profiling",
    "display-authoring",
    "scenario-generation",
    "judgement-pooling",
    "llm-judging",
    "judgement-audit",
    "judgement-gap-fill",
    "strategy-authoring",
    "baseline-suite",
    "strategy-diagnosis",
    "strategy-experiments",
    "benchmark-design",
    "evaluation-execution",
    "evaluation-analysis",
    "evaluation-comparison",
    "lifecycle-orchestrator",
    "improvement-loop",
    "stakeholder-report",
    "workspace-hygiene",
    "assets-as-code",
    "ci-gate",
    "conversation-journaling",
}

CODE_ONLY_SKILLS = {"assets-as-code", "ci-gate"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_marketplace():
    return json.loads(MARKETPLACE_PATH.read_text(encoding="utf-8"))


def _discover_skill_files():
    """Return a dict of {skill_name: SKILL.md path} for stable + experimental skills.

    Only immediate subdirectories of src/skills/ (and their experimental/
    children) are considered skills, so src/skills/AGENTS.md is never mistaken
    for one.
    """
    skills = {}
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        stable_md = entry / "SKILL.md"
        experimental_md = entry / "experimental" / "SKILL.md"
        if stable_md.exists():
            skills[entry.name] = stable_md
        elif experimental_md.exists():
            skills[entry.name] = experimental_md
    return skills


def _parse_frontmatter(path: Path):
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} must start with a YAML frontmatter block"
    end = text.index("\n---", 4)
    raw_frontmatter = text[4:end]
    body = text[end + 4 :].lstrip("\n")
    frontmatter = yaml.safe_load(raw_frontmatter)
    return frontmatter, body, raw_frontmatter


def _extract_mcp_tool_names():
    """Parse fastmcp.py with ast and collect every @mcp.tool / @mcp.tool(...) name."""
    tree = ast.parse(FASTMCP_PATH.read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for dec in node.decorator_list:
            target = dec.func if isinstance(dec, ast.Call) else dec
            if (
                isinstance(target, ast.Attribute)
                and target.attr == "tool"
                and isinstance(target.value, ast.Name)
                and target.value.id == "mcp"
            ):
                names.append(node.name)
    return set(names)


BACKTICK_RE = re.compile(r"`([a-zA-Z0-9_]+)`")


def _candidate_tool_references(body: str):
    """Bare-word backticked identifiers that look like tool names (snake_case,
    contains an underscore) rather than skill names or other code terms.
    """
    return {
        m for m in BACKTICK_RE.findall(body)
        if "_" in m and not m.startswith("mcp__")
    }


SKILL_REF_RE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`\s+skill")
NEXT_STEPS_RE = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")


# ---------------------------------------------------------------------------
# 1. Manifest
# ---------------------------------------------------------------------------


def test_marketplace_manifest_parses_and_has_expected_shape():
    data = _load_marketplace()
    assert data["name"] == "elastic-relevance-studio"
    assert "plugins" in data and len(data["plugins"]) == 1
    plugin = data["plugins"][0]
    assert plugin["name"] == "relevance-studio"
    assert plugin["strict"] is False
    skills_path = (REPO_ROOT / plugin["skills"].lstrip("./")).resolve()
    assert skills_path == SKILLS_DIR.resolve()
    assert skills_path.is_dir()
    assert "mcp_url" in plugin["userConfig"]
    assert "auth_header" in plugin["userConfig"]
    assert plugin["userConfig"]["auth_header"].get("sensitive") is True
    # auth_header must stay optional: Relevance Studio supports Basic, ApiKey,
    # Bearer, or no auth (AUTH_ENABLED=false) — it must not force one scheme.
    assert plugin["userConfig"]["auth_header"].get("required") is not True
    assert "relevance-studio" in plugin["mcpServers"]


# ---------------------------------------------------------------------------
# 2. Version lockstep
# ---------------------------------------------------------------------------


def test_version_lockstep_across_manifest_version_and_package_json():
    marketplace_version = _load_marketplace()["plugins"][0]["version"]
    server_version = VERSION_PATH.read_text(encoding="utf-8").strip()
    package_json_version = json.loads(PACKAGE_JSON_PATH.read_text(encoding="utf-8"))["version"]
    assert marketplace_version == server_version == package_json_version, (
        f"version mismatch: marketplace={marketplace_version!r} "
        f"VERSION={server_version!r} package.json={package_json_version!r}"
    )


# ---------------------------------------------------------------------------
# 3. Frontmatter
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skill_name,skill_path",
    sorted(_discover_skill_files().items()),
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_skill_frontmatter_is_well_formed(skill_name, skill_path):
    frontmatter, body, raw_frontmatter = _parse_frontmatter(skill_path)

    assert set(frontmatter.keys()) == {"name", "description"}, (
        f"{skill_path} frontmatter must contain exactly 'name' and 'description', "
        f"got {sorted(frontmatter.keys())}"
    )
    # Both values must have been double-quoted strings in the source YAML.
    for key in ("name", "description"):
        line_prefix = f'{key}: "'
        assert line_prefix in raw_frontmatter, (
            f"{skill_path}: {key!r} must be a double-quoted string"
        )

    name = frontmatter["name"]
    description = frontmatter["description"]

    assert name == skill_name, f"{skill_path}: frontmatter name {name!r} != directory name {skill_name!r}"
    assert SKILL_NAME_RE.match(name), f"{skill_path}: name {name!r} must match {SKILL_NAME_RE.pattern}"
    assert len(name) <= MAX_SKILL_NAME_LEN

    assert description, f"{skill_path}: description must not be empty"
    assert len(description) <= MAX_DESCRIPTION_LEN, (
        f"{skill_path}: description is {len(description)} chars, max {MAX_DESCRIPTION_LEN}"
    )
    assert description.startswith("Use when") or description.startswith("Use whenever"), (
        f"{skill_path}: description must start with 'Use when' or 'Use whenever'"
    )
    if skill_name in CODE_ONLY_SKILLS:
        assert description.rstrip().endswith(
            "Requires Claude Code (shell and filesystem access)."
        ), f"{skill_path}: Code-only skill description must end with the Code-only suffix"


# ---------------------------------------------------------------------------
# 4. Catalog completeness
# ---------------------------------------------------------------------------


def test_catalog_is_subset_of_final_catalog():
    discovered = set(_discover_skill_files().keys())
    unexpected = discovered - EXPECTED_FINAL_CATALOG
    assert not unexpected, f"skill(s) not in the planned catalog: {sorted(unexpected)}"


def test_no_duplicate_or_orphaned_skill_directories():
    # Every immediate subdirectory of src/skills/ must resolve to exactly one
    # SKILL.md, either directly or via experimental/.
    discovered = _discover_skill_files()
    for entry in sorted(SKILLS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        assert entry.name in discovered, (
            f"{entry} has no SKILL.md (checked both {entry.name}/SKILL.md and "
            f"{entry.name}/experimental/SKILL.md)"
        )


# ---------------------------------------------------------------------------
# 5 & 6. Tool drift (forward and reverse)
# ---------------------------------------------------------------------------


def test_every_tool_referenced_in_a_skill_actually_exists():
    mcp_tools = _extract_mcp_tool_names()
    skills = _discover_skill_files()
    for skill_name, path in skills.items():
        _, body, _ = _parse_frontmatter(path)
        tools_section_match = re.search(r"## Tools\n(.*?)(\n## |\Z)", body, re.DOTALL)
        if not tools_section_match:
            continue
        referenced = _candidate_tool_references(tools_section_match.group(1))
        unknown = referenced - mcp_tools
        assert not unknown, (
            f"{path}: ## Tools references unknown tool name(s) {sorted(unknown)}; "
            f"known MCP tools are {sorted(mcp_tools)}"
        )


def test_every_mcp_tool_is_documented_in_mcp_tools_reference():
    mcp_tools = _extract_mcp_tool_names()
    reference_path = SKILLS_DIR / "studio-fundamentals" / "references" / "mcp-tools.md"
    assert reference_path.exists(), (
        "studio-fundamentals/references/mcp-tools.md is required and must document "
        "every MCP tool"
    )
    reference_text = reference_path.read_text(encoding="utf-8")
    missing = {tool for tool in mcp_tools if tool not in reference_text}
    assert not missing, f"mcp-tools.md is missing documentation for: {sorted(missing)}"


# ---------------------------------------------------------------------------
# 7. Cross-references
# ---------------------------------------------------------------------------


def test_cross_referenced_skills_exist():
    discovered = set(_discover_skill_files().keys())
    skills = _discover_skill_files()
    for skill_name, path in skills.items():
        _, body, _ = _parse_frontmatter(path)
        referenced_as_skill = set(SKILL_REF_RE.findall(body))

        next_steps_match = re.search(r"## Next steps\n(.*?)(\n## |\Z)", body, re.DOTALL)
        referenced_in_next_steps = set()
        if next_steps_match:
            referenced_in_next_steps = set(NEXT_STEPS_RE.findall(next_steps_match.group(1)))
            # Only keep ones that look like skill names (exist in the final
            # catalog or are already-discovered skills); tool names can also be
            # backticked in prose here, so filter to plausible skill-name shape.
            referenced_in_next_steps &= (EXPECTED_FINAL_CATALOG | discovered)

        for ref in referenced_as_skill | referenced_in_next_steps:
            assert ref in discovered or ref in EXPECTED_FINAL_CATALOG, (
                f"{path}: references unknown skill `{ref}`"
            )


# ---------------------------------------------------------------------------
# 8. Hygiene
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "skill_name,skill_path",
    sorted(_discover_skill_files().items()),
    ids=lambda v: v if isinstance(v, str) else None,
)
def test_skill_hygiene(skill_name, skill_path):
    text = skill_path.read_text(encoding="utf-8")
    assert "mcp__" not in text, f"{skill_path}: must not reference client-prefixed mcp__ tool names"

    line_count = len(text.splitlines())
    assert line_count <= MAX_SKILL_MD_LINES, (
        f"{skill_path}: {line_count} lines exceeds the {MAX_SKILL_MD_LINES}-line hard limit"
    )

    if skill_name != "studio-fundamentals":
        assert "studio-fundamentals" in text, (
            f"{skill_path}: non-foundation skills must mention `studio-fundamentals` "
            "in their Prerequisites section"
        )


# ---------------------------------------------------------------------------
# 9. Agent instruction files
# ---------------------------------------------------------------------------


def test_agent_instruction_files_exist_and_are_wired_correctly():
    agents_md = REPO_ROOT / "AGENTS.md"
    claude_md = REPO_ROOT / "CLAUDE.md"
    skills_agents_md = SKILLS_DIR / "AGENTS.md"

    assert agents_md.exists()
    assert skills_agents_md.exists()

    assert claude_md.is_symlink(), "CLAUDE.md must be a symlink to AGENTS.md"
    import os

    target = os.readlink(claude_md)
    assert target == "AGENTS.md", f"CLAUDE.md symlink target is {target!r}, expected 'AGENTS.md'"

    assert "src/skills/AGENTS.md" in agents_md.read_text(encoding="utf-8")


def test_skills_agents_md_is_never_discovered_as_a_skill():
    # src/skills/AGENTS.md lives alongside skill directories but is a file, not
    # a directory, so skill discovery (which only considers directories) must
    # never pick it up.
    discovered = _discover_skill_files()
    assert "AGENTS.md" not in discovered
    assert "AGENTS" not in discovered
