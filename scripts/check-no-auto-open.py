#!/usr/bin/env python3
"""Reject development server settings that may open a browser."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


SKIP_DIRS = {".git", "fixtures", "node_modules", "tests"}
BROWSER_ASSIGNMENT = re.compile(r"\bBROWSER\s*=\s*([^\s;&|]+)", re.IGNORECASE)
OPEN_FLAG = re.compile(r"(?:^|\s)--open(?:[=\s]|$)")
DOCUSAURUS = re.compile(r"\bdocusaurus\s+(?:start|serve)\b")
LIVE_SERVER = re.compile(r"(?:^|[\s/])live-server(?:\s|$)")
CONFIG_OPEN = re.compile(r"\bopen\s*:\s*true\b")


def source_files(root: Path, name: str) -> list[Path]:
    return [
        path
        for path in root.rglob(name)
        if not any(part in SKIP_DIRS for part in path.relative_to(root).parts)
    ]


def command_errors(command: str) -> list[str]:
    errors: list[str] = []
    if OPEN_FLAG.search(command):
        errors.append("uses --open")
    if DOCUSAURUS.search(command) and "--no-open" not in command:
        errors.append("runs Docusaurus without --no-open")
    if LIVE_SERVER.search(command) and "--no-browser" not in command:
        errors.append("runs live-server without --no-browser")
    for match in BROWSER_ASSIGNMENT.finditer(command):
        value = match.group(1).strip("'\"").lower()
        if value != "none":
            errors.append(f"sets BROWSER={match.group(1)} instead of BROWSER=none")
    return errors


def check_package_json(root: Path) -> list[str]:
    errors: list[str] = []
    for path in source_files(root, "package.json"):
        try:
            scripts = json.loads(path.read_text()).get("scripts", {})
        except (json.JSONDecodeError, OSError) as exc:
            errors.append(f"{path.relative_to(root)}: cannot read package scripts: {exc}")
            continue
        for name, command in scripts.items():
            if not isinstance(command, str):
                continue
            for detail in command_errors(command):
                errors.append(f"{path.relative_to(root)} script {name!r}: {detail}")
    return errors


def check_justfiles(root: Path) -> list[str]:
    errors: list[str] = []
    for name in ("justfile", "Justfile"):
        for path in source_files(root, name):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                command = line.strip()
                if not command or command.startswith("#"):
                    continue
                for detail in command_errors(command):
                    errors.append(
                        f"{path.relative_to(root)}:{line_number}: {detail}"
                    )
    return errors


def check_configs(root: Path) -> list[str]:
    errors: list[str] = []
    patterns = ("vite.config.*", "astro.config.*")
    for pattern in patterns:
        for path in source_files(root, pattern):
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                if CONFIG_OPEN.search(line):
                    errors.append(
                        f"{path.relative_to(root)}:{line_number}: sets open: true"
                    )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    errors = check_package_json(root) + check_justfiles(root) + check_configs(root)
    if errors:
        print("Development server browser auto-open settings found:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("No development server browser auto-open settings found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
