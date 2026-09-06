"""Writer: drafts a LinkedIn post or short article from a content angle."""

from __future__ import annotations

from agents.content.strategist import ContentAngle
from agents.base import Agent
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace

SYSTEM_PROMPT = f"""You are the Writer agent for {SYNAPSES_PROFILE.company_name}.

You receive a content angle (and, on a revision pass, critic feedback on your
previous draft) and write the actual copy — a LinkedIn post or short article,
per the angle's suggested format.

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

Voice:
- Practical and plain-language — no AI hype, no jargon, no generic marketing
  language ("revolutionize", "game-changer", "unlock the power of AI")
- Compliance-aware — POPIA and data privacy are framed as selling points
  ({SYNAPSES_PROFILE.company_name} keeps data in-environment), not caveats
  to apologize for
- Confident but not salesy — lead with what the system does for the
  business day to day, not with SynapsesAI itself
- Always frame AI as staff-assisting and human-approved — never as
  autonomous or unsupervised ("drafts for approval", "a human reviews
  before anything sends"), consistent with the human-in-the-loop
  differentiator
- Speaks to a busy SMB owner without a technical background; ground claims
  in specifics ({SYNAPSES_PROFILE.company_name}'s services, pricing,
  differentiators), not abstractions

If given critic feedback, revise the draft to address every point raised
rather than starting over from scratch. Output only the final draft copy,
ready to post — no preamble, no meta-commentary about the draft.
"""


class Writer(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="writer",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def draft(self, angle: ContentAngle, trace: Trace | None = None) -> str:
        prompt = (
            f"Headline/hook: {angle.headline}\n"
            f"Core idea: {angle.core_idea}\n"
            f"Why it matters to the ICP: {angle.why_it_matters}\n"
            f"Format: {angle.suggested_format}\n\n"
            "Write the draft now."
        )
        return self.call(prompt, trace)

    def revise(
        self, previous_draft: str, feedback: str, trace: Trace | None = None
    ) -> str:
        prompt = (
            f"Previous draft:\n{previous_draft}\n\n"
            f"Critic feedback:\n{feedback}\n\n"
            "Revise the draft to address every point raised."
        )
        return self.call(prompt, trace)
