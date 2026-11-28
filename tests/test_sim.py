"""The simulator: the traffic generator, with every Flagsmith call replaced by a fake.

What matters here is the *shape* of what reaches Flagsmith - one exposure per experiment a learner is
enrolled in, and conversion events only for that learner's own arm - because that is what the
guardian's verdicts are computed from. The arm probabilities themselves are asserted in each
experiment's own test file.
"""
import random

from learnloop import knobs, sim


class Fake:
    """Stands in for Flagsmith: hands out a fixed arm and collects what was sent."""

    def __init__(self, arms: dict[str, str | None]):
        self.arms = arms
        self.exposures: list[tuple[str, str]] = []
        self.events: list[tuple[str, object]] = []

    def resolve(self, uid, traits=None):
        return self

    def arm_of(self, resolved, name, uid, traits=None):
        value = self.arms.get(name, "__missing__")
        if value is None:
            return None
        if value == "__missing__":
            value = next(iter(knobs.EXPERIMENTS[name]))
        self.exposures.append((name, value))
        return value

    def emit(self, event, uid, value=None, traits=None):
        self.events.append((event, value))


def drive(arms, users=300, seed=11):
    fake = Fake(arms)
    rng = random.Random(seed)
    for _ in range(users):
        sim.simulate_learner(rng, resolve=fake.resolve, arm_of=fake.arm_of, emit=fake.emit)
    return fake


def test_a_learner_is_exposed_to_each_experiment_at_most_once():
    fake = Fake({})
    seen = sim.simulate_learner(random.Random(3), resolve=fake.resolve, arm_of=fake.arm_of,
                                emit=fake.emit)
    assert len(seen) == len({flag for flag, _ in seen})


def test_every_experiment_flag_is_reachable_from_the_simulator():
    fake = drive({}, users=200)
    assert {flag for flag, _ in fake.exposures} == set(knobs.EXPERIMENTS)


def test_a_learner_not_enrolled_produces_no_exposure_and_no_events():
    fake = drive({name: None for name in knobs.EXPERIMENTS}, users=50)
    assert fake.exposures == []
    assert fake.events == []


def test_only_the_metrics_the_lab_declares_are_ever_sent():
    fake = drive({}, users=300)
    declared = {m for arms in knobs.EXPERIMENTS.values() for table in arms.values() for m in table}
    allowed = {m.removesuffix("_avg") for m in declared} | {"lesson_load_ms"}
    assert {event for event, _ in fake.events} <= allowed


def test_the_mean_metric_always_carries_a_numeric_value():
    fake = drive({"lesson_loading": "prefetch"}, users=200)
    values = [v for event, v in fake.events if event == "lesson_load_ms"]
    assert values and all(isinstance(v, int) and v >= 100 for v in values)


def test_occurrence_metrics_carry_no_value():
    fake = drive({}, users=200)
    assert all(v is None for event, v in fake.events if event != "lesson_load_ms")


def test_a_slower_arm_reports_higher_load_times():
    eager = drive({"lesson_loading": "eager"}, users=250)
    prefetch = drive({"lesson_loading": "prefetch"}, users=250)

    def mean(fake):
        vals = [v for e, v in fake.events if e == "lesson_load_ms"]
        return sum(vals) / len(vals)

    assert mean(prefetch) > mean(eager) * 1.3


def test_page_visit_rates_cover_every_experiment_page():
    assert set(knobs.PAGE_VISIT_RATE) == {"home", "pricing", "lesson", "quiz", "help"}
    assert all(0 < rate <= 1 for rate in knobs.PAGE_VISIT_RATE.values())


def test_a_dry_run_needs_no_network_and_splits_the_arms():
    tally = sim.run(200, dry_run=True)
    assert set(tally) == set(knobs.EXPERIMENTS)
    for flag, arms in tally.items():
        assert set(arms) <= set(knobs.EXPERIMENTS[flag])
        assert sum(arms.values()) > 0


def test_the_cli_refuses_to_send_without_an_environment_key(monkeypatch, capsys):
    monkeypatch.setattr(sim.flags, "client", lambda: None)
    assert sim.main(["--users", "5"]) == 2
    assert "No environment key" in capsys.readouterr().out


def test_the_cli_dry_run_reports_each_experiment(capsys):
    assert sim.main(["--users", "40", "--dry-run"]) == 0
    out = capsys.readouterr().out
    for flag in knobs.EXPERIMENTS:
        assert flag in out
