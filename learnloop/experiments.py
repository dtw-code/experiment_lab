"""What each experiment arm actually changes, as pure functions.

One block per flag, in the order the experiments are numbered. Every block is self-contained: the
flag name appears only inside its own block, so `guardian cleanup` can delete a block and its tests
without the edit reaching past the lines that flag occupies (`window_lines` in cleanup.yaml).

Nothing here reads a flag or sends an event. `app.py` reads the flag and passes the arm in;
`learnloop/sim.py` does the same headlessly. That is what makes every arm testable with no network.
"""
from __future__ import annotations

import random

from . import knobs

# --- E1 pricing_layout -- WINNER -------------------------------------------------------------------
# Control `monthly_first` shows the monthly plan first; `annual_first` leads with the annual plan.
# Conversion event: subscription_started (occurrence, higher is better).
PRICING_LAYOUTS = {
    "monthly_first": [("Monthly", 9), ("Annual", 79)],
    "annual_first": [("Annual (save 27%)", 79), ("Monthly", 9)],
}


def pricing_layout_tiers(arm) -> list[tuple[str, int]]:
    """The plan buttons, in the order this arm shows them. An unknown arm falls back to control."""
    return PRICING_LAYOUTS.get(str(arm), PRICING_LAYOUTS["monthly_first"])


# --- E2 quiz_timer -- HARMFUL_VARIANT --------------------------------------------------------------
# Control `none` is untimed; `30` puts a 30-second countdown on every question.
# Conversion event: quiz_passed (occurrence, higher is better).

def quiz_timer_seconds(arm) -> int | None:
    """Seconds on the clock, or None for untimed. Accepts 'none', '', '30', 30."""
    try:
        seconds = int(str(arm).strip())
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


# --- E3 help_widget -- SYSTEMIC_FAILURE ------------------------------------------------------------
# Control `link` is a plain "Contact support" link; `chat_hint` adds a nudge to reread the lesson.
# Conversion event: support_ticket_opened (occurrence, LOWER is better, and it has an absolute
# ceiling in the guardian's policy: both arms breach it, which is the point of this experiment).
HELP_WIDGET_HINTS = {
    "chat_hint": "Stuck? Try rereading card 3 before asking for help.",
}


def help_widget_hint(arm) -> str | None:
    """The extra self-service hint this arm shows above the support link, or None for control."""
    return HELP_WIDGET_HINTS.get(str(arm))


# --- E4 lesson_loading -- SEVERE_HARM, on the MEAN metric ------------------------------------------
# Control `eager` loads every card up front; `prefetch` also warms the NEXT lesson, which makes this
# one noticeably slower. Conversion event: lesson_load_ms (MEAN of a numeric value, LOWER is better).

def lesson_loading_ms(arm, rng: random.Random | None = None) -> int:
    """One learner's load time in ms: the arm's average, jittered, never below 100."""
    avg = knobs.outcome_table("lesson_loading", str(arm))["lesson_load_ms_avg"]
    if rng is None:
        return int(avg)
    return max(100, round(rng.gauss(avg, avg * knobs.LOAD_TIME_SPREAD)))


# --- E5 streak_reminder -- INCONCLUSIVE ------------------------------------------------------------
# Control `none` shows nothing; `gentle` shows an encouraging nudge. The effect is real but tiny, and
# the experiment carries TWO goal metrics with neither named primary in the guardian's policy, so no
# winner can be promoted from it. Conversion events: daily_return, streak_continued (both
# occurrence, higher is better).
STREAK_REMINDER_COPY = {
    "gentle": "Nice {days}-day streak. A five-minute lesson keeps it growing.",
}


def streak_reminder_copy(arm, streak_days: int) -> str | None:
    """The nudge this arm shows on Home, or None for control."""
    template = STREAK_REMINDER_COPY.get(str(arm))
    return template.format(days=streak_days) if template else None
