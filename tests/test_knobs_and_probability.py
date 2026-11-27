from learnloop import knobs, sim


def test_outcome_table_returns_configured_probabilities_for_known_arm():
    table = knobs.outcome_table("pricing_layout", "annual_first")
    assert table["subscription_started"] == 0.14
    assert table["revenue_avg"] == 14.0


def test_outcome_table_falls_back_to_control_for_unknown_arm():
    control = knobs.EXPERIMENTS["pricing_layout"]["monthly_first"]
    assert knobs.outcome_table("pricing_layout", "non_existent_arm") == control


def test_probability_scales_guardrail_metrics_by_guardrail_factor(monkeypatch):
    monkeypatch.setattr(knobs, "GUARDRAIL_FACTOR", 1.5)
    base_p = knobs.outcome_table("quiz_timer", "none")["quiz_abandoned"]
    calc_p = sim._p("quiz_timer", "none", "quiz_abandoned")
    assert calc_p == base_p * 1.5


def test_probability_scales_positive_metrics_by_global_lift(monkeypatch):
    monkeypatch.setattr(knobs, "GLOBAL_LIFT", 0.5)
    base_p = knobs.outcome_table("quiz_timer", "none")["quiz_passed"]
    calc_p = sim._p("quiz_timer", "none", "quiz_passed")
    assert calc_p == base_p * 0.5


def test_probability_clamps_at_one(monkeypatch):
    monkeypatch.setattr(knobs, "GLOBAL_LIFT", 10.0)
    calc_p = sim._p("quiz_timer", "none", "quiz_passed")
    assert calc_p == 1.0


def test_probability_returns_zero_for_untracked_metric():
    assert sim._p("quiz_timer", "none", "untracked_metric_event") == 0.0
