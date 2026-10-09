"""Parse SKILL.md frontmatter and body."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DELIM = "---"


@dataclass
class SkillFile:
    """A parsed SKILL.md with frontmatter, body, and any parse error."""

    path: Path
    frontmatter: dict
    body: str
    raw: str
    yaml_error: str | None = field(default=None)


def parse_skill(path: Path) -> SkillFile:
    """Parse a SKILL.md file into frontmatter dict and markdown body."""
    raw = path.read_text(encoding="utf-8")
    frontmatter: dict = {}
    body = raw
    yaml_error = None
    if raw.startswith(DELIM):
        end = raw.find("\n" + DELIM, len(DELIM))
        if end != -1:
            try:
                loaded = yaml.safe_load(raw[len(DELIM) : end])
                if isinstance(loaded, dict):
                    frontmatter = loaded
                elif loaded is not None:
                    yaml_error = "frontmatter is not a mapping"
            except yaml.YAMLError as exc:
                yaml_error = str(exc).split("\n")[0]
            # skip the closing delimiter plus its newline
            body = raw[end + len(DELIM) + 1 :]
        else:
            yaml_error = "opening --- has no closing ---"
    return SkillFile(path=path, frontmatter=frontmatter, body=body, raw=raw, yaml_error=yaml_error)
