"""Router: given a goal string, decides which team(s) are needed.

Keyword-based routing, kept intentionally simple and inspectable. A pure
lead-gen goal ("find 10 leads in the legal sector") matches only leadgen and
skips Content; a pure content-planning goal ("write 3 LinkedIn posts about
X") matches only content and skips Lead Gen. A sales-outreach goal always
pulls in leadgen too, since outreach drafts need leads to draft against.
"""

from __future__ import annotations

TEAMS = ("research", "leadgen", "content", "sales")

_KEYWORDS: dict[str, tuple[str, ...]] = {
    "research": (
        "market", "competitor", "trend", "industry", "landscape",
        "research", "brief",
    ),
    "leadgen": (
        "lead", "prospect", "leads", "companies", "sector", "icp",
        "find me", "list of",
    ),
    "content": (
        "post", "content", "write", "blog", "copy", "linkedin post",
        "article", "campaign", "newsletter",
    ),
    "sales": (
        "outreach", "cold email", "cold outreach", "reach out",
        "sales email", "linkedin dm", "cold dm", "pitch to", "pitch these",
    ),
}


def route(goal: str) -> list[str]:
    """Return the ordered list of teams a goal likely needs.

    Falls back to ["research"] if nothing matches, since a market brief is
    a safe default starting point.
    """
    goal_lower = goal.lower()
    matched = [
        team for team in TEAMS
        if any(kw in goal_lower for kw in _KEYWORDS[team])
    ]

    # Outreach drafts need leads to draft against, even if the goal didn't
    # separately mention finding/qualifying prospects.
    if "sales" in matched and "leadgen" not in matched:
        matched.insert(matched.index("sales"), "leadgen")

    return matched or ["research"]
