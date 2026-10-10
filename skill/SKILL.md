---
name: skill-lint
description: "Use when linting SKILL.md files: frontmatter, size, assets."
---

# skill-lint

CLI linter for Agent Skill files (SKILL.md + asset folders). Catches the
failure classes that make skills undiscoverable or token-hungry before they
reach an agent.

Repo: `agent-julia/skill-lint` (install from source, uv).

## Install

```bash
git clone https://github.com/agent-julia/skill-lint
cd skill-lint
uv tool install .
```

## Use

```bash
skill-lint lint path/to/SKILL.md
skill-lint lint skills/ --json          # CI output
skill-lint lint skills/ --profile spec  # agentskills.io-style third-party skills
```

Exit code: `0` = clean, `1` = at least one error. Warnings do not fail the
build; every finding carries a `fix:` suggestion line.

## Rules

- `frontmatter-yaml` — frontmatter must parse as YAML with `name`.
- `frontmatter-typos` — unknown keys near-matching known ones (difflib 0.85).
- `name-format` — lowercase, hyphens/underscores, ≤64 chars.
- `description-length` — ≤64 chars (Hermes profile).
- `description-trigger` — first 57 chars must be a self-contained trigger
  starting with `Use when`.
- `pruned-marker` — fail on `[SKILL_PRUNED]` (lost content after compaction).
- `body-size` — body ≤250 lines (over-engineering smell).
- `token-estimate` — warn >4000 tokens on load; loading a fat skill burns
  context every session.
- `asset-refs` — every `references/` `templates/` `scripts/` link must exist
  (no dead links).
- `asset-orphan` — non-empty asset folders must be linked from the body.
- `script-executable` — linked scripts must be executable.
- `duplicate-names` — skill name must be unique across the scanned tree.

## Profiles

- `hermes` (default) — desc ≤64, trigger prefix `Use when`. Use for skills
  that run inside Hermes.
- `spec` — desc ≤1024, no trigger requirement. Use for third-party skills
  written against the agentskills.io spec.

## Design stance

Suggest-only: the linter never rewrites files. Keep skills lean; a skill that
loads 9k tokens of prose costs that context in every session that touches it.
