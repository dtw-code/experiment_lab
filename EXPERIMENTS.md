# The five experiments — what to look at, and where

Five running experiments in Flagsmith **project 56888 / Development (121707)**, one for each verdict
the guardian can reach. Every one of them is visible in the app: open the page, read the arm off the
screen, click the button that records the metric.

Live on 2026-11-28 from ~3,060 simulated learners. Verdicts below are what
`guardian verdicts --live --detail` actually returned, not predictions.

| # | Exp | Flag | Page | Control → Variant_1 | Metric (aggregation) | Verdict | Guardian does |
|---|-----|------|------|---------------------|----------------------|---------|---------------|
| E1 | 1724 | `pricing_layout` | **Pricing** | `monthly_first` → `annual_first` | `subscription_started` (occurrence, up) | **WINNER** | `create_rollout_proposal` |
| E2 | 1725 | `quiz_timer` | **Quiz** | `none` → `30` | `quiz_passed` (occurrence, up) | **HARMFUL_VARIANT** | `create_rollback_proposal` |
| E3 | 1726 | `help_widget` | **Lesson** | `link` → `chat_hint` | `support_ticket_opened` (occurrence, **down**) | **SYSTEMIC_FAILURE** | `notify_only`, HIGH + alert |
| E4 | 1727 | `lesson_loading` | **Lesson** | `eager` → `prefetch` | `lesson_load_ms` (**mean**, down) | **SEVERE_HARM** | `create_rollback_proposal`, HIGH |
| E5 | 1728 | `streak_reminder` | **Home** | `none` → `gentle` | `daily_return` + `streak_continued` (occurrence, up) | **INCONCLUSIVE** | `record_no_decision` |

Five metrics are **occurrence**; `lesson_load_ms` is the one **mean/aggregate** metric — the event
carries a numeric millisecond value and Flagsmith averages it.

---

## How to watch one

```powershell
py -m streamlit run app.py
```

In the sidebar, type a **User ID** and pick a **Page**. Each ID is bucketed independently, so change
the ID until you get the arm you want; the arm you were served is always printed at the bottom under
**Debug: resolved experiment arms**. The button on the page is what records the metric.

---

## E1 `pricing_layout` → WINNER

**Page: Pricing.** Both arms offer the same two plans; only the order changes.

| Arm | What you see |
|---|---|
| `monthly_first` (control) | `Subscribe - Monthly: $9` first, then `Subscribe - Annual: $79` |
| `annual_first` (Variant_1) | `Subscribe - Annual (save 27%): $79` first, then Monthly |

Clicking either button records `subscription_started`.

**Live numbers:** 19.36% → 33.21%, lift **+71.5%**, interval [+48.3%, +94.8%], win probability
**1.000**. Both halves of the winner rule are satisfied — probability ≥ 0.95 *and* the interval stays
above zero — so the guardian proposes a rollout to `Variant_1`.

## E2 `quiz_timer` → HARMFUL_VARIANT

**Page: Quiz.** The caption under the heading is the whole difference.

| Arm | What you see |
|---|---|
| `none` (control) | `Untimed` |
| `30` (Variant_1) | `⏱️ 30s timer` |

Answer `3` (the correct answer) and press **Submit** to record `quiz_passed`.

**Live numbers:** 50.27% → 43.18%, lift **−14.1%**, interval [−21.1%, −7.0%], win probability
**0.000**. Clearly worse — but a **14.1%** worsening is under the **25%** bar
(`severe_min_relative_worsening`), so it is *harmful*, not *severe*. This is the pair to compare with
E4: same gates, same thresholds, only the size of the damage differs.

## E3 `help_widget` → SYSTEMIC_FAILURE

**Page: Lesson**, below the divider.

| Arm | What you see |
|---|---|
| `link` (control) | just the `Contact support` button |
| `chat_hint` (Variant_1) | `💡 Stuck? Try rereading card 3 before asking for help.` above the button |

**Contact support** records `support_ticket_opened`.

**Live numbers:** 22.79% → 21.37%. The variant is *slightly better*, and it changes nothing — because
`support_ticket_opened` is declared a `failure_rate` with an **absolute ceiling of 0.05** in the
guardian's `policy.yaml`, and the ceiling is compared against the **Wilson lower bound**. Control's
bound is **0.2060**, four times the ceiling. The *control itself* is broken, so the guardian says
"a rollback would not help", raises an **alert** at **HIGH** priority and routes to `notify_only`
instead of proposing anything.

This is the one experiment whose verdict comes from a rung *above* harm and winner, which is why a
better-looking variant cannot override it.

## E4 `lesson_loading` → SEVERE_HARM — the mean metric

**Page: Lesson**, the caption above **Start lesson**.

| Arm | What you see | Load time recorded |
|---|---|---|
| `eager` (control) | `Content loading: eager` | ~1,500 ms |
| `prefetch` (Variant_1) | `Content loading: prefetch` | ~2,400 ms |

**Start lesson** records `lesson_load_ms` **with that number as the event value**. In the Flagsmith
console this metric shows as `Mean`, direction *lower is better* — the only non-rate metric in the lab.

**Live numbers:** **1,501 ms → 2,384 ms**, lift **+58.8%**, interval [+55.8%, +61.8%], win probability
**0.000**. A 58.8% worsening is well past the 25% bar and the interval is nowhere near zero, so this
is **SEVERE_HARM**: rollback proposal at **HIGH** priority.

Worth noticing: the guardian reads this through a different interval entirely. For an occurrence
metric it uses a Wilson interval on a rate in [0,1]; here the value is unbounded milliseconds, so it
reads the spread out of `sum_squares` instead (`guardian/aggregates.py`). Same ladder, same
thresholds, different arithmetic — `wilson_low_arm` is deliberately `null` on these rows.

## E5 `streak_reminder` → INCONCLUSIVE

**Page: Home**, under **Today**.

| Arm | What you see |
|---|---|
| `none` (control) | just the two buttons |
| `gentle` (Variant_1) | `🌱 Nice 5-day streak. A five-minute lesson keeps it growing.` |

`I'll come back tomorrow` records `daily_return`; `Keep the streak alive` records `streak_continued`.

**Live numbers:** `daily_return` 29.75% → 30.77% (win 0.727); `streak_continued` 40.43% → 40.22%
(win 0.453). Nothing clears either bar.

It is inconclusive for **two** independent reasons, and that is on purpose:

1. **No primary metric can be inferred.** The experiment declares *two* goal metrics, and with more
   than one the guardian refuses to choose for you — `policy.yaml` deliberately has **no**
   `primary_metric_map` entry for 1728, so the verdict carries `no_primary_metric` and no winner can
   ever be promoted, however the numbers move.
2. **The effects are genuinely too small** anyway (+3.4% and −0.5%), nowhere near a 0.95 win
   probability and nowhere near the harm threshold either.

Add `"1728": "1771"` to `primary_metric_map` and metric 1771 becomes a winner candidate — that single
line is the difference between "no decision" and "a decision is possible".

---

## The six plain flags (not experiments)

These exist so the guardian's other paths have something to act on. None of them is part of an
experiment, so none is removed when one ends.

| Flag | Default | Where it shows | What it is for |
|---|---|---|---|
| `maintenance_mode` | off | whole app | kill switch — turn it on and the app stops at an error |
| `support_chat` | off | sidebar | identity override (`vip-learner`) |
| `beta_exam_mode` | off | Quiz | segment override (`pro_users`) |
| `daily_goal_xp` | `20` | Home metric | remote config, with a `power_users` value override |
| `ai_tutor` | `off` | Lesson | staged % rollout that is **not** an experiment |
| `legacy_leaderboard` | on | Home | stale fully-rolled-out flag — a `guardian cleanup` candidate with no experiment behind it |

---

## Regenerating the data

```powershell
py -m learnloop.sim --users 3000
```

```powershell
cd C:\Users\KIIT\Desktop\AI_Proj\Flagsmith; .venv\Scripts\python.exe -m guardian refresh 1724 1725 1726 1727 1728
```

```powershell
cd C:\Users\KIIT\Desktop\AI_Proj\Flagsmith; $env:RESULTS_SOURCE="mcp"; .venv\Scripts\python.exe -m guardian verdicts --live --detail
```

Events reach Flagsmith's warehouse a few minutes after a run, and results older than 30 minutes read
`DATA_UNTRUSTED` on purpose — hence the `refresh` step. 3,000 learners is the calibrated size:
`learnloop/knobs.py` explains which margin each number protects, and E2 is the one that loses
significance first if you run fewer.

## Changing who wins

Everything is in `learnloop/knobs.py`, and every number there has a test guarding the verdict it
produces (`tests/test_exp_*.py`). Widen E2's gap past 25% and `test_the_variant_is_worse_but_not_severely`
fails rather than the demo quietly turning into SEVERE_HARM.
