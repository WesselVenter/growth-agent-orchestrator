#!/usr/bin/env python
"""Manual smoke test for the Research team.

Runs Researcher -> Synthesizer in sequence on a fixed topic and prints the
resulting structured market brief.

Usage:
    python test_research_team.py
"""

import sys

from dotenv import load_dotenv

from agents.research.researcher import Researcher
from agents.research.synthesizer import Synthesizer
from orchestration.trace import Trace

TOPIC = "POPIA compliance for SA legal firms"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()
    trace = Trace()

    researcher = Researcher()
    synthesizer = Synthesizer()

    print(f"Topic: {TOPIC}\n")

    print("Running Researcher (web search)...")
    findings = researcher.call(TOPIC, trace)
    print("\n--- Raw findings ---")
    print(findings)

    print("\nRunning Synthesizer (structured brief)...")
    brief = synthesizer.synthesize(findings, trace)

    print("\n--- Market Brief ---")
    print(brief.model_dump_json(indent=2))

    print("\n--- Market Brief (markdown) ---")
    print(brief.to_markdown())


if __name__ == "__main__":
    main()
