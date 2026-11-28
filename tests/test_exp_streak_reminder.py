"""E5 `streak_reminder` - the experiment built to stay INCONCLUSIVE.

Two things keep it there, and both are deliberate:

  * it carries TWO goal metrics, `daily_return` and `streak_continued`, and `policy.yaml` names
    neither as primary - with more than one goal metric the guardian refuses to pick for you, so no
    winner can ever be promoted (`no_primary_metric`);
  * the lifts are tiny anyway, so neither metric would clear a 0.95 win probability.
"""
from conftest import goto

from learnloop import experiments, knobs


# ---- the arm logic, pure ----------------------------------------------------------------------
def test_control_shows_no_nudge():
    assert experiments.streak_reminder_copy("none", 5) is None


def test_the_variant_shows_a_nudge_naming_the_streak():
    copy = experiments.streak_reminder_copy("gentle", 12)
    assert "12-day streak" in copy


def test_an_unknown_arm_behaves_like_control():
    assert experiments.streak_reminder_copy("urgent", 5) is None
    assert experiments.streak_reminder_copy(None, 5) is None


# ---- the knobs that keep this INCONCLUSIVE ----------------------------------------------------
def test_both_lifts_are_too_small_to_declare_a_winner():
    arms = knobs.EXPERIMENTS["streak_reminder"]
    for metric in ("daily_return", "streak_continued"):
        control, variant = arms["none"][metric], arms["gentle"][metric]
        lift = (variant - control) / control
        assert 0 < lift < 0.10, f"{metric} lift {lift:.3f} is outside the inconclusive window"


def test_neither_metric_moves_backwards():
    arms = knobs.EXPERIMENTS["streak_reminder"]
    for metric in ("daily_return", "streak_continued"):
        assert arms["gentle"][metric] >= arms["none"][metric], \
            "a negative lift could trip the harm branch instead of staying inconclusive"


def test_the_experiment_declares_exactly_two_goal_metrics():
    assert set(knobs.EXPERIMENTS["streak_reminder"]["none"]) == {"daily_return", "streak_continued"}


# ---- the page --------------------------------------------------------------------------------
def test_home_shows_the_nudge_on_the_variant(arm, app):
    arm("streak_reminder", "gentle")
    at = app().run()
    assert not at.exception
    assert any("streak" in w.value for w in at.warning)


def test_home_shows_no_nudge_on_control(arm, app):
    arm("streak_reminder", "none")
    at = app().run()
    assert not any("streak" in str(w.value) for w in at.warning)


def test_both_conversions_are_reachable_from_home(arm, app, tracked):
    arm("streak_reminder", "gentle")
    at = app().run()
    next(b for b in at.button if b.label == "I'll come back tomorrow").click().run()
    next(b for b in at.button if b.label == "Keep the streak alive").click().run()
    assert ("daily_return", None) in tracked
    assert ("streak_continued", None) in tracked


def test_the_nudge_does_not_leak_onto_other_pages(arm, app):
    arm("streak_reminder", "gentle")
    at = goto(app().run(), "Quiz")
    assert not any("streak" in str(w.value) for w in at.warning)
