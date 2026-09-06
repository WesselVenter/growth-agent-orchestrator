"""
context/business_profile.py

Shared business context for SynapsesAI's growth agent orchestration system.
Every agent (Research, Lead Gen, Content, Sales Support) reads from this
to stay grounded in real brand voice, real ICP, and real positioning.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ServiceOffering:
    name: str
    description: str
    starting_price: str
    tech_notes: str = ""


@dataclass
class ICP:
    ownership: str
    staff_range: str
    site_range: str
    operational_profile: str
    decision_maker_profile: str
    disqualifiers: List[str] = field(default_factory=list)


@dataclass
class BusinessProfile:
    company_name: str = "SynapsesAI"
    tagline: str = "We build the systems that run your business."
    one_liner: str = (
        "A done-for-you AI operations platform for South African SMBs: "
        "private AI systems, automation workflows, custom applications, "
        "and websites, built around how the business actually runs."
    )
    country: str = "South Africa"
    website: str = "https://www.synapsesai.co.za"
    contact_email: str = "synapsesai.sa@gmail.com"

    flagship_product: ServiceOffering = field(default_factory=lambda: ServiceOffering(
        name="AI Operating System (Company Brain)",
        description=(
            "A private, POPIA-compliant AI knowledge system. Staff query internal "
            "documents in plain language and get answers with source citations. "
            "Also drafts emails for approval and sends one daily WhatsApp briefing. "
            "Nothing leaves the client's environment; nothing trains public models."
        ),
        starting_price="R20,000 pilot",
        tech_notes="Built on Claude AI, PostgreSQL, hosted with POPIA in mind.",
    ))

    other_services: List[ServiceOffering] = field(default_factory=lambda: [
        ServiceOffering(
            name="Automation Workflows",
            description=(
                "Custom automation built on an n8n stack. Automates invoicing, "
                "quoting, marketing, and lead follow-up so routine work runs itself "
                "and nothing slips through the cracks."
            ),
            starting_price="R4,000 per workflow",
        ),
        ServiceOffering(
            name="Custom Applications",
            description=(
                "Purpose-built software for a specific business need — e.g. a "
                "staff portal, compliance tracker, or booking system."
            ),
            starting_price="R25,000 per build",
        ),
        ServiceOffering(
            name="Custom Websites",
            description=(
                "Fast, modern landing pages or full websites that plug directly "
                "into the automation, apps, and Company Brain SynapsesAI builds."
            ),
            starting_price="R8,000 per site",
        ),
    ])

    differentiators: List[str] = field(default_factory=lambda: [
        "Data never leaves the client's environment and is never used to train public models",
        "Human-in-the-loop by design: nothing goes out to a customer without approval — not a black box",
        "One partner builds everything, so automation, apps, and website all plug into the same 'brain'",
        "Hands-on ISO 9001 / 27001 experience; everything handled with POPIA in mind",
        "Delivered on tools SA SMBs already trust: WhatsApp Business Platform, Claude AI, PostgreSQL",
    ])

    icp: ICP = field(default_factory=lambda: ICP(
        ownership="South African-owned",
        staff_range="30–300 staff",
        site_range="1–5 sites",
        operational_profile=(
            "Document-heavy operations — significant institutional knowledge trapped "
            "in files, procedures, and staff memory rather than a searchable system"
        ),
        decision_maker_profile=(
            "Owner-managed, or has a local MD/GM who can approve a build without "
            "a formal procurement committee or multi-stakeholder sign-off"
        ),
        disqualifiers=[
            "Multinational or foreign-owned with procurement centralized abroad",
            "Requires formal RFP/tender process to engage a vendor",
            "Very small (<10 staff) with little internal documentation to build on",
            "Highly regulated in ways that require accreditation SynapsesAI doesn't hold "
            "(e.g. certain financial services, medical device manufacturing)",
        ],
    ))

    sales_funnel: List[str] = field(default_factory=lambda: [
        "Free 30-minute discovery consultation",
        "Written summary of proposed build + cost + savings, delivered within 48 hours",
        "Build and go live in 2–3 weeks, including training for the client's team",
    ])

    voice_guidelines: List[str] = field(default_factory=lambda: [
        "Practical and plain-language — no AI hype, no jargon",
        "Compliance-aware — POPIA and data privacy are selling points, not caveats",
        "Confident but not salesy — lead with what the system does for the business day to day",
        "Always frame AI as staff-assisting, human-approved — never fully autonomous or unsupervised",
    ])

    def as_prompt_context(self) -> str:
        """Render the profile as plain text for inclusion in agent system prompts."""
        other_services = "\n".join(
            f"- {s.name}: {s.description} (from {s.starting_price})"
            for s in self.other_services
        )
        differentiators = "\n".join(f"- {d}" for d in self.differentiators)
        disqualifiers = "\n".join(f"- {d}" for d in self.icp.disqualifiers)
        funnel = " -> ".join(self.sales_funnel)
        voice = "\n".join(f"- {v}" for v in self.voice_guidelines)

        return f"""Company: {self.company_name} — {self.tagline}
{self.one_liner}
Country: {self.country} | Website: {self.website} | Contact: {self.contact_email}

Flagship product: {self.flagship_product.name}
{self.flagship_product.description}
From {self.flagship_product.starting_price}. ({self.flagship_product.tech_notes})

Other services:
{other_services}

Differentiators:
{differentiators}

Ideal Customer Profile (ICP):
- Ownership: {self.icp.ownership}
- Staff: {self.icp.staff_range}
- Sites: {self.icp.site_range}
- Operational profile: {self.icp.operational_profile}
- Decision maker: {self.icp.decision_maker_profile}

ICP disqualifiers (do not pursue if any apply):
{disqualifiers}

Sales funnel:
{funnel}

Voice guidelines:
{voice}
"""


# Single shared instance every agent imports
SYNAPSES_PROFILE = BusinessProfile()
