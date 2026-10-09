"""Shared classroom test-order guidance, not a calibrated risk estimate."""

RANKING_RULE = (
    "Test first: risk 5–10 and evidence 0–5. This group comes first. "
    "Within each group, rank by risk × (10 − evidence), highest first. "
    "Uncertainty amplifies risk: zero risk means zero priority. "
    "Equal scores within a group are tied. This is discussion guidance, not a readiness score."
)


def priority_score(risk: float, evidence: float) -> float:
    return risk * (10 - evidence)


def test_first(risk: float, evidence: float) -> bool:
    return risk >= 5 and evidence <= 5


def priority_group_score(risk: float, evidence: float) -> tuple[bool, float]:
    return test_first(risk, evidence), priority_score(risk, evidence)
