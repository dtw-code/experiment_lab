"""E1 `pricing_layout` - the experiment built to reach WINNER.

Everything about this flag is here and nowhere else, so removing the experiment means deleting this
file plus one block each in app.py, learnloop/experiments.py, learnloop/knobs.py and
learnloop/flags.py. The conversion event `subscription_started` outlives the flag: it is a product
metric, and `cleanup.yaml` protects every `track_event(` line from being touched.
"""
from conftest import goto

from learnloop import experiments, knobs


# ---- the arm logic, pure ----------------------------------------------------------------------
def test_control_leads_with_the_monthly_plan():
    assert experiments.pricing_layout_tiers("monthly_first")[0] == ("Monthly", 9)


def test_the_variant_leads_with_the_annual_plan():
    assert experiments.pricing_layout_tiers("annual_first")[0][1] == 79


def test_both_arms_offer_the_same_two_plans():
    control = sorted(p for _, p in experiments.pricing_layout_tiers("monthly_first"))
    variant = sorted(p for _, p in experiments.pricing_layout_tiers("annual_first"))
    assert control == variant == [9, 79]


def test_an_unknown_arm_falls_back_to_control():
    assert experiments.pricing_layout_tiers("something_else") == experiments.PRICING_LAYOUTS["monthly_first"]
    assert experiments.pricing_layout_tiers(None) == experiments.PRICING_LAYOUTS["monthly_first"]


# ---- the knobs that make this experiment a WINNER ---------------------------------------------
def test_the_variant_is_tuned_to_win_clearly():
    arms = knobs.EXPERIMENTS["pricing_layout"]
    control = arms["monthly_first"]["subscription_started"]
    variant = arms["annual_first"]["subscription_started"]
    assert variant > control
    assert (variant - control) / control >= 0.40, \
        "a WINNER needs win probability >= 0.95 with the interval clear of zero"


# ---- the page --------------------------------------------------------------------------------
def test_the_pricing_page_renders_the_arm_it_was_served(arm, app):
    arm("pricing_layout", "annual_first")
    at = goto(app().run(), "Pricing")
    assert not at.exception
    assert any("Annual (save 27%): $79" in b.label for b in at.button)


def test_subscribing_records_one_conversion(arm, app, tracked):
    arm("pricing_layout", "annual_first")
    at = goto(app().run(), "Pricing")
    button = next(b for b in at.button if "Annual (save 27%)" in b.label)
    button.click().run()
    assert ("subscription_started", None) in tracked


def test_a_second_click_does_not_inflate_the_metric(arm, app, tracked):
    arm("pricing_layout", "monthly_first")
    at = goto(app().run(), "Pricing")
    button = next(b for b in at.button if "Monthly: $9" in b.label)
    button.click().run()
    button.click().run()
    assert [e for e, _ in tracked].count("subscription_started") == 1
