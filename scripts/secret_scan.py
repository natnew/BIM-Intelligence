"""Run Gitleaks against the working tree, staged changes or repository Git history."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--staged",
        action="store_true",
        help="scan the Git index diff; used by the pre-commit hook",
    )
    mode.add_argument(
        "--history",
        action="store_true",
        help="scan repository history (the default)",
    )
    mode.add_argument(
        "--working-tree",
        action="store_true",
        help="scan current repository files, including untracked non-ignored files",
    )
    args = parser.parse_args(argv)
    executable = shutil.which("gitleaks")
    if executable is None:
        print(
            "Gitleaks is required. Install the approved Gitleaks CLI and retry.",
            file=sys.stderr,
        )
        return 2

    command = [
        executable,
        "git",
        "--redact",
        "--no-banner",
        "--config",
        str(REPOSITORY_ROOT / ".gitleaks.toml"),
    ]
    if args.staged:
        command.extend(["--staged", "--pre-commit"])
        print("Scanning staged changes with Gitleaks (redacted output).")
    elif args.working_tree:
        command = [
            executable,
            "dir",
            "--redact",
            "--no-banner",
            "--config",
            str(REPOSITORY_ROOT / ".gitleaks.toml"),
            str(REPOSITORY_ROOT),
        ]
        print("Scanning repository working tree with Gitleaks (redacted output).")
    else:
        print("Scanning repository Git history with Gitleaks (redacted output).")
    try:
        result = subprocess.run(command, cwd=REPOSITORY_ROOT, check=False)
    except OSError:
        print("Gitleaks could not be started.", file=sys.stderr)
        return 2
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
