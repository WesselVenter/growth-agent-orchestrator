"""Outreach Drafter: drafts personalized outreach from a qualified lead + content/positioning."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from agents.base import Agent
from agents.leadgen.qualifier import QualifiedProspect, QualifiedProspectList
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace

DRAFT_NOTICE = "**DRAFT — for human review before sending. Do not send unedited.**"


class OutreachDraft(BaseModel):
    channel: Literal["email", "linkedin_dm"] = Field(
        description="Best-fit outreach channel for this lead, given what's known about it."
    )
    subject: str = Field(
        default="",
        description="Email subject line. Leave as an empty string if channel is linkedin_dm.",
    )
    message: str = Field(description="The outreach message body.")


SYSTEM_PROMPT = f"""You are the Outreach Drafter agent for {SYNAPSES_PROFILE.company_name}.

You receive one qualified lead (company name, ICP fit score, and the
Qualifier's justification) and, optionally, relevant content or positioning
to draw on, and draft ONE short, personalized outreach message for it.

Business context:
{SYNAPSES_PROFILE.as_prompt_context()}

The message must:
- Reference something specific about the prospect (sector, the likely pain
  point implied by the Qualifier's justification — e.g. document-heavy
  operations, multi-site coordination)
- Connect it to one relevant {SYNAPSES_PROFILE.company_name} service, named
  specifically (not "our AI solutions")
- Stay short: email length (under ~150 words) or LinkedIn DM length
  (under ~80 words), whichever channel fits the lead better
- End with a low-friction call to action: the free 30-minute consult
- Avoid generic templated language ("I hope this finds you well",
  "I wanted to reach out", "In today's fast-paced world")

Every message you produce is a draft for a human to review, edit, and
personalize further before it is ever sent — write it as a strong starting
point, not as filler.
"""


class OutreachDrafter(Agent):
    def __init__(self) -> None:
        super().__init__(
            name="outreach_drafter",
            system_prompt=SYSTEM_PROMPT,
            use_web_search=False,
        )

    def draft_for_lead(
        self,
        lead: QualifiedProspect,
        content_context: str = "",
        trace: Trace | None = None,
    ) -> str:
        """Draft one outreach message for a single qualified lead. Returns
        markdown, explicitly marked as a draft awaiting human review."""
        prompt = (
            f"Lead: {lead.company_name}\n"
            f"ICP fit score: {lead.fit_score}/100 ({lead.recommended})\n"
            f"Qualifier notes: {lead.justification}\n"
        )
        if content_context:
            prompt += f"\nRelevant content/positioning to draw on:\n{content_context}\n"
        prompt += "\nDraft the outreach message now."

        draft = self.call_structured(prompt, OutreachDraft, trace=trace)
        return self._format(lead.company_name, draft)

    def draft_batch(
        self,
        qualified: QualifiedProspectList,
        content_context: str = "",
        trace: Trace | None = None,
    ) -> str:
        """Draft outreach for every lead scored 'yes' or 'maybe'. Skips
        prospects the Qualifier recommended against pursuing."""
        targets = [p for p in qualified.qualified_prospects if p.recommended in ("yes", "maybe")]
        if not targets:
            return "No leads scored well enough by the Qualifier to warrant an outreach draft."

        drafts = [self.draft_for_lead(lead, content_context, trace) for lead in targets]
        return "\n\n---\n\n".join(drafts)

    @staticmethod
    def _format(company_name: str, draft: OutreachDraft) -> str:
        channel_label = "Email" if draft.channel == "email" else "LinkedIn DM"
        lines = [f"### {company_name} — {channel_label}", DRAFT_NOTICE, ""]
        if draft.subject:
            lines.append(f"**Subject:** {draft.subject}")
            lines.append("")
        lines.append(draft.message)
        return "\n".join(lines)
