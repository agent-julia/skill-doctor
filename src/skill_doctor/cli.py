"""CLI entrypoint for skill-doctor."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .frontmatter import parse_skill
from .rules import SEVERITY_ORDER, Finding, find_duplicate_names, lint_skill


def iter_skill_files(target: Path) -> list[Path]:
    """Collect SKILL.md files from a file or directory target."""
    if target.is_file():
        return [target] if target.name == "SKILL.md" else []
    return sorted(target.rglob("SKILL.md"))


def lint_targets(targets: list[Path]) -> list[Finding]:
    """Lint all SKILL.md files under the given targets."""
    files: list[Path] = []
    for target in targets:
        files.extend(iter_skill_files(target))
    if not files:
        print("no SKILL.md files found", file=sys.stderr)
        return []

    skills = [parse_skill(path) for path in files]
    findings: list[Finding] = []
    for skill in skills:
        findings.extend(lint_skill(skill))
    findings.extend(find_duplicate_names(skills))
    return findings


def summarize(findings: list[Finding]) -> str:
    errors = sum(1 for f in findings if f.severity == "error")
    warns = sum(1 for f in findings if f.severity == "warn")
    infos = sum(1 for f in findings if f.severity == "info")
    return f"{errors} error(s), {warns} warning(s), {infos} info"


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse CLI."""
    parser = argparse.ArgumentParser(prog="skill-doctor", description="Lint and health-check agent SKILL.md files")
    sub = parser.add_subparsers(dest="command", required=True)
    lint = sub.add_parser("lint", help="lint SKILL.md files")
    lint.add_argument("targets", nargs="+", type=Path, help="SKILL.md file or directory (scanned recursively)")
    lint.add_argument("--json", action="store_true", help="machine-readable JSON output")
    return parser


def cmd_lint(args: argparse.Namespace) -> int:
    """Run the lint command."""
    findings = lint_targets(args.targets)
    findings.sort(key=lambda f: (SEVERITY_ORDER[f.severity], str(f.path), f.rule))
    if args.json:
        print(json.dumps([f.__dict__ | {"path": str(f.path)} for f in findings], indent=2))
    else:
        for finding in findings:
            print(finding.format())
        print(f"\n{summarize(findings)}")
    return 1 if any(f.severity == "error" for f in findings) else 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    if args.command == "lint":
        return cmd_lint(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
