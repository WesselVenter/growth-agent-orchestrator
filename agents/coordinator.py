"""Coordinator: given a goal and the teams selected for it, runs each team's
agent pipeline in the right order and assembles the final report."""

from __future__ import annotations

from agents.base import Agent
from agents.content.critic import MAX_REVISIONS, SCORE_THRESHOLD, Critic
from agents.content.strategist import Strategist
from agents.content.writer import Writer
from agents.leadgen.prospector import Prospector
from agents.leadgen.qualifier import Qualifier, QualifiedProspectList
from agents.research.researcher import Researcher
from agents.research.synthesizer import Synthesizer
from agents.sales.outreach_drafter import OutreachDrafter
from context.business_profile import SYNAPSES_PROFILE
from orchestration.trace import Trace

REPORT_SYSTEM_PROMPT = f"""You are the Coordinator agent for {SYNAPSES_PROFILE.company_name}.

You receive a goal and the outputs produced by one or more specialist teams
(research, leadgen, content, sales). Assemble these into a single, coherent
final Markdown report addressed to a {SYNAPSES_PROFILE.company_name} team
member who requested this work.

Structure:
1. Summary of what was done, in relation to the original goal
2. Key outputs from each team that ran (organized by team, in full)
3. Recommended next actions

Do not invent information that wasn't produced by a team. Preserve
important detail (e.g. full lead lists, full drafts) rather than
over-summarizing. If the sales team produced outreach drafts, keep their
"DRAFT — for human review" markers intact in the report.
"""


class Coordinator:
    def __init__(self) -> None:
        self.report_agent = Agent(name="coordinator", system_prompt=REPORT_SYSTEM_PROMPT)

    def run(self, goal: str, teams: list[str], trace: Trace) -> str:
        """Run whichever teams are in `teams`, in dependency order, and
        return the assembled final Markdown report. `teams` is expected to
        come from orchestration.router.route()."""
        team_outputs: dict[str, str] = {}

        research_brief = ""
        if "research" in teams:
            trace.log_handoff("coordinator", "research", f"goal requires market research: {goal}")
            research_brief = self._run_research(goal, trace)
            team_outputs["research"] = research_brief

        qualified_leads: QualifiedProspectList | None = None
        if "leadgen" in teams:
            trace.log_handoff("coordinator", "leadgen", f"goal requires lead generation: {goal}")
            qualified_leads = self._run_leadgen(goal, trace)
            team_outputs["leadgen"] = qualified_leads.to_markdown()

        content_output = ""
        if "content" in teams:
            trace.log_handoff("coordinator", "content", f"goal requires content: {goal}")
            # Research feeds Content: pass the market brief along if it ran.
            content_output = self._run_content(goal, research_brief, trace)
            team_outputs["content"] = content_output

        if "sales" in teams:
            trace.log_handoff("coordinator", "sales", f"goal requires outreach drafts: {goal}")
            # Lead Gen feeds Sales: draft against the qualified leads (and
            # content, if any ran) rather than the raw goal.
            team_outputs["sales"] = self._run_sales(qualified_leads, content_output, trace)

        trace.log_handoff("coordinator", "coordinator", "assembling final report")
        return self._assemble_report(goal, teams, team_outputs, trace)

    def _run_research(self, goal: str, trace: Trace) -> str:
        researcher = Researcher()
        synthesizer = Synthesizer()
        findings = researcher.call(goal, trace)
        trace.log_handoff("researcher", "synthesizer", "raw findings ready for synthesis")
        brief = synthesizer.synthesize(findings, trace)
        return brief.to_markdown()

    def _run_leadgen(self, goal: str, trace: Trace) -> QualifiedProspectList:
        prospector = Prospector()
        qualifier = Qualifier()
        candidates = prospector.call(goal, trace)
        trace.log_handoff("prospector", "qualifier", "candidate list ready for qualification")
        return qualifier.qualify(candidates, trace)

    def _run_content(self, goal: str, research_brief: str, trace: Trace) -> str:
        strategist = Strategist()
        writer = Writer()
        critic = Critic()

        strategist_input = goal if not research_brief else f"{goal}\n\nMarket brief:\n{research_brief}"
        angle_list = strategist.generate_angles(strategist_input, trace)
        angle = angle_list.angles[0]
        trace.log_handoff(
            "strategist", "writer", f"{len(angle_list.angles)} angles generated; drafting on: {angle.headline}"
        )

        draft = writer.draft(angle, trace)

        revision_count = 0
        while True:
            trace.log_handoff("writer", "critic", f"draft ready for review (pass {revision_count + 1})")
            critique = critic.grade(draft, trace)

            if critique.overall_score >= SCORE_THRESHOLD or revision_count >= MAX_REVISIONS:
                trace.log_handoff(
                    "critic", "coordinator",
                    f"draft finalized at score {critique.overall_score}/10 after {revision_count} revision(s)",
                )
                break

            revision_count += 1
            trace.log_handoff(
                "critic", "writer",
                f"revision {revision_count} requested (score {critique.overall_score}/10): {critique.feedback}",
            )
            draft = writer.revise(draft, critique.feedback, trace)

        return draft

    def _run_sales(
        self, qualified_leads: QualifiedProspectList | None, content_output: str, trace: Trace
    ) -> str:
        if qualified_leads is None or not qualified_leads.qualified_prospects:
            return "No qualified leads were available to draft outreach against."

        drafter = OutreachDrafter()
        return drafter.draft_batch(qualified_leads, content_output, trace)

    def _assemble_report(
        self, goal: str, teams: list[str], team_outputs: dict[str, str], trace: Trace
    ) -> str:
        sections = "\n\n".join(
            f"=== {team.upper()} OUTPUT ===\n{output}"
            for team, output in team_outputs.items()
        )
        prompt = f"Goal: {goal}\n\nTeams run: {', '.join(teams)}\n\n{sections}"
        return self.report_agent.call(prompt, trace)
