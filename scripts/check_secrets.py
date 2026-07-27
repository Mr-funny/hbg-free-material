#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


EXCLUDED_PARTS = {".git", ".venv", "downloads", "build", "dist", "__pycache__"}
PATTERNS = {
    "github_token": re.compile(rb"gh[opsu]_[A-Za-z0-9]{20,}"),
    "openai_key": re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    "aws_access_key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "private_key": re.compile(rb"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY"),
}


def iter_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file() and not EXCLUDED_PARTS.intersection(path.relative_to(root).parts):
            yield path


def load_env_values(path: Path) -> dict[str, bytes]:
    values: dict[str, bytes] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        value = value.strip().strip("\"'")
        if len(value) >= 8 and not value.startswith("your_"):
            values[name.strip()] = value.encode()
    return values


def main() -> int:
    parser = argparse.ArgumentParser(description="Scan repository files without printing secret values.")
    parser.add_argument("--env-file", type=Path, help="Optional local env file whose exact values must not appear.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    root = args.root.resolve()
    exact_values = load_env_values(args.env_file) if args.env_file else {}
    findings: list[tuple[str, Path]] = []

    for path in iter_files(root):
        try:
            data = path.read_bytes()
        except OSError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((name, path))
        for name, value in exact_values.items():
            if value in data:
                findings.append((f"exact:{name}", path))

    if findings:
        for kind, path in findings:
            print(f"potential secret: {kind} in {path.relative_to(root)}")
        return 1

    print("secret scan: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
