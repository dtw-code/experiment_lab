"""Offline tests: pure parsing + the simulator's knob wiring (no Flagsmith, no Streamlit)."""
import random

from learnloop import flags, knobs, sim


def test_lesson_config_parsing_falls_back():
    assert flags.parse_lesson_length('{"minutes": 5, "cards": 4}') == {"minutes": 5, "cards": 4}
    assert flags.parse_lesson_length("not json")["minutes"] == 10
    assert flags.lesson_arm({"minutes": 5, "cards": 4}) == "5min"


def test_quiz_timer_parsing():
    assert flags.parse_quiz_timer("none") is None
    assert flags.parse_quiz_timer("30") == 30
    assert flags.parse_quiz_timer(0) is None


def test_unknown_arm_falls_back_to_control():
    assert knobs.outcome_table("quiz_timer", "999") == knobs.EXPERIMENTS["quiz_timer"]["none"]


def test_dry_run_exposes_every_experiment():
    tally = sim.run(300, dry_run=True)
    assert set(tally) == set(knobs.EXPERIMENTS)
    assert set(tally["pricing_layout"]) == set(knobs.EXPERIMENTS["pricing_layout"])


def test_onboarding_only_for_new_learners():
    seen = []
    rng = random.Random(1)

    def expose(name, uid, traits=None):
        if name == "onboarding_flow":
            seen.append(traits["days_since_signup"])
        return True, '{"minutes": 10}' if name == "lesson_length" else next(iter(knobs.EXPERIMENTS[name]))

    noop = lambda *a, **k: None  # noqa: E731
    for _ in range(200):
        sim.simulate_user(rng, emit=noop, expose=expose, plain=noop)
    assert seen and all(d <= 7 for d in seen)
