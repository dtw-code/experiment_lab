"""E2 `quiz_timer` - the experiment built to reach HARMFUL_VARIANT.

Harmful, not severe: the variant is clearly worse but by less than the 25% relative worsening that
`policy.yaml` calls severe. The knob test below is what keeps that true, so a later tweak that widens
the gap fails here instead of silently turning the demo into SEVERE_HARM.
"""
import pytest
from conftest import goto

from learnloop import experiments, knobs


# ---- the arm logic, pure ----------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("none", None), ("", None), (None, None), ("0", None), ("-5", None),
    ("30", 30), (30, 30), (" 30 ", 30),
])
def test_the_timer_is_read_from_the_arm_value(raw, expected):
    assert experiments.quiz_timer_seconds(raw) == expected


def test_control_is_untimed():
    assert experiments.quiz_timer_seconds("none") is None


# ---- the knobs that keep this HARMFUL and not SEVERE ------------------------------------------
def test_the_variant_is_worse_but_not_severely():
    arms = knobs.EXPERIMENTS["quiz_timer"]
    control, variant = arms["none"]["quiz_passed"], arms["30"]["quiz_passed"]
    worsening = (control - variant) / control
    assert worsening > 0, "the variant has to lose for HARMFUL_VARIANT"
    assert worsening < 0.25, \
        "at or above policy.severe_min_relative_worsening this becomes SEVERE_HARM instead"
    assert worsening > 0.08, "too small and it will not reach win probability <= 0.05"


# ---- the page --------------------------------------------------------------------------------
def test_the_quiz_shows_the_countdown_on_the_variant(arm, app):
    arm("quiz_timer", "30")
    at = goto(app().run(), "Quiz")
    assert not at.exception
    assert any("30s timer" in c.value for c in at.caption)


def test_the_quiz_is_untimed_on_control(arm, app):
    arm("quiz_timer", "none")
    at = goto(app().run(), "Quiz")
    assert any("Untimed" in c.value for c in at.caption)


def test_a_correct_answer_records_the_pass(arm, app, tracked):
    arm("quiz_timer", "none")
    at = goto(app().run(), "Quiz")
    at.radio(key="q1").set_value("3").run()
    next(b for b in at.button if b.label == "Submit").click().run()
    assert ("quiz_passed", None) in tracked


def test_a_wrong_answer_records_nothing(arm, app, tracked):
    arm("quiz_timer", "30")
    at = goto(app().run(), "Quiz")
    at.radio(key="q1").set_value("4").run()
    next(b for b in at.button if b.label == "Submit").click().run()
    assert tracked == []
