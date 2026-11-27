from learnloop import flags, knobs, sim


def test_batch_simulation_dry_run_covers_all_experiments_offline():
    tally = sim.run(users=300, dry_run=True)
    assert set(tally.keys()) == set(knobs.EXPERIMENTS.keys())
    for exp, arms in tally.items():
        assert len(arms) > 0
        expected_arms = set(knobs.EXPERIMENTS[exp].keys())
        assert set(arms.keys()).issubset(expected_arms)
        for arm, count in arms.items():
            assert count > 0, f"Expected non-zero exposure count for {exp}.{arm}, got {count}"


def test_batch_simulation_flushes_events_at_intervals_and_finish(monkeypatch):
    flush_calls = []

    monkeypatch.setattr(flags, "flush", lambda: flush_calls.append("flush"))
    monkeypatch.setattr(flags, "experiment", lambda name, uid, traits=None: (True, "control"))
    monkeypatch.setattr(flags, "track", lambda *a, **k: None)
    monkeypatch.setattr(flags, "flag", lambda *a, **k: (False, None))

    # 250 users should trigger flush at user 99, user 199, and post-loop completion (3 flushes total)
    sim.run(users=250, dry_run=False)
    assert len(flush_calls) == 3
