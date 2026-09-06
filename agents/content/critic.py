"""Critic: grades drafts, sends back for revision if below threshold."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base import Agent
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace

SCORE_THRESHOLD = 7
MAX_REVISIONS = 2


class Critique(BaseModel):
    hook_strength: int = Field(ge=0, le=10, description="Does the opening line earn a read?")
    clarity: int = Field(ge=0, le=10, description="Clarity for a non-technical SMB owner.")
    brand_fit: int = Field(
        ge=0, le=10, description="Alignment with brand voice, compliance framing, and human-in-the-loop positioning."
    )
    specificity: int = Field(
        ge=0, le=10, description="Concrete claims/specifics vs. generic AI marketing language."
    )
    overall_score: int = Field(
        ge=0, le=10, description="Overall score: 0 = unusable, 10 = ready to ship as-is."
    )
    feedback: str = Field(
        description="Specific, actionable feedback the Writer agent can act on in one revision pass."
    )


SYSTEM_PROMPT = f"""You are the Critic agent for {SYNAPSES_PROFILE.company_name}.

You receive a content draft and grade it 0-10 on each of:
- hook_strength: does the opening line earn a read, or is it generic/throat-clearing?
- clarity: is it clear and plain-language for a non-technical SMB owner?
- brand_fit: does it match the brand voice — practical, compliance-aware
  (POPIA framed as a selling point), confident but not salesy, and does it
  frame AI as human-approved rather than autonomous?
- specificity: are claims concrete and grounded in specifics (services,
  pricing, differentiators), or vague/hype-y?

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

Then give an overall_score (0-10) — not necessarily an average of the four,
but your holistic judgment of whether this is ready to publish.

A score of {SCORE_THRESHOLD} or above means the draft is ready to ship as-is.
Below that, feedback must be specific and actionable enough for the Writer
to fix in one revision pass — name the exact line or claim that needs to
change and what to change it to, don't just restate the sub-scores.
"""


class Critic(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="critic",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def grade(self, draft: str, trace: Trace | None = None) -> Critique:
        return self.call_structured(draft, Critique, trace=trace)
