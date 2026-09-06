#!/usr/bin/env python
"""CLI entrypoint.

Usage:
    python cli.py "find 10 leads in the legal sector, Gauteng"
"""

import sys

from dotenv import load_dotenv

from orchestration.run import run_and_save


def main() -> None:
    # Windows consoles default to a legacy codepage that can't encode the
    # emoji/unicode agents sometimes produce; force UTF-8 output.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()

    if len(sys.argv) < 2:
        print('Usage: python cli.py "<goal>"')
        sys.exit(1)

    goal = " ".join(sys.argv[1:])
    print(f"Goal: {goal}\n")
    print("Running...\n")

    run_dir = run_and_save(goal)

    report_path = run_dir / "report.md"
    print(report_path.read_text(encoding="utf-8"))
    print(f"\nSaved to {run_dir}")


if __name__ == "__main__":
    main()
