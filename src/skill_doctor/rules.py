"""Lint rules for SKILL.md files. Each rule is one small function."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .frontmatter import SkillFile

NAME_MAX = 64
DESC_MAX = 64
DESC_TRIGGER_CHARS = 57
BODY_MIN_LINES = 5
BODY_MAX_LINES = 250
TOKEN_WARN = 4000

SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]*$")
ASSET_RE = re.compile(r"\b(references|templates|scripts)/[\w\-./]+")
PRUNED_MARK = "[SKILL_PRUNED]"


@dataclass
class Finding:
    """One lint finding."""

    severity: str
    rule: str
    message: str
    path: Path

    def format(self) -> str:
        return f"{self.severity.upper():5} {self.rule:22} {self.path}: {self.message}"


def rule_yaml(skill: SkillFile) -> list[Finding]:
    if skill.yaml_error:
        return [Finding("error", "yaml-parseable", skill.yaml_error, skill.path)]
    return []


def rule_name_present(skill: SkillFile) -> list[Finding]:
    if "name" not in skill.frontmatter:
        return [Finding("error", "name-present", "frontmatter missing 'name'", skill.path)]
    return []


def rule_name_format(skill: SkillFile) -> list[Finding]:
    name = skill.frontmatter.get("name")
    if not isinstance(name, str) or not name:
        return [Finding("error", "name-format", "'name' must be a non-empty string", skill.path)]
    findings = []
    if len(name) > NAME_MAX:
        findings.append(Finding("error", "name-format", f"name is {len(name)} chars (max {NAME_MAX})", skill.path))
    if not NAME_RE.match(name):
        findings.append(Finding("error", "name-format", f"name '{name}' must be lowercase, digits, hyphens, underscores", skill.path))
    return findings


def rule_description_present(skill: SkillFile) -> list[Finding]:
    if "description" not in skill.frontmatter:
        return [Finding("error", "description-present", "frontmatter missing 'description'", skill.path)]
    return []


def rule_description_length(skill: SkillFile) -> list[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or not desc:
        return [Finding("error", "description-length", "'description' must be a non-empty string", skill.path)]
    if len(desc) > DESC_MAX:
        return [Finding("error", "description-length", f"description is {len(desc)} chars (max {DESC_MAX})", skill.path)]
    return []


def rule_description_trigger(skill: SkillFile) -> list[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str):
        return []
    trigger = desc[:DESC_TRIGGER_CHARS]
    if not trigger.startswith("Use when"):
        return [Finding("warn", "description-trigger", f"first {DESC_TRIGGER_CHARS} chars should be a self-contained trigger starting with 'Use when'", skill.path)]
    return []


def rule_pruned_marker(skill: SkillFile) -> list[Finding]:
    if PRUNED_MARK in skill.raw:
        return [Finding("error", "no-pruned-marker", f"contains '{PRUNED_MARK}'; skill lost content to compaction — reload it", skill.path)]
    return []


def rule_body_size(skill: SkillFile) -> list[Finding]:
    lines = skill.body.strip().splitlines()
    if len(lines) < BODY_MIN_LINES:
        return [Finding("warn", "body-size", f"body is {len(lines)} lines (min {BODY_MIN_LINES}); too thin to be useful", skill.path)]
    if len(lines) > BODY_MAX_LINES:
        return [Finding("warn", "body-size", f"body is {len(lines)} lines (max {BODY_MAX_LINES}); likely over-engineered and token-hungry", skill.path)]
    return []


def rule_asset_refs(skill: SkillFile) -> list[Finding]:
    findings = []
    checked: set[str] = set()
    for match in ASSET_RE.finditer(skill.body):
        rel = match.group(0)
        if rel in checked:
            continue
        checked.add(rel)
        if not (skill.path.parent / rel).exists():
            findings.append(Finding("warn", "asset-refs", f"referenced file '{rel}' does not exist", skill.path))
    return findings


def rule_token_estimate(skill: SkillFile) -> list[Finding]:
    estimate = len(skill.raw) // 4
    if estimate > TOKEN_WARN:
        return [Finding("warn", "token-estimate", f"~{estimate} tokens on load (over {TOKEN_WARN}); consider trimming", skill.path)]
    return [Finding("info", "token-estimate", f"~{estimate} tokens on load", skill.path)]


RULES: list[tuple[str, Callable[[SkillFile], list[Finding]]]] = [
    ("yaml-parseable", rule_yaml),
    ("name-present", rule_name_present),
    ("name-format", rule_name_format),
    ("description-present", rule_description_present),
    ("description-length", rule_description_length),
    ("description-trigger", rule_description_trigger),
    ("no-pruned-marker", rule_pruned_marker),
    ("body-size", rule_body_size),
    ("asset-refs", rule_asset_refs),
    ("token-estimate", rule_token_estimate),
]


def lint_skill(skill: SkillFile) -> list[Finding]:
    """Run all rules against one parsed skill."""
    findings: list[Finding] = []
    for _rule_id, rule in RULES:
        findings.extend(rule(skill))
    return findings


def find_duplicate_names(skills: list[SkillFile]) -> list[Finding]:
    """Repo-level check: two SKILL.md files claiming the same name."""
    seen: dict[str, Path] = {}
    findings = []
    for skill in skills:
        name = skill.frontmatter.get("name")
        if not isinstance(name, str):
            continue
        if name in seen:
            findings.append(Finding("error", "duplicate-name", f"name '{name}' also used by {seen[name]}", skill.path))
        else:
            seen[name] = skill.path
    return findings
