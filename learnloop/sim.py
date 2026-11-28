"""Headless learner simulator: the traffic that drives the five experiments to a verdict.

    py -m learnloop.sim                      # knobs.SIM_USERS learners
    py -m learnloop.sim --users 3000
    py -m learnloop.sim --dry-run            # no network: prints the arm split the knobs would feed
    py -m learnloop.sim --workers 16         # parallel identities (default 12)

Each learner costs ONE identity request: `flags.resolve_identity` resolves every flag in one call and
`flags.arm_of` records the exposure per experiment, which is what the SDK's `get_experiment_flag`
does internally. Conversion events are buffered and flushed in batches.

Flagsmith computes experiment results from a warehouse, not from the request, so events take a few
minutes to land. Recompute the experiment in the console, or run `guardian refresh <id>`, afterwards.
"""
from __future__ import annotations

import argparse
import random
import uuid
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor

from . import experiments, flags, knobs


def make_traits(rng: random.Random) -> dict:
    return {
        "plan": rng.choices(["free", "pro", "enterprise"], [70, 25, 5])[0],
        "country": rng.choice(["IN", "US", "UK", "DE"]),
        "days_since_signup": rng.randint(0, 400),
        "streak_days": rng.choice([0, 1, 3, 7, 14, 30, 45]),
    }


def simulate_learner(rng: random.Random, *, resolve=flags.resolve_identity, arm_of=flags.arm_of,
                     emit=flags.track_event) -> list[tuple[str, str]]:
    """One learner session. Returns [(flag, arm)] exposures and emits that arm's metric events."""
    uid = f"sim-{uuid.uuid4()}"
    traits = make_traits(rng)
    resolved = resolve(uid, traits)
    seen: list[tuple[str, str]] = []

    def visit(page: str) -> bool:
        return rng.random() < knobs.PAGE_VISIT_RATE[page]

    def fire(flag: str, arm: str, metric: str, value=None) -> None:
        if rng.random() < knobs.probability(flag, arm, metric):
            emit(metric, uid, value, traits)

    if visit("home"):                                       # E5 streak_reminder
        arm = arm_of(resolved, "streak_reminder", uid, traits)
        if arm is not None:
            seen.append(("streak_reminder", str(arm)))
            fire("streak_reminder", str(arm), "daily_return")
            fire("streak_reminder", str(arm), "streak_continued")

    if visit("lesson"):                                     # E4 lesson_loading (the mean metric)
        arm = arm_of(resolved, "lesson_loading", uid, traits)
        if arm is not None:
            seen.append(("lesson_loading", str(arm)))
            emit("lesson_load_ms", uid, experiments.lesson_loading_ms(arm, rng), traits)

    if visit("help"):                                       # E3 help_widget
        arm = arm_of(resolved, "help_widget", uid, traits)
        if arm is not None:
            seen.append(("help_widget", str(arm)))
            fire("help_widget", str(arm), "support_ticket_opened")

    if visit("pricing"):                                    # E1 pricing_layout
        arm = arm_of(resolved, "pricing_layout", uid, traits)
        if arm is not None:
            seen.append(("pricing_layout", str(arm)))
            fire("pricing_layout", str(arm), "subscription_started")

    return seen


def _fake_resolve(uid, traits=None):
    return None


def _even_split(rng: random.Random):
    """Stand-in for Flagsmith that hands out arms 50/50, for --dry-run."""
    def arm_of(resolved, name, uid, traits=None):
        return rng.choice(list(knobs.EXPERIMENTS[name]))
    return arm_of


def run(users: int, dry_run: bool = False, workers: int = 12) -> dict:
    rng = random.Random(knobs.SEED)
    tally: dict[str, Counter] = defaultdict(Counter)
    if dry_run:
        for _ in range(users):
            for flag, arm in simulate_learner(rng, resolve=_fake_resolve, arm_of=_even_split(rng),
                                              emit=lambda *a, **k: None):
                tally[flag][arm] += 1
        return {k: dict(v) for k, v in tally.items()}

    seeds = [random.Random(knobs.SEED + i) for i in range(users)]
    done = 0
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        for seen in pool.map(simulate_learner, seeds):
            for flag, arm in seen:
                tally[flag][arm] += 1
            done += 1
            if done % 250 == 0:
                flags.flush()
                print(f"  {done}/{users} learners", flush=True)
    flags.flush()
    return {k: dict(v) for k, v in tally.items()}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--users", type=int, default=knobs.SIM_USERS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--workers", type=int, default=12)
    args = ap.parse_args(argv)
    if not args.dry_run and flags.client() is None:
        print("No environment key: fill flagsmith.json or set FLAGSMITH_ENVIRONMENT_KEY.")
        return 2
    if args.users < knobs.MIN_USERS_FOR_VERDICTS and not args.dry_run:
        print(f"note: {args.users} learners is below the {knobs.MIN_USERS_FOR_VERDICTS} the knobs are "
              f"calibrated for; the HARMFUL_VARIANT margin may not reach significance.")
    print(f"simulating {args.users} learners (dry_run={args.dry_run}, workers={args.workers}) ...")
    for flag, arms in run(args.users, args.dry_run, args.workers).items():
        print(f"  {flag:16s} exposures per arm: {dict(sorted(arms.items()))}")
    print("done. Events land in the warehouse within a few minutes; recompute the experiment "
          "in the console or run `guardian refresh <experiment id>`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
