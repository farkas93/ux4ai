"""Shared classroom test-order guidance, not a calibrated risk estimate."""

RANKING_RULE = "High-risk hypotheses with limited evidence are shown first. This is discussion guidance, not a readiness score."


def priority_score(risk: float, evidence: float) -> float:
    return risk * (10 - evidence)


def test_first(risk: float, evidence: float) -> bool:
    return risk >= 5 and evidence <= 5


def priority_group_score(risk: float, evidence: float) -> tuple[bool, float]:
    return test_first(risk, evidence), priority_score(risk, evidence)


def hypothesis_header(number: int, statement: str, max_characters: int = 52) -> str:
    """Create equally bounded H-number headers in the hypothesis editor."""
    prefix = f"H{number} · "
    clean = " ".join((statement or "").split())
    available = max(1, max_characters - len(prefix))
    if len(clean) > available:
        clean = clean[:available - 1].rstrip() + "…"
    return prefix + clean
