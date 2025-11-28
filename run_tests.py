#!/usr/bin/env python3
"""Helper script to run pytest with coverage over rgenerator."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=backend/rgenerator",
        "--cov-report=term-missing",
    ]
    process = subprocess.run(cmd, cwd=repo_root)
    return process.returncode


if __name__ == "__main__":
    raise SystemExit(main())
