"""Strategist: turns a market brief into a small set of content angles."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base import Agent
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace


class ContentAngle(BaseModel):
    headline: str = Field(description="A specific, concrete headline/hook for this angle.")
    core_idea: str = Field(description="The core idea in 1-2 sentences.")
    why_it_matters: str = Field(
        description=f"Why this would resonate specifically with {SYNAPSES_PROFILE.company_name}'s ICP."
    )
    suggested_format: str = Field(
        description="Suggested format, e.g. LinkedIn post, short article, case study, email."
    )


class ContentAngleList(BaseModel):
    angles: list[ContentAngle] = Field(
        min_length=2,
        max_length=3,
        description="2-3 concrete, specific content angles derived from the brief.",
    )


SYSTEM_PROMPT = f"""You are the Content Strategist agent for {SYNAPSES_PROFILE.company_name}.

You receive a market brief and produce 2-3 content angles that would
resonate with {SYNAPSES_PROFILE.company_name}'s ICP.

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

For each angle, provide:
- headline: a specific, concrete headline/hook (not generic AI marketing language)
- core_idea: the core idea in 1-2 sentences
- why_it_matters: why this would resonate specifically with the ICP, grounded
  in something from the brief (a trend, pain point, or opportunity)
- suggested_format: LinkedIn post, short article, case study, email, etc.

Favor concrete, specific angles tied directly to findings in the brief over
generic advice. Each angle should be usable as-is by a Writer agent without
further clarification.
"""


class Strategist(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="strategist",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def generate_angles(self, market_brief: str, trace: Trace | None = None) -> ContentAngleList:
        return self.call_structured(market_brief, ContentAngleList, trace=trace)
