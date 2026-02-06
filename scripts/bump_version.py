"""Bump the project version in pyproject.toml.

Reads BUMP from the environment (major, minor, patch), updates the
version field, and prints the new version.
"""

from __future__ import annotations

import os
import re
import sys


def main() -> int:
    """Run the version bump."""
    path = "pyproject.toml"
    text = open(path, "r", encoding="utf-8").read()
    match = re.search(r'(?m)^version = "(\d+)\.(\d+)\.(\d+)"\s*$', text)
    if not match:
        print("version not found in pyproject.toml", file=sys.stderr)
        return 1

    major, minor, patch = (int(value) for value in match.groups())
    bump = os.environ.get("BUMP")
    if bump == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump == "minor":
        minor += 1
        patch = 0
    elif bump == "patch":
        patch += 1
    else:
        print(f"unknown bump type: {bump}", file=sys.stderr)
        return 1

    new_line = f'version = "{major}.{minor}.{patch}"'
    text = re.sub(
        r'(?m)^version = "\d+\.\d+\.\d+"\s*$',
        new_line,
        text,
        count=1,
    )
    open(path, "w", encoding="utf-8").write(text)
    print(f"Bumped version to {major}.{minor}.{patch}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
