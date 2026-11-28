"""E4 `lesson_loading` - the experiment built to reach SEVERE_HARM, and the lab's only MEAN metric.

`lesson_load_ms` is not a rate: the event carries a numeric millisecond value and Flagsmith averages
it, so the guardian judges it through its mean family (`guardian/aggregates.py`) instead of a Wilson
interval. Lower is better, and the variant is much higher.
"""
import random

from conftest import goto

from learnloop import experiments, knobs


# ---- the arm logic, pure ----------------------------------------------------------------------
def test_each_arm_reports_its_own_average_without_jitter():
    assert experiments.lesson_loading_ms("eager") == 1500
    assert experiments.lesson_loading_ms("prefetch") == 2400


def test_an_unknown_arm_falls_back_to_control():
    assert experiments.lesson_loading_ms("lazy") == experiments.lesson_loading_ms("eager")


def test_jittered_times_stay_positive_and_centre_on_the_average():
    rng = random.Random(1)
    draws = [experiments.lesson_loading_ms("eager", rng) for _ in range(400)]
    assert min(draws) >= 100
    assert abs(sum(draws) / len(draws) - 1500) < 150


def test_the_variant_is_slower_than_control_on_average():
    rng = random.Random(2)
    eager = sum(experiments.lesson_loading_ms("eager", rng) for _ in range(300))
    prefetch = sum(experiments.lesson_loading_ms("prefetch", rng) for _ in range(300))
    assert prefetch > eager


# ---- the knobs that make this SEVERE and not merely HARMFUL -----------------------------------
def test_the_variant_worsens_by_more_than_the_severe_bar():
    arms = knobs.EXPERIMENTS["lesson_loading"]
    control = arms["eager"]["lesson_load_ms_avg"]
    variant = arms["prefetch"]["lesson_load_ms_avg"]
    worsening = (variant - control) / control
    assert worsening >= 0.25, "policy.severe_min_relative_worsening is the bar for SEVERE_HARM"
    assert worsening >= 0.40, "leave margin: sampling noise must not drop it under the bar"


def test_the_spread_is_tight_enough_for_the_interval_to_exclude_zero():
    assert knobs.LOAD_TIME_SPREAD <= 0.35


# ---- the page --------------------------------------------------------------------------------
def test_the_lesson_page_names_the_arm_it_was_served(arm, app):
    arm("lesson_loading", "prefetch")
    at = goto(app().run(), "Lesson")
    assert not at.exception
    assert "Content loading: prefetch" in [c.value for c in at.caption]


def test_starting_a_lesson_records_the_load_time_as_the_event_value(arm, app, tracked):
    arm("lesson_loading", "prefetch")
    at = goto(app().run(), "Lesson")
    next(b for b in at.button if b.label == "Start lesson").click().run()
    assert ("lesson_load_ms", 2400) in tracked


def test_control_records_the_faster_load_time(arm, app, tracked):
    arm("lesson_loading", "eager")
    at = goto(app().run(), "Lesson")
    next(b for b in at.button if b.label == "Start lesson").click().run()
    assert ("lesson_load_ms", 1500) in tracked


def test_the_load_time_is_recorded_once_per_session(arm, app, tracked):
    arm("lesson_loading", "eager")
    at = goto(app().run(), "Lesson")
    button = next(b for b in at.button if b.label == "Start lesson")
    button.click().run()
    button.click().run()
    assert [e for e, _ in tracked].count("lesson_load_ms") == 1
