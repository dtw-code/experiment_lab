import random
from learnloop import sim


def test_make_traits_generates_valid_schema_and_expected_ranges():
    rng = random.Random(42)
    valid_plans = {"free", "pro", "enterprise"}
    valid_countries = {"IN", "US", "UK", "DE"}
    valid_streaks = {0, 1, 3, 7, 14, 30, 45}

    for _ in range(50):
        traits = sim.make_traits(rng)
        assert traits["plan"] in valid_plans
        assert traits["country"] in valid_countries
        assert traits["streak_days"] in valid_streaks
        assert 0 <= traits["days_since_signup"] <= 400


def test_simulate_user_restricts_onboarding_to_learners_within_seven_days():
    # Force traits to have days_since_signup > 7
    rng = random.Random(123)
    exposures_recorded = []
    events_recorded = []

    def fake_expose(name, uid, traits=None):
        exposures_recorded.append(name)
        return True, "control"

    def fake_emit(event, uid, value=None, traits=None):
        events_recorded.append(event)

    def fake_plain(name, uid, traits=None):
        pass

    # Test with user who signed up 8 days ago
    orig_make_traits = sim.make_traits
    try:
        sim.make_traits = lambda r: {
            "plan": "free",
            "country": "US",
            "days_since_signup": 8,
            "streak_days": 1,
        }
        for _ in range(30):
            sim.simulate_user(rng, emit=fake_emit, expose=fake_expose, plain=fake_plain)

        assert "onboarding_flow" not in exposures_recorded
        assert "onboarding_completed" not in events_recorded
        assert "onboarding_skipped" not in events_recorded
    finally:
        sim.make_traits = orig_make_traits


def test_simulate_user_evaluates_all_plain_flags_on_every_session():
    rng = random.Random(999)
    evaluated_plain_flags = []

    def fake_plain(name, uid, traits=None):
        evaluated_plain_flags.append(name)

    sim.simulate_user(
        rng,
        emit=lambda *a, **k: None,
        expose=lambda name, uid, traits=None: (True, "val"),
        plain=fake_plain,
    )

    expected_plain = {
        "maintenance_mode",
        "beta_exam_mode",
        "support_chat",
        "daily_goal_xp",
        "ai_tutor",
        "legacy_leaderboard",
    }
    assert expected_plain.issubset(set(evaluated_plain_flags))


def test_simulate_user_emits_lesson_started_when_lesson_page_visited(monkeypatch):
    rng = random.Random(42)
    # Ensure lesson page is always hit
    monkeypatch.setitem(sim.knobs.PAGE_VISIT_RATE, "lesson", 1.0)

    emitted_events = []

    def fake_emit(event, uid, value=None, traits=None):
        emitted_events.append(event)

    def fake_expose(name, uid, traits=None):
        if name == "lesson_length":
            return True, '{"minutes": 10, "cards": 8}'
        return True, "control"

    sim.simulate_user(
        rng,
        emit=fake_emit,
        expose=fake_expose,
        plain=lambda *a, **k: None,
    )

    assert "lesson_started" in emitted_events


def test_simulate_user_emits_revenue_when_subscription_started_fires(monkeypatch):
    rng = random.Random(42)
    monkeypatch.setitem(sim.knobs.PAGE_VISIT_RATE, "pricing", 1.0)
    # Force subscription_started probability to 1.0
    monkeypatch.setattr(sim, "_p", lambda exp, arm, metric: 1.0 if metric == "subscription_started" else 0.0)

    emitted = []

    def fake_emit(event, uid, value=None, traits=None):
        emitted.append((event, value))

    sim.simulate_user(
        rng,
        emit=fake_emit,
        expose=lambda name, uid, traits=None: (True, "monthly_first"),
        plain=lambda *a, **k: None,
    )

    event_names = [e[0] for e in emitted]
    assert "subscription_started" in event_names
    assert "revenue" in event_names
    revenue_value = next(val for evt, val in emitted if evt == "revenue")
    assert isinstance(revenue_value, float)
    assert revenue_value > 0.0
