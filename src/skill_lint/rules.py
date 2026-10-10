"""Lint rules for SKILL.md files. Each rule is one small function."""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .frontmatter import SkillFile

NAME_MAX = 64
DESC_TRIGGER_CHARS = 57
BODY_MIN_LINES = 5
BODY_MAX_LINES = 250
TOKEN_WARN = 4000

SEVERITY_ORDER = {"error": 0, "warn": 1, "info": 2}

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9\-_]*$")
# path segment: word chars/hyphens with at most one extension dot, so a
# trailing sentence period is not swallowed into the match
SEG = r"[\w\-]+(?:\.[\w\-]+)?"
ASSET_RE = re.compile(r"\b(references|templates|scripts)/" + SEG + r"(?:/" + SEG + r")*")
PRUNED_MARK = "[SKILL_PRUNED]"

ASSET_DIRS = ("references", "templates", "scripts")

# frontmatter keys a reader may legitimately see; used only to catch typos
KNOWN_KEYS = {
    "name", "description", "license", "allowed-tools", "compatibility",
    "metadata", "version", "author", "platforms", "tags", "when_to_use",
}


@dataclass(frozen=True)
class Profile:
    """Lint flavor: which limits apply."""

    desc_max: int
    compatibility_max: int
    require_trigger: bool


HERMES = Profile(desc_max=64, compatibility_max=0, require_trigger=True)
SPEC = Profile(desc_max=1024, compatibility_max=500, require_trigger=False)
PROFILES = {"hermes": HERMES, "spec": SPEC}


@dataclass
class Finding:
    """One lint finding, optionally with a fix suggestion."""

    severity: str
    rule: str
    message: str
    path: Path
    suggestion: str | None = None

    def format(self) -> str:
        line = f"{self.severity.upper():5} {self.rule:22} {self.path}: {self.message}"
        if self.suggestion:
            line += f"\n           fix: {self.suggestion}"
        return line


def rule_yaml(skill: SkillFile, profile: Profile) -> list[Finding]:
    if skill.yaml_error:
        return [Finding("error", "yaml-parseable", skill.yaml_error, skill.path)]
    return []


def rule_frontmatter_typos(skill: SkillFile, profile: Profile) -> list[Finding]:
    findings = []
    for key in skill.frontmatter:
        if key not in KNOWN_KEYS:
            near = difflib.get_close_matches(key, KNOWN_KEYS, n=1, cutoff=0.85)
            if near:
                findings.append(Finding("warn", "frontmatter-typos", f"unknown key '{key}'; did you mean '{near[0]}'?", skill.path))
    return findings


def rule_name_present(skill: SkillFile, profile: Profile) -> list[Finding]:
    if "name" not in skill.frontmatter:
        return [Finding("error", "name-present", "frontmatter missing 'name'", skill.path)]
    return []


def rule_name_format(skill: SkillFile, profile: Profile) -> list[Finding]:
    name = skill.frontmatter.get("name")
    if not isinstance(name, str) or not name:
        return [Finding("error", "name-format", "'name' must be a non-empty string", skill.path)]
    findings = []
    if len(name) > NAME_MAX:
        findings.append(Finding(
            "error", "name-format", f"name is {len(name)} chars (max {NAME_MAX})", skill.path,
            suggestion=f"shorten to {NAME_MAX} chars or less"))
    if not NAME_RE.match(name):
        findings.append(Finding(
            "error", "name-format", f"name '{name}' must be lowercase, digits, hyphens, underscores", skill.path,
            suggestion="use lowercase-hyphen form, e.g. 'my-skill'"))
    return findings


def rule_description_present(skill: SkillFile, profile: Profile) -> list[Finding]:
    if "description" not in skill.frontmatter:
        return [Finding("error", "description-present", "frontmatter missing 'description'", skill.path)]
    return []


def rule_description_length(skill: SkillFile, profile: Profile) -> list[Finding]:
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str) or not desc:
        return [Finding("error", "description-length", "'description' must be a non-empty string", skill.path)]
    if len(desc) > profile.desc_max:
        return [Finding(
            "error", "description-length", f"description is {len(desc)} chars (max {profile.desc_max} in {profile_name(profile)} profile)", skill.path,
            suggestion=f"trim to {profile.desc_max} chars; lead with the trigger phrase")]
    return []


def rule_description_trigger(skill: SkillFile, profile: Profile) -> list[Finding]:
    if not profile.require_trigger:
        return []
    desc = skill.frontmatter.get("description")
    if not isinstance(desc, str):
        return []
    if not desc[:DESC_TRIGGER_CHARS].startswith("Use when"):
        return [Finding(
            "warn", "description-trigger", f"first {DESC_TRIGGER_CHARS} chars should be a self-contained trigger starting with 'Use when'", skill.path,
            suggestion=f"rewrite as 'Use when <situation>. <what it does>'")]
    return []


def rule_compatibility_length(skill: SkillFile, profile: Profile) -> list[Finding]:
    compat = skill.frontmatter.get("compatibility")
    if isinstance(compat, str) and profile.compatibility_max and len(compat) > profile.compatibility_max:
        return [Finding(
            "error", "compatibility-length", f"compatibility is {len(compat)} chars (max {profile.compatibility_max})", skill.path,
            suggestion=f"trim to {profile.compatibility_max} chars")]
    return []


def rule_pruned_marker(skill: SkillFile, profile: Profile) -> list[Finding]:
    if PRUNED_MARK in skill.raw:
        return [Finding(
            "error", "no-pruned-marker", f"contains '{PRUNED_MARK}'; skill lost content to compaction — reload it", skill.path,
            suggestion="reload the skill with skill_view(name='...')")]
    return []


def rule_body_size(skill: SkillFile, profile: Profile) -> list[Finding]:
    lines = skill.body.strip().splitlines()
    if len(lines) < BODY_MIN_LINES:
        return [Finding("warn", "body-size", f"body is {len(lines)} lines (min {BODY_MIN_LINES}); too thin to be useful", skill.path)]
    if len(lines) > BODY_MAX_LINES:
        return [Finding("warn", "body-size", f"body is {len(lines)} lines (max {BODY_MAX_LINES}); likely over-engineered and token-hungry", skill.path)]
    return []


def rule_asset_refs(skill: SkillFile, profile: Profile) -> list[Finding]:
    findings = []
    checked: set[str] = set()
    for match in ASSET_RE.finditer(skill.body):
        rel = match.group(0)
        if rel in checked:
            continue
        checked.add(rel)
        target = skill.path.parent / rel
        if not target.exists():
            findings.append(Finding("warn", "asset-refs", f"referenced file '{rel}' does not exist", skill.path))
        elif rel.startswith("scripts/") and not target.stat().st_mode & 0o111:
            findings.append(Finding("warn", "script-executable", f"'{rel}' is referenced but not executable", skill.path))
    return findings


def rule_asset_orphan(skill: SkillFile, profile: Profile) -> list[Finding]:
    findings = []
    mentioned = {m.group(0) for m in ASSET_RE.finditer(skill.body)}
    for dirname in ASSET_DIRS:
        dirpath = skill.path.parent / dirname
        if not dirpath.is_dir():
            continue
        files = [p for p in dirpath.rglob("*") if p.is_file()]
        if files and not any(str(p.relative_to(skill.path.parent)) in mentioned for p in files):
            findings.append(Finding("warn", "asset-orphan", f"directory '{dirname}/' has {len(files)} file(s) but none are referenced in the body", skill.path))
    return findings


def rule_token_estimate(skill: SkillFile, profile: Profile) -> list[Finding]:
    estimate = len(skill.raw) // 4
    if estimate > TOKEN_WARN:
        return [Finding("warn", "token-estimate", f"~{estimate} tokens on load (over {TOKEN_WARN}); consider trimming", skill.path)]
    return [Finding("info", "token-estimate", f"~{estimate} tokens on load", skill.path)]


RULES: list[tuple[str, Callable[[SkillFile, Profile], list[Finding]]]] = [
    ("yaml-parseable", rule_yaml),
    ("frontmatter-typos", rule_frontmatter_typos),
    ("name-present", rule_name_present),
    ("name-format", rule_name_format),
    ("description-present", rule_description_present),
    ("description-length", rule_description_length),
    ("description-trigger", rule_description_trigger),
    ("compatibility-length", rule_compatibility_length),
    ("no-pruned-marker", rule_pruned_marker),
    ("body-size", rule_body_size),
    ("asset-refs", rule_asset_refs),
    ("asset-orphan", rule_asset_orphan),
    ("token-estimate", rule_token_estimate),
]


def profile_name(profile: Profile) -> str:
    for name, candidate in PROFILES.items():
        if candidate == profile:
            return name
    return "custom"


def lint_skill(skill: SkillFile, profile: Profile) -> list[Finding]:
    """Run all rules against one parsed skill."""
    findings: list[Finding] = []
    for _rule_id, rule in RULES:
        findings.extend(rule(skill, profile))
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
