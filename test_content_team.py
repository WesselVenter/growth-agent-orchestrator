#!/usr/bin/env python
"""Manual smoke test for the Content team.

Runs Strategist -> Writer -> Critic (with the revision loop) end-to-end on
one content angle derived from a sample market brief, and prints every
revision cycle plus the final draft.

Usage:
    python test_content_team.py
"""

import sys

from dotenv import load_dotenv

from agents.content.critic import MAX_REVISIONS, SCORE_THRESHOLD, Critic
from agents.content.strategist import Strategist
from agents.content.writer import Writer
from orchestration.trace import Trace

# A short sample market brief, standing in for Synthesizer output.
SAMPLE_MARKET_BRIEF = """
**Key Trends**
- POPIA enforcement is escalating: the Information Regulator audited 17 law
  firms in 2024 alone, with more enforcement expected in 2025.
- Cloud-based AI tools are a specific POPIA risk for firms handling client
  data, since uploads can trigger unlawful cross-border data transfers.
- AI adoption is accelerating fastest among medium-sized firms (30-300
  staff), who see it as a way to close the gap with larger, better-resourced
  competitors.

**Audience Pain Points**
- Staff lose hours per week searching for information buried in old files,
  emails, and case notes.
- Firms want the efficiency of AI but are wary of sending client data to
  public AI tools given POPIA exposure.
- Institutional knowledge walks out the door when senior staff leave.

**Opportunities**
- Position private, in-environment AI as the safe alternative to public
  cloud AI tools for firms handling confidential client data.
- Use the POPIA compliance angle as a business-protection argument, not
  just an efficiency pitch.
"""


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    load_dotenv()
    trace = Trace()

    strategist = Strategist()
    writer = Writer()
    critic = Critic()

    print("Running Strategist (content angles)...")
    angle_list = strategist.generate_angles(SAMPLE_MARKET_BRIEF, trace)
    trace.log_handoff("strategist", "test_script", f"{len(angle_list.angles)} angles generated")

    print(f"\n--- {len(angle_list.angles)} Content Angles ---")
    for i, a in enumerate(angle_list.angles, start=1):
        print(f"\n{i}. {a.headline} ({a.suggested_format})")
        print(f"   Core idea: {a.core_idea}")
        print(f"   Why it matters: {a.why_it_matters}")

    angle = angle_list.angles[0]
    print(f"\nSelected angle for drafting: {angle.headline}\n")

    print("Running Writer (initial draft)...")
    draft = writer.draft(angle, trace)

    revision_count = 0
    while True:
        print(f"\nRunning Critic (review pass {revision_count + 1})...")
        critique = critic.grade(draft, trace)
        trace.log_handoff(
            "critic", "test_script",
            f"pass {revision_count + 1}: overall_score={critique.overall_score}",
        )

        print(f"  hook_strength={critique.hook_strength} clarity={critique.clarity} "
              f"brand_fit={critique.brand_fit} specificity={critique.specificity} "
              f"overall={critique.overall_score}")
        print(f"  feedback: {critique.feedback}")

        if critique.overall_score >= SCORE_THRESHOLD or revision_count >= MAX_REVISIONS:
            print(f"\nFinal score {critique.overall_score}/10 after {revision_count} revision(s).")
            break

        revision_count += 1
        print(f"\nScore below {SCORE_THRESHOLD} — running Writer revision {revision_count}...")
        draft = writer.revise(draft, critique.feedback, trace)

    print("\n--- Final Draft ---")
    print(draft)

    print(f"\n--- Trace: {len(trace.calls)} calls, {len(trace.handoffs)} handoffs ---")
    for h in trace.handoffs:
        print(f"  {h.from_agent} -> {h.to_agent}: {h.reason}")


if __name__ == "__main__":
    main()
