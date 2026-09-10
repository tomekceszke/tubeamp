#!/usr/bin/env python3
"""Fail if a built distribution carries anything private.

The repo root holds files that are deliberately never published — a personal
`local.toml`, exported cookies, saved screenshots, agent state. Hatchling
excludes VCS-ignored paths by default and `pyproject.toml` pins an allow-list
on top of that, but neither is worth trusting silently: this runs on every tag
and is the last thing standing between a private playlist URL and PyPI.

It also checks the wheel for the two files that ship as data rather than code,
because an install missing them starts unstyled and untyped and no test fails.
"""

from __future__ import annotations

import fnmatch
import sys
import tarfile
import zipfile
from pathlib import Path

FORBIDDEN_NAMES = ("local.toml", "cookies.txt", "*.svg", ".env", "*.log")
FORBIDDEN_DIRS = frozenset({".venv", ".claude", ".git", "viz_cache", "__pycache__"})

REQUIRED_IN_WHEEL = ("tubeamp/styles/tubeamp.tcss", "tubeamp/py.typed")


def members(archive: Path) -> list[str]:
    if archive.suffix == ".whl":
        with zipfile.ZipFile(archive) as zf:
            return zf.namelist()
    with tarfile.open(archive) as tf:
        return tf.getnames()


def offenders(names: list[str]) -> list[str]:
    found = []
    for name in names:
        path = Path(name)
        in_forbidden_dir = bool(FORBIDDEN_DIRS.intersection(path.parts))
        matches_name = any(fnmatch.fnmatch(path.name, p) for p in FORBIDDEN_NAMES)
        if in_forbidden_dir or matches_name:
            found.append(name)
    return found


def main() -> int:
    dist = Path("dist")
    archives = sorted(dist.glob("*.tar.gz")) + sorted(dist.glob("*.whl"))
    if not archives:
        print("no archives in dist/ — nothing to audit", file=sys.stderr)
        return 1

    failed = False
    for archive in archives:
        names = members(archive)
        leaked = offenders(names)
        if leaked:
            failed = True
            print(f"FAIL {archive.name}: private files in the archive", file=sys.stderr)
            for name in leaked:
                print(f"       {name}", file=sys.stderr)
        else:
            print(f"ok   {archive.name}: {len(names)} entries, nothing private")

        if archive.suffix == ".whl":
            missing = [want for want in REQUIRED_IN_WHEEL if want not in names]
            if missing:
                failed = True
                print(f"FAIL {archive.name}: missing {', '.join(missing)}", file=sys.stderr)
            else:
                print(f"ok   {archive.name}: stylesheet and py.typed present")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
