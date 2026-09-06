#!/usr/bin/env python
"""Manual smoke test for the Lead Gen team.

Runs Prospector -> Qualifier in sequence on a fixed query and prints the
resulting scored prospect list.

Usage:
    python test_leadgen_team.py
"""

import sys

from dotenv import load_dotenv

from agents.leadgen.prospector import Prospector
from agents.leadgen.qualifier import Qualifier
from orchestration.trace import Trace

QUERY = "find prospects in the legal services sector, Gauteng"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()
    trace = Trace()

    prospector = Prospector()
    qualifier = Qualifier()

    print(f"Query: {QUERY}\n")

    print("Running Prospector (web search)...")
    candidates = prospector.call(QUERY, trace)
    print("\n--- Raw candidates ---")
    print(candidates)

    print("\nRunning Qualifier (structured ICP scoring)...")
    qualified = qualifier.qualify(candidates, trace)

    print("\n--- Qualified Prospects (JSON) ---")
    print(qualified.model_dump_json(indent=2))

    print("\n--- Qualified Prospects (markdown) ---")
    print(qualified.to_markdown())


if __name__ == "__main__":
    main()
