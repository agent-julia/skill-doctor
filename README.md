# skill-doctor

Linter and health checker for agent `SKILL.md` files (Hermes Agent Skills, Anthropic Agent Skills, and compatible formats).

Agent skill ecosystems are where npm was in 2012: everyone hand-writes package metadata and finds out it is invalid by getting rejected at publish time. `skill-doctor` catches problems before that, and keeps a skills repo healthy as it grows.

## Install

```bash
uv tool install git+https://github.com/agent-julia/skill-doctor.git
# or from source
uv sync && uv run skill-doctor --help
```

## Usage

```bash
skill-doctor lint path/to/SKILL.md
skill-doctor lint skills/              # recursive
skill-doctor lint skills/ --json       # machine-readable
```

Exit code is 1 when any error-level finding exists, 0 otherwise — CI friendly.

## Checks

- `yaml-parseable` — frontmatter must be valid YAML mapping
- `name-present`, `name-format` — required, `^[a-z0-9][a-z0-9\-_]*$`, max 64 chars
- `description-present`, `description-length` — required, max 64 chars
- `description-trigger` — first 57 chars should be a self-contained trigger (`Use when ...`)
- `no-pruned-marker` — flags `[SKILL_PRUNED]`, the marker left when a skill loses content to context compaction
- `body-size` — warn if thinner than 5 lines or heavier than 250 lines
- `asset-refs` — `references/`, `templates/`, `scripts/` paths mentioned in the body must exist
- `token-estimate` — rough tokens-on-load estimate, warn above 4000
- `duplicate-name` (repo-level) — two SKILL.md files claiming the same name

## Design

- Standard library plus PyYAML only; no framework.
- One rule = one small function returning findings. Add a rule by adding a function and one entry to `RULES`.
- Rules report; they never rewrite content.

## License

MIT
