"""THE TWEAK FILE. Edit numbers here to make a variant win, lose or tie; nothing else needs to change.

Each experiment maps a variant (= the flag VALUE served by Flagsmith) to the probabilities/values the simulator
(and the buttons in the web UI) use when emitting metric events. Unknown variant values fall back to the first
(control) entry.

Quick recipes
  * variant clearly wins ........ raise its primary metric (e.g. annual_first subscription_started 0.08 -> 0.14)
  * no real difference (A/A) .... give every variant identical numbers
  * wins but hurts a guardrail .. raise primary AND its guardrail (streak_reminder "urgent" is set up this way)
  * inconclusive / underpowered .. keep the lift tiny (0.08 vs 0.085) and SIM_USERS small
"""

SIM_USERS = 600            # users per simulator run (Streamlit page and `python -m learnloop.sim` both default to this)
SEED = 7                   # seeds the OUTCOME randomness only; user ids are always fresh so Flagsmith re-buckets
GLOBAL_LIFT = 1.0          # multiplies every positive metric probability (1.0 = off). 0.5 = a bad day for everything
GUARDRAIL_FACTOR = 1.0     # multiplies every guardrail probability (reminder_opt_out, quiz_abandoned, onboarding_skipped)

# Chance a simulated user reaches the page hosting an experiment (exposure is only recorded on that page).
PAGE_VISIT_RATE = {"home": 1.0, "pricing": 0.6, "lesson": 0.8, "quiz": 0.7, "onboarding": 1.0, "help": 0.5}

# Share of simulated users who are "new learners" (the onboarding experiment only exposes these).
NEW_LEARNER_SHARE = 0.4

# Metrics where LOWER is better. Used by the simulator only to apply GUARDRAIL_FACTOR.
GUARDRAIL_METRICS = {"quiz_abandoned", "onboarding_skipped", "reminder_opt_out", "support_ticket_opened"}

EXPERIMENTS = {
    # E1 pricing_layout (string, 3 arms). Primary: subscription_started. Secondary: revenue (numeric event value).
    "pricing_layout": {
        "monthly_first": {"subscription_started": 0.08, "revenue_avg": 9.0},     # control
        "annual_first":  {"subscription_started": 0.14, "revenue_avg": 14.0},    # clear winner
        "three_tier":    {"subscription_started": 0.08, "revenue_avg": 11.0},    # ties on conversion, wins on revenue
    },
    # E2 lesson_length (JSON remote config). Primary: lesson_completed (denominator: lesson_started).
    # Control = the arm whose flag value has "minutes": 10; the arm key is derived from minutes, see sim.arm_key().
    "lesson_length": {
        "10min": {"lesson_completed": 0.55},   # control
        "5min":  {"lesson_completed": 0.62},   # small win, only significant with ~600+ users
    },
    # E3 quiz_timer (numeric-as-string). Primary: quiz_passed. Guardrail: quiz_abandoned (lower is better).
    "quiz_timer": {
        "none": {"quiz_passed": 0.50, "quiz_abandoned": 0.15},
        "60":   {"quiz_passed": 0.50, "quiz_abandoned": 0.16},   # ~tie
        "30":   {"quiz_passed": 0.42, "quiz_abandoned": 0.30},   # clearly worse on both
    },
    # E4 onboarding_flow (new learners only). Primary: onboarding_completed. Guardrail: onboarding_skipped.
    "onboarding_flow": {
        "classic":   {"onboarding_completed": 0.45, "onboarding_skipped": 0.30},
        "checklist": {"onboarding_completed": 0.58, "onboarding_skipped": 0.18},
    },
    # E5 streak_reminder (copy). Primary: daily_return. Guardrail: reminder_opt_out.
    # "urgent" WINS the primary but trips the guardrail -> the guardian should not ship it blindly.
    "streak_reminder": {
        "none":   {"daily_return": 0.30, "reminder_opt_out": 0.00},
        "gentle": {"daily_return": 0.36, "reminder_opt_out": 0.03},
        "urgent": {"daily_return": 0.44, "reminder_opt_out": 0.14},
    },
    # E6 help_widget (Lesson page help area). Primary: support_ticket_opened - LOWER IS BETTER.
    "help_widget": {
        "link":       {"support_ticket_opened": 0.20},   # control: plain "contact support" link
        "inline_faq": {"support_ticket_opened": 0.12},   # inline FAQ deflects tickets (the winner = the lower number)
        "chat_hint":  {"support_ticket_opened": 0.21},   # no real change
    },
}


def outcome_table(experiment: str, arm: str) -> dict:
    """Metric table for an arm; unknown arms fall back to the first (control) entry."""
    arms = EXPERIMENTS[experiment]
    return arms.get(arm) or next(iter(arms.values()))
