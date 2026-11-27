"""Headless user simulator. Same flag + metric calls as the web UI, driven by learnloop/knobs.py.

    py -m learnloop.sim                 # SIM_USERS users from knobs.py
    py -m learnloop.sim --users 2000
    py -m learnloop.sim --dry-run       # no Flagsmith calls: prints what each arm would be fed (sanity check of knobs)
"""
from __future__ import annotations

import argparse
import random
import uuid
from collections import Counter, defaultdict

from . import flags, knobs


def make_traits(rng: random.Random) -> dict:
    new = rng.random() < knobs.NEW_LEARNER_SHARE
    return {
        "plan": rng.choices(["free", "pro", "enterprise"], [70, 25, 5])[0],
        "country": rng.choice(["IN", "US", "UK", "DE"]),
        "days_since_signup": rng.randint(0, 7) if new else rng.randint(8, 400),
        "streak_days": rng.choice([0, 1, 3, 7, 14, 30, 45]),
    }


def _p(experiment: str, arm: str, metric: str) -> float:
    p = knobs.outcome_table(experiment, arm).get(metric, 0.0)
    if metric in knobs.GUARDRAIL_METRICS:
        return min(1.0, p * knobs.GUARDRAIL_FACTOR)
    return min(1.0, p * knobs.GLOBAL_LIFT)


def simulate_user(rng: random.Random, emit=flags.track, expose=flags.experiment,
                  plain=flags.flag) -> list[tuple[str, str]]:
    """One user session. Returns [(experiment, arm)] exposures; emits metric events through `emit`."""
    uid = f"sim-{uuid.uuid4()}"
    traits = make_traits(rng)
    seen: list[tuple[str, str]] = []

    def hit(page: str) -> bool:
        return rng.random() < knobs.PAGE_VISIT_RATE[page]

    def fire(exp: str, arm: str, metric: str, value=None):
        if rng.random() < _p(exp, arm, metric):
            emit(metric, uid, value, traits)

    if hit("home"):  # E5 streak_reminder
        _, v = expose("streak_reminder", uid, traits)
        seen.append(("streak_reminder", v))
        fire("streak_reminder", v, "daily_return")
        fire("streak_reminder", v, "reminder_opt_out")

    if traits["days_since_signup"] <= 7 and hit("onboarding"):  # E4: new learners only
        _, v = expose("onboarding_flow", uid, traits)
        seen.append(("onboarding_flow", v))
        fire("onboarding_flow", v, "onboarding_completed")
        fire("onboarding_flow", v, "onboarding_skipped")

    if hit("lesson"):  # E2 lesson_length
        _, raw = expose("lesson_length", uid, traits)
        arm = flags.lesson_arm(flags.parse_lesson_length(raw))
        seen.append(("lesson_length", arm))
        emit("lesson_started", uid, None, traits)
        fire("lesson_length", arm, "lesson_completed", flags.parse_lesson_length(raw)["minutes"])

    if hit("quiz"):  # E3 quiz_timer
        _, v = expose("quiz_timer", uid, traits)
        v = str(v)
        seen.append(("quiz_timer", v))
        fire("quiz_timer", v, "quiz_passed")
        fire("quiz_timer", v, "quiz_abandoned")

    if hit("help"):  # E6 help_widget (lower is better)
        _, v = expose("help_widget", uid, traits)
        seen.append(("help_widget", str(v)))
        fire("help_widget", str(v), "support_ticket_opened")

    if hit("pricing"):  # E1 pricing_layout
        _, v = expose("pricing_layout", uid, traits)
        seen.append(("pricing_layout", v))
        if rng.random() < _p("pricing_layout", v, "subscription_started"):
            avg = knobs.outcome_table("pricing_layout", v)["revenue_avg"]
            emit("subscription_started", uid, None, traits)
            emit("revenue", uid, round(max(1.0, rng.gauss(avg, avg * 0.25)), 2), traits)

    # Non-experiment flags are evaluated too so segments / overrides / kill switch show up in Flagsmith analytics.
    for name in ("maintenance_mode", "beta_exam_mode", "support_chat", "daily_goal_xp", "ai_tutor", "legacy_leaderboard"):
        plain(name, uid, traits)
    return seen


def run(users: int, dry_run: bool = False) -> dict:
    rng = random.Random(knobs.SEED)
    tally: dict[str, Counter] = defaultdict(Counter)
    if dry_run:
        # Fake an even 3-way split so the knob table is exercised without network.
        def fake_expose(name, uid, traits=None):
            arms = list(knobs.EXPERIMENTS[name])
            arm = rng.choice(arms)
            if name == "lesson_length":
                arm = '{"minutes": %s, "cards": 8}' % arm.removesuffix("min")
            return True, arm
        expose, emit, plain = fake_expose, (lambda *a, **k: None), (lambda *a, **k: None)
    else:
        expose, emit, plain = flags.experiment, flags.track, flags.flag

    for i in range(users):
        for exp, arm in simulate_user(rng, emit=emit, expose=expose, plain=plain):
            tally[exp][arm] += 1
        if not dry_run and i % 100 == 99:
            flags.flush()
    if not dry_run:
        flags.flush()
    return {k: dict(v) for k, v in tally.items()}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=knobs.SIM_USERS)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not args.dry_run and flags.client() is None:
        raise SystemExit("No environment key: fill flagsmith.json or set FLAGSMITH_ENVIRONMENT_KEY.")
    print(f"simulating {args.users} users (dry_run={args.dry_run}) ...")
    for exp, arms in run(args.users, args.dry_run).items():
        print(f"  {exp:16s} exposures per arm: {arms}")
    print("done. Events can take a few minutes to appear in the console; hit Recompute on the experiment.")
