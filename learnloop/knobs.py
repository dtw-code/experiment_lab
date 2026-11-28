"""THE TWEAK FILE. These numbers decide which verdict the guardian reaches; nothing else has to change.

Each experiment maps an arm (= the flag VALUE Flagsmith serves) to the probability, or the average
value, that the simulator feeds its metric events. An unknown arm falls back to the first (control)
entry, so the app is safe before the flags exist.

The five sets below are calibrated, not arbitrary. The guardian's ladder
(`guardian/stats.py`, thresholds in `policy.yaml`) reads them like this:

    verdict           what the numbers have to do
    ---------------   --------------------------------------------------------------------------
    WINNER            win probability >= 0.95 AND the confidence interval stays above zero
    HARMFUL_VARIANT   win probability <= 0.05, worsening under 25% and no ceiling breached
    SEVERE_HARM       win probability <= 0.05, interval below zero, worsening of 25% or more
    SYSTEMIC_FAILURE  CONTROL's own lower bound breaches the metric's absolute ceiling
    INCONCLUSIVE      nothing clears either bar (and here: no primary metric is named either)

So the margins matter more than the absolute levels. `MIN_USERS_FOR_VERDICTS` is the sample size
these margins were sized for - below it the harm verdict loses significance and reads INCONCLUSIVE.
"""

SIM_USERS = 3000           # users per simulator run (the CLI and the Simulator page both default to this)
MIN_USERS_FOR_VERDICTS = 3000
SEED = 7                   # seeds the OUTCOME randomness only; user ids are always fresh so Flagsmith re-buckets
GLOBAL_LIFT = 1.0          # multiplies every higher-is-better probability (1.0 = off). 0.5 = a bad day
GUARDRAIL_FACTOR = 1.0     # multiplies every lower-is-better probability

# Chance a simulated learner reaches the page that hosts an experiment; exposure is only recorded
# there. Kept high on purpose: each arm needs ~1,200 identities for E2 to stay significant.
PAGE_VISIT_RATE = {"home": 1.0, "pricing": 0.85, "lesson": 0.9, "quiz": 0.85, "help": 0.85}

# Metrics where LOWER is better. The simulator applies GUARDRAIL_FACTOR to these.
LOWER_IS_BETTER = {"support_ticket_opened"}

EXPERIMENTS = {
    # E1 pricing_layout -> WINNER. Primary: subscription_started (occurrence, up).
    # 0.20 -> 0.32 is a +60% relative lift; at ~1,250 per arm the interval sits well clear of zero.
    "pricing_layout": {
        "monthly_first": {"subscription_started": 0.20},   # control
        "annual_first": {"subscription_started": 0.32},    # the winner
    },
    # E3 help_widget -> SYSTEMIC_FAILURE. Primary: support_ticket_opened (occurrence, DOWN), declared
    # a failure_rate with abs_ceiling 0.05. Both arms sit near 0.21, so CONTROL breaches the ceiling
    # too and a rollback would not help - which is exactly what SYSTEMIC_FAILURE means.
    "help_widget": {
        "link": {"support_ticket_opened": 0.22},           # control, already over the ceiling
        "chat_hint": {"support_ticket_opened": 0.21},      # no real change
    },
    # E4 lesson_loading -> SEVERE_HARM, and the one MEAN metric in the lab.
    # Primary: lesson_load_ms (mean of a numeric event value, DOWN). 1500 -> 2400 ms is a 60%
    # worsening, far past the 25% bar, with an interval nowhere near zero.
    "lesson_loading": {
        "eager": {"lesson_load_ms_avg": 1500},             # control
        "prefetch": {"lesson_load_ms_avg": 2400},          # severely slower
    },
    # E5 streak_reminder -> INCONCLUSIVE. Two goal metrics, daily_return and streak_continued, and
    # policy.yaml deliberately names NEITHER as primary. The lifts are also genuinely small (+5% and
    # +3%), so even with a primary named this would not clear 0.95.
    "streak_reminder": {
        "none": {"daily_return": 0.300, "streak_continued": 0.400},     # control
        "gentle": {"daily_return": 0.315, "streak_continued": 0.412},   # a nudge, barely
    },
}

LOAD_TIME_SPREAD = 0.25    # load time standard deviation as a share of the arm's average


def outcome_table(experiment: str, arm: str) -> dict:
    """Metric table for an arm; an unknown arm falls back to the first (control) entry."""
    arms = EXPERIMENTS[experiment]
    return arms.get(arm) or next(iter(arms.values()))


def probability(experiment: str, arm: str, metric: str) -> float:
    """The arm's probability for `metric`, after the two global multipliers."""
    p = outcome_table(experiment, arm).get(metric, 0.0)
    factor = GUARDRAIL_FACTOR if metric in LOWER_IS_BETTER else GLOBAL_LIFT
    return min(1.0, p * factor)
