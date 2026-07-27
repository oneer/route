#!/usr/bin/env python3
"""Check installed direct dependency versions against a constraints file."""

from __future__ import annotations

import argparse
import importlib
import re
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


PIN = re.compile(r"^([A-Za-z0-9_.-]+)==([^\s;]+)$")


def normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_constraints(path: Path) -> dict[str, tuple[str, str]]:
    constraints: dict[str, tuple[str, str]] = {}
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = PIN.fullmatch(line)
        if not match:
            raise ValueError(f"Unsupported constraint at {path}:{line_number}: {line}")
        package, expected = match.groups()
        key = normalized(package)
        if key in constraints:
            raise ValueError(f"Duplicate constraint for {package}")
        constraints[key] = (package, expected)
    if not constraints:
        raise ValueError(f"No constraints found in {path}")
    return constraints


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--constraints", type=Path, required=True)
    parser.add_argument(
        "--smoke-import",
        action="append",
        default=[],
        metavar="MODULE",
        help="Import a runtime-critical module after checking distribution versions; may be repeated.",
    )
    args = parser.parse_args()

    mismatches: list[str] = []
    for package, expected in read_constraints(args.constraints).values():
        try:
            actual = version(package)
        except PackageNotFoundError:
            mismatches.append(f"{package}: missing, expected {expected}")
            continue
        if actual != expected:
            mismatches.append(f"{package}: installed {actual}, expected {expected}")

    for module in args.smoke_import:
        try:
            importlib.import_module(module)
        except Exception as error:
            mismatches.append(f"{module}: import failed: {type(error).__name__}: {error}")

    if mismatches:
        raise SystemExit("Environment mismatch:\n- " + "\n- ".join(mismatches))
    print(f"environment_check=pass constraints={args.constraints}")


if __name__ == "__main__":
    main()
