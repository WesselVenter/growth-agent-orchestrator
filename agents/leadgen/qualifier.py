"""Qualifier: scores each prospect 0-100 against the ICP with structured reasoning."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.base import Agent
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace


class QualifiedProspect(BaseModel):
    company_name: str
    fit_score: int = Field(ge=0, le=100, description="Overall ICP fit score, 0-100.")
    justification: str = Field(
        description=(
            "Short justification (2-4 sentences) explaining the score: which ICP "
            "criteria were matched, which were missed or uncertain, and why."
        )
    )
    recommended: Literal["yes", "no", "maybe"] = Field(
        description="Overall recommendation given the score and confidence in the underlying data."
    )


class QualifiedProspectList(BaseModel):
    qualified_prospects: list[QualifiedProspect] = Field(
        description="One entry per prospect received, sorted by fit_score descending."
    )

    def to_markdown(self) -> str:
        ranked = sorted(self.qualified_prospects, key=lambda p: p.fit_score, reverse=True)
        lines = ["| Rank | Company | Fit Score | Recommended |", "|---|---|---|---|"]
        for i, p in enumerate(ranked, start=1):
            lines.append(f"| {i} | {p.company_name} | {p.fit_score}/100 | {p.recommended} |")

        details = "\n\n".join(
            f"### {p.company_name} — {p.fit_score}/100 ({p.recommended})\n{p.justification}"
            for p in ranked
        )
        return "\n".join(lines) + "\n\n" + details


ICP = SYNAPSES_PROFILE.icp

SYSTEM_PROMPT = f"""You are the Qualifier agent for {SYNAPSES_PROFILE.company_name}.

You receive a list of prospect companies (with whatever size/source signals
were found) from the Prospector agent and score each one against the ICP
below. You do not perform new research — reason only from what's given, and
treat missing/uncertain data as a reason to lower confidence, not to guess.

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

ICP to score against:
- Ownership: {ICP.ownership}
- Staff: {ICP.staff_range}
- Sites: {ICP.site_range}
- Operational profile: {ICP.operational_profile}
- Decision maker: {ICP.decision_maker_profile}
- Disqualifiers: {ICP.disqualifiers}

Scoring approach — use structured reasoning, not a gut number:
1. Check each ICP criterion (ownership, staff range, site count, document-heavy
   operations, accessible decision-maker) individually against the evidence.
2. Check for any disqualifiers; if one clearly applies, the score should be low
   (below 20) regardless of other criteria.
3. Weigh confidence: a criterion that's confirmed counts more than one that's
   inferred or unknown. Uncertainty should pull the score toward the middle,
   not toward either extreme.
4. Combine into a single 0-100 fit score, where 0 = clearly disqualified,
   50 = plausible but too uncertain to prioritize, 100 = ideal, confirmed fit.

For every prospect, write a short (2-4 sentence) justification naming the
specific criteria that drove the score up or down. Be honest about weak or
uncertain fits rather than inflating scores.
"""


class Qualifier(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="qualifier",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def qualify(self, prospects_text: str, trace: Trace | None = None) -> QualifiedProspectList:
        return self.call_structured(prospects_text, QualifiedProspectList, trace=trace)
