# skill-lint

Linter and health checker for agent `SKILL.md` files (Hermes Agent Skills, Anthropic Agent Skills, and compatible formats).

Agent skill ecosystems are where npm was in 2012: everyone hand-writes package metadata and finds out it is invalid by getting rejected at publish time. `skill-lint` catches problems before that, and keeps a skills repo healthy as it grows.

## Install

```bash
uv tool install git+https://github.com/agent-julia/skill-lint.git
# or from source
uv sync && uv run skill-lint --help
```

## Usage

```bash
skill-lint lint path/to/SKILL.md
skill-lint lint skills/              # recursive
skill-lint lint skills/ --json       # machine-readable
skill-lint lint skills/ --profile spec   # agentskills.io limits instead of Hermes defaults
```

Exit code is 1 when any error-level finding exists, 0 otherwise — CI friendly.

## Profiles

- `hermes` (default) — Hermes Agent Skills limits: description max 64 chars, trigger phrase required
- `spec` — agentskills.io limits: description max 1024, compatibility max 500, no trigger requirement

## Checks

- `yaml-parseable` — frontmatter must be valid YAML mapping
- `frontmatter-typos` — unknown keys that look like misspellings of known ones (`descrption` → `description`)
- `name-present`, `name-format` — required, `^[a-z0-9][a-z0-9\-_]*$`, max 64 chars
- `description-present`, `description-length` — required, within profile limit
- `description-trigger` — first 57 chars should be a self-contained trigger (`Use when ...`); hermes profile only
- `compatibility-length` — within profile limit; spec profile only
- `no-pruned-marker` — flags `[SKILL_PRUNED]`, the marker left when a skill loses content to context compaction
- `body-size` — warn if thinner than 5 lines or heavier than 250 lines
- `asset-refs` — `references/`, `templates/`, `scripts/` paths mentioned in the body must exist (dead-link check)
- `asset-orphan` — a `references/`, `templates/`, or `scripts/` directory with files that no body text links to
- `script-executable` — referenced files under `scripts/` must have the executable bit
- `token-estimate` — rough tokens-on-load estimate, warn above 4000
- `duplicate-name` (repo-level) — two SKILL.md files claiming the same name

Findings that have an obvious fix carry a `fix:` suggestion line (and a
`suggestion` field in JSON output).

## Design

- Standard library plus PyYAML only; no framework.
- One rule = one small function returning findings. Add a rule by adding a function and one entry to `RULES`.
- Rules report; they never rewrite content.

## License

MIT
