# Managing the `relevance-studio` plugin's skills

This is the living, authoritative guide for the skills in this directory. It supersedes any
external spec that was used to originally design the plugin. Read it before creating,
editing, renaming, removing, or reviewing anything under `src/skills/` or `.claude-plugin/`.

## Purpose and scope

These skills teach Claude Code and Claude Desktop how to operate Elasticsearch Relevance
Studio through its MCP server. They ship inside the `relevance-studio` plugin, defined in
`.claude-plugin/marketplace.json`. The plugin namespace prefixes every skill name, so a
skill directory named `workspace-bootstrap` is invoked as
`relevance-studio:workspace-bootstrap` — but refer to skills by their bare name (no prefix)
in SKILL.md prose; the prefix is a client-side invocation detail, not something skills should
hard-code.

This file itself is **not** a skill. It must never be moved into a skill directory or given
a `SKILL.md` name.

## Layout

```
src/skills/
  AGENTS.md                 <- this file, not a skill
  <skill-name>/
    SKILL.md
    references/*.md         (optional — bulky material referenced from SKILL.md)
    scripts/*                (optional — shell helpers, Code-only skills)
  <skill-name>/
    experimental/
      SKILL.md               <- experimental skills nest one level deeper, with
                                 NO SKILL.md in the parent directory
```

The `experimental/` nesting is how a skill is gated out of the stable set — there is no
separate manifest flag for it. Promoting an experimental skill means moving
`<name>/experimental/SKILL.md` (and its `references/`/`scripts/`) up to `<name>/SKILL.md`.

## Authoring conventions

### Naming and frontmatter

- The directory name equals the frontmatter `name`. For experimental skills, the **parent**
  directory name is the skill name (e.g. `assets-as-code/experimental/SKILL.md` has
  `name: "assets-as-code"`).
- Names are unprefixed kebab-case matching `^[a-z0-9]+(-[a-z0-9]+)*$`, at most 64 characters.
- Frontmatter contains exactly two keys, `name` and `description`, both double-quoted:
  ```yaml
  ---
  name: "benchmark-design"
  description: "Use when …"
  ---
  ```
- `description` must:
  - be 1,024 characters or fewer, and start with "Use when" or "Use whenever";
  - name concrete triggers, including phrasings users actually say (e.g. "NDCG", "test
    queries", "why is this result ranked low");
  - trigger **broadly** — Claude tends to under-trigger skills, so err toward more scenarios
    rather than fewer;
  - end with the literal sentence "Requires Claude Code (shell and filesystem access)." for
    Code-only skills (currently `assets-as-code` and `ci-gate`).

### Body structure

Use these sections, in this order, omitting any that don't apply:

```
## When this applies
## Prerequisites
## Tools
## Procedure
## Guardrails
## Examples            (Correct / Incorrect pairs)
## Next steps          (hand-offs to other skills, by name)
```

- **Prerequisites.** Every skill except `studio-fundamentals` starts this section with:
  *"If you haven't loaded the `studio-fundamentals` skill in this conversation, load it
  first."* State any workspace requirement here too.
- **Length.** Target 300 lines or fewer per `SKILL.md`, hard limit 500. Move bulky reference
  material into `references/` and say in the body when to read it.
- **Examples.** At least one Correct/Incorrect pair for the skill's most common mistake,
  formatted as a bold label plus a short prose example (see `studio-fundamentals/SKILL.md`
  or `connect-and-verify/SKILL.md` for the pattern).

### Referring to tools and skills

- Refer to MCP tools by **bare tool name** in backticks: `` `scenarios_search` ``. Never use
  a client-specific prefixed name (e.g. `mcp__...`) — the prefix differs between the Claude
  Code plugin connection and the Desktop connector.
- Refer to other skills by bare skill name in backticks: "hand off to the
  `benchmark-design` skill." Never reference another skill's file path.

### Surface neutrality

- Every skill must be completable with MCP tools alone — Claude Desktop may not have a
  shell. Bundled scripts (`scripts/`) are optional accelerators used only when a shell is
  available; the `SKILL.md` must describe the no-shell fallback.
- `assets-as-code` and `ci-gate` are the only Code-only exceptions, and their descriptions
  say so explicitly.

### Shared knowledge

`src/skills/studio-fundamentals/references/` is the single home for data-model, MCP-tool,
gotcha, deep-link, and metric knowledge. Every other skill links to it by skill name
(`studio-fundamentals`) rather than duplicating its content. If you learn a new trap or
verify a new tool behavior, add it there, not in the skill where you happened to discover it.

### Inherited behavioral rules

Every skill relies on the rules defined in `studio-fundamentals/SKILL.md`: scope operations
to a `workspace_id`, never fabricate `_id`/`doc_id` values, use display-driven `_source`
filtering, confirm before bulk operations (>10 creates/updates, or any delete), confirm
before touching a workspace other than the active one, refer to assets by name not ID, never
dump raw JSON, and explain tool errors in plain language.

## Checklists

### Add a skill

1. Create `src/skills/<name>/SKILL.md` (or `src/skills/<name>/experimental/SKILL.md` if
   experimental) following the conventions above.
2. Add its name to the catalog list asserted in `tests/unit/test_plugin.py`.
3. Add it to the routing table in `studio-fundamentals/SKILL.md` ("Which skill do I need?").
4. Add `## Next steps` hand-offs in whichever skills logically lead to it.
5. Run `pytest tests/unit/test_plugin.py`.

### Rename a skill

1. Rename the directory and update `name` in its frontmatter.
2. Update every cross-reference (routing table, other skills' `## Next steps`, the catalog
   test).
3. Mention the rename in release notes — it changes users' slash-command invocation.

### Remove a skill

Same updates as a rename, plus delete any hand-offs that pointed to it from other skills.

### Promote an experimental skill

1. Move `<name>/experimental/*` up to `<name>/` (delete the now-empty `experimental/` dir).
2. Update its status everywhere it's listed (routing table, any status note in another
   skill).
3. Re-run `pytest tests/unit/test_plugin.py`.
4. Mention the promotion in release notes.

### MCP or API changed

1. Update `studio-fundamentals/references/mcp-tools.md` and `gotchas.md` to reflect the new
   behavior.
2. Update the `## Tools` and `## Procedure` sections of every affected skill.
3. Run `pytest tests/unit/test_plugin.py` — the tool-drift check will catch references to
   tools that no longer exist, but it can't catch a tool whose *behavior* changed without a
   name change, so review manually too.

## Testing

- **Automated:** `pytest tests/unit/test_plugin.py` (or `./scripts/test.sh --lang py --type
  unit`, which runs the whole `tests/unit` suite). It checks: manifest validity, version
  lockstep across `marketplace.json`/`VERSION`/`package.json`, frontmatter shape, catalog
  completeness, MCP tool-name drift (both directions), cross-reference integrity, and basic
  hygiene (no `mcp__` prefixes, line limits, Prerequisites mentions
  `studio-fundamentals`).
- **Manual, Claude Code:** load the plugin from a local checkout and run a realistic prompt
  that should trigger the skill you're testing; confirm it triggers and that the tool calls
  it makes actually succeed against a running MCP server. (The exact local-marketplace
  command for this hasn't been finalized — verify against the current Claude Code docs and
  record the working command here once confirmed.)
- **Manual, Claude Desktop:** required for any skill that isn't Code-only, since Desktop has
  no shell and may handle the plugin's `mcpServers`/`userConfig` differently than Claude
  Code.

## Versioning

Never bump the plugin version by hand. `scripts/release.sh` keeps
`.claude-plugin/marketplace.json`'s `plugins[0].version` in lockstep with
`src/server/VERSION` and `package.json`. Skill changes ship with the next product release —
there's no independent plugin release cadence.

## Do / don't

- **Don't** use prefixed `mcp__...` tool names in skill prose — use the bare tool name.
- **Don't** fabricate IDs in examples (e.g. don't write `workspace_id: "abc123"` as if it
  were a plausible-looking real value) — show the lookup step instead.
- **Don't** write an example query against content indices without `_source` filtering.
- **Don't** duplicate reference content across skills — link to
  `studio-fundamentals/references/` instead.
- **Don't** write a description that summarizes what the skill *does* instead of *when to use
  it*. "Manages workspace creation" is wrong; "Use when the user wants to start relevance
  testing for a new search use case..." is right.
- **Do** keep descriptions broad — err toward over-triggering, not under-triggering.
