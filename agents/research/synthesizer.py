"""Synthesizer: turns raw findings into a structured market brief."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agents.base import Agent
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace


class MarketBrief(BaseModel):
    key_trends: list[str] = Field(
        description="Notable market/industry trends relevant to the topic, each as one concise statement."
    )
    competitor_notes: list[str] = Field(
        description="Observations about competitors or alternative solutions active in this space."
    )
    audience_pain_points: list[str] = Field(
        description="Specific problems/frustrations the target audience faces, grounded in the research."
    )
    opportunities: list[str] = Field(
        description=(
            f"Concrete opportunities for {SYNAPSES_PROFILE.company_name} implied by the findings, "
            "tied to its ICP and services where relevant."
        )
    )

    def to_markdown(self) -> str:
        def bullets(items: list[str]) -> str:
            return "\n".join(f"- {item}" for item in items) if items else "- (none identified)"

        return (
            "**Key Trends**\n" + bullets(self.key_trends) + "\n\n"
            "**Competitor Notes**\n" + bullets(self.competitor_notes) + "\n\n"
            "**Audience Pain Points**\n" + bullets(self.audience_pain_points) + "\n\n"
            "**Opportunities**\n" + bullets(self.opportunities)
        )


SYSTEM_PROMPT = f"""You are the Synthesizer agent for {SYNAPSES_PROFILE.company_name}.

You receive raw research notes (with sources) from the Researcher agent and
turn them into a structured market brief. You do not perform new research —
only work from what's in the notes given to you, and note gaps rather than
inventing detail.

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

Populate exactly these four fields, each a list of concise, specific
statements (not vague generalities):
- key_trends: notable market/industry trends relevant to the topic
- competitor_notes: what competitors or alternative solutions are doing
- audience_pain_points: concrete problems/frustrations the target audience faces
- opportunities: concrete opportunities for {SYNAPSES_PROFILE.company_name},
  tied to its ICP and services where relevant

Every statement should be decision-useful to someone deciding what to build
or say next, not a restatement of the raw notes.
"""


class Synthesizer(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="synthesizer",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def synthesize(self, raw_findings: str, trace: Trace | None = None) -> MarketBrief:
        return self.call_structured(raw_findings, MarketBrief, trace=trace)
