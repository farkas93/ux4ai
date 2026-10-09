from aipm_toolkit.priority_rules import priority_group_score, priority_score
from aipm_toolkit.priority_rules import test_first as in_test_first
from aipm_toolkit.ui.callbacks import _ranking_items


def test_uncertainty_does_not_create_priority_without_risk():
    assert priority_score(0, 0) == 0
    assert priority_score(0, 10) == 0
    assert priority_score(9, 2) == 72
    items = _ranking_items(["a", "b"], ["No risk", "Risky"], [0, 9], [0, 6])
    assert [item["statement"] for item in items] == ["Risky", "No risk"]


def test_upper_left_group_precedes_larger_score_outside_it():
    # Explicit quadrant guidance takes precedence over the product score.
    items = _ranking_items(["a", "b", "c"], ["Low risk", "Test first", "Strong evidence"], [4.5, 5, 10], [0, 5, 6])
    assert [item["statement"] for item in items] == ["Test first", "Low risk", "Strong evidence"]
    assert in_test_first(5, 5)
    assert not in_test_first(4.5, 0)
    assert not in_test_first(10, 5.5)
    assert priority_group_score(5, 5) > priority_group_score(4.5, 0)


def test_ties_keep_order_within_group_and_fully_evidenced_scores_zero():
    items = _ranking_items(["a", "b", "c"], ["First", "Second", "Evidenced"], [8, 8, 10], [2, 2, 10])
    assert [item["statement"] for item in items] == ["First", "Second", "Evidenced"]
    assert items[-1]["priority"] == 0
