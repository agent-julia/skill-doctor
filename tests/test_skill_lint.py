"""Tests for skill-lint rules and CLI."""

from pathlib import Path

from skill_lint.cli import main
from skill_lint.frontmatter import parse_skill
from skill_lint.rules import (
    HERMES,
    SPEC,
    find_duplicate_names,
    lint_skill,
    rule_description_length,
    rule_description_trigger,
    rule_frontmatter_typos,
    rule_name_format,
    rule_pruned_marker,
)

GOOD = """---
name: good-skill
description: Use when checking things. Lints stuff.
---

# Good Skill

Do the thing. Then do the other thing.

1. First step.
2. Second step.
"""


def write_skill(tmp_path: Path, text: str, name: str = "SKILL.md") -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def test_good_skill_is_clean(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD))
    errors = [f for f in lint_skill(skill, HERMES) if f.severity == "error"]
    assert errors == []


def test_missing_name(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("name: good-skill\n", "")))
    assert any(f.rule == "name-present" and f.severity == "error" for f in lint_skill(skill, HERMES))


def test_name_format(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("good-skill", "Bad Skill!")))
    assert any(f.rule == "name-format" for f in rule_name_format(skill, HERMES))


def test_description_too_long(tmp_path):
    long_desc = "x" * 65
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("Use when checking things. Lints stuff.", long_desc)))
    assert any(f.rule == "description-length" and f.severity == "error" for f in rule_description_length(skill, HERMES))


def test_description_trigger_warns(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("Use when checking things.", "Does stuff.")))
    assert any(f.rule == "description-trigger" for f in rule_description_trigger(skill, HERMES))


def test_pruned_marker(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD + "\n[SKILL_PRUNED]\n"))
    assert any(f.rule == "no-pruned-marker" and f.severity == "error" for f in rule_pruned_marker(skill, HERMES))


def test_malformed_yaml(tmp_path):
    skill = parse_skill(write_skill(tmp_path, "---\nname: [unclosed\n---\n# Body\n"))
    assert skill.yaml_error is not None
    assert any(f.rule == "yaml-parseable" for f in lint_skill(skill, HERMES))


def test_duplicate_names(tmp_path):
    a = parse_skill(write_skill(tmp_path, GOOD, name="a/SKILL.md"))
    b_dir = tmp_path / "b"
    b_dir.mkdir()
    b = parse_skill(write_skill(b_dir, GOOD))
    findings = find_duplicate_names([a, b])
    assert len(findings) == 1 and findings[0].rule == "duplicate-name"


def test_asset_refs_missing(tmp_path):
    text = GOOD + "\nSee references/api.md for details.\n"
    skill = parse_skill(write_skill(tmp_path, text))
    assert any(f.rule == "asset-refs" for f in lint_skill(skill, HERMES))


def test_asset_orphan_warns(tmp_path):
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "notes.md").write_text("notes")
    skill = parse_skill(write_skill(tmp_path, GOOD))
    assert any(f.rule == "asset-orphan" and "references/" in f.message for f in lint_skill(skill, HERMES))


def test_asset_orphan_silent_when_referenced(tmp_path):
    refs = tmp_path / "references"
    refs.mkdir()
    (refs / "notes.md").write_text("notes")
    skill = parse_skill(write_skill(tmp_path, GOOD + "\nSee references/notes.md.\n"))
    assert not any(f.rule == "asset-orphan" for f in lint_skill(skill, HERMES))


def test_script_not_executable_warns(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "run.sh").write_text("#!/bin/sh\n")
    skill = parse_skill(write_skill(tmp_path, GOOD + "\nRun scripts/run.sh.\n"))
    assert any(f.rule == "script-executable" for f in lint_skill(skill, HERMES))


def test_spec_profile_allows_long_description(tmp_path):
    long_desc = "x" * 200
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("Use when checking things. Lints stuff.", long_desc)))
    assert rule_description_length(skill, HERMES)
    assert not rule_description_length(skill, SPEC)


def test_spec_profile_skips_trigger_rule(tmp_path):
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("Use when checking things.", "Does stuff.")))
    assert not rule_description_trigger(skill, SPEC)


def test_suggestion_attached_to_fixable_errors(tmp_path):
    long_desc = "x" * 65
    skill = parse_skill(write_skill(tmp_path, GOOD.replace("Use when checking things. Lints stuff.", long_desc)))
    finding = rule_description_length(skill, HERMES)[0]
    assert finding.suggestion


def test_frontmatter_typo_detected(tmp_path):
    text = GOOD.replace("description:", "descrption:")
    skill = parse_skill(write_skill(tmp_path, text))
    assert any(f.rule == "frontmatter-typos" and "'description'" in f.message for f in rule_frontmatter_typos(skill, HERMES))


def test_frontmatter_unknown_key_silent(tmp_path):
    text = GOOD.replace("name: good-skill", "name: good-skill\nsomething_random: 1")
    skill = parse_skill(write_skill(tmp_path, text))
    assert not rule_frontmatter_typos(skill, HERMES)


def test_cli_exit_codes(tmp_path, capsys):
    write_skill(tmp_path, GOOD)
    assert main(["lint", str(tmp_path)]) == 0
    write_skill(tmp_path, GOOD.replace("name: good-skill\n", ""), name="bad/SKILL.md")
    assert main(["lint", str(tmp_path)]) == 1
