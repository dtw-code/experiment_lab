# LearnLoop - console setup (copy these values exactly)

Flag **names, values and event names are case-sensitive and must match the code.** Menu wording may differ slightly
by Flagsmith version; the values are what matter.

## 0. Point the app at your environment
Create the new project in Flagsmith, copy its **client-side environment key**, then either edit `flagsmith.json`
(`"environment": "<key>"`) or set `FLAGSMITH_ENVIRONMENT_KEY`. (It currently holds the key of the old payment project.)
Until a flag exists the app serves its built-in default and sends no exposure, so create things in any order.

## 1. Segments (project level)
| Segment | Rule(s) | Used by |
|---|---|---|
| `pro_users` | trait `plan` **is in** `pro,enterprise` (or two rules, match ANY: `plan = pro`, `plan = enterprise`) | `beta_exam_mode` |
| `new_learners` | trait `days_since_signup` **<=** `7` | `onboarding_flow` audience, plain-flag demo |
| `power_users` | trait `streak_days` **>=** `30` | `daily_goal_xp` |

## 2. Plain (non-experiment) flags
| Flag | Enabled | Value | Extra setup | What it proves |
|---|---|---|---|---|
| `maintenance_mode` | off | - | none | Kill switch. Turn ON -> whole app shows "down for maintenance". |
| `beta_exam_mode` | off | - | Segment override `pro_users` -> **enabled** | Segment targeting. Sidebar plan=pro shows the beta banner on Quiz. |
| `support_chat` | off | - | **Identity override**: identity `vip-learner` -> enabled (create the identity by opening the app once with that User ID) | Identity override. |
| `daily_goal_xp` | on | `20` | Segment override `power_users` -> value `50` | Remote config + segment value override. |
| `ai_tutor` | on | `off` | Multivariate: add value `on` with weight **10%** (remaining 90% stays `off`) | Staged % rollout that is **not** an experiment. |
| `legacy_leaderboard` | on | - | Tag it `stale`; leave on for 100% everywhere | Stale fully-rolled-out flag -> `guardian cleanup` candidate. |

## 3. Experiment flags (create all as **enabled**, multivariate)
| Flag | Control value (flag default) | Variation values | Weights | Type of value |
|---|---|---|---|---|
| `pricing_layout` | `monthly_first` | `annual_first`, `three_tier` | 34 / 33 / 33 | string, 3 arms |
| `lesson_length` | `{"minutes": 10, "cards": 8}` | `{"minutes": 5, "cards": 4}` | 50 / 50 | JSON remote config |
| `quiz_timer` | `none` | `60`, `30` | 34 / 33 / 33 | numeric as string |
| `onboarding_flow` | `classic` | `checklist` | 50 / 50 | string; audience = segment `new_learners` if the experiment lets you pick one (the app only ever exposes new learners anyway) |
| `streak_reminder` | `none` | `gentle`, `urgent` | 34 / 33 / 33 | string copy test |

## 4. Metrics (events sent with `track_event`)
| Event name | Meaning | Aggregation | Good direction | Notes |
|---|---|---|---|---|
| `subscription_started` | upgraded to Pro | Occurrence | up | |
| `revenue` | order value, numeric event `value` | **Mean** (average order value; Sum also works) | up | send by the same users as above |
| `lesson_started` | opened a lesson | Occurrence | up | denominator-style / secondary |
| `lesson_completed` | finished (value = minutes) | Occurrence | up | |
| `quiz_passed` | passed quiz | Occurrence | up | |
| `quiz_abandoned` | gave up | Occurrence | **down** (guardrail) | |
| `onboarding_completed` | finished onboarding | Occurrence | up | |
| `onboarding_skipped` | skipped onboarding | Occurrence | **down** (guardrail) | |
| `daily_return` | came back next day | Occurrence | up | |
| `reminder_opt_out` | turned reminders off | Occurrence | **down** (guardrail) | |

## 5. Experiments
| # | Experiment (flag) | Hypothesis | Primary | Secondary | Guardrail | With default knobs | Guardian scenario |
|---|---|---|---|---|---|---|---|
| 1 | `pricing_layout` | Showing annual first lifts upgrades | `subscription_started` | `revenue` | - | `annual_first` wins clearly; `three_tier` ties on conversion but wins on revenue | clear winner -> ship; secondary-metric tension |
| 2 | `lesson_length` | 5-min lessons finish more | `lesson_completed` | `lesson_started` | - | `5min` small win (0.62 vs 0.55), borderline at ~600 users | needs-more-data / low-power |
| 3 | `quiz_timer` | A timer raises pass rate | `quiz_passed` | - | `quiz_abandoned` | `60` ties, `30` is worse on both | losing arm, harmful variant -> rollback |
| 4 | `onboarding_flow` | Checklist beats the classic tour | `onboarding_completed` | - | `onboarding_skipped` | `checklist` wins, fewer skips | segment-scoped experiment, small N (~40% of users) |
| 5 | `streak_reminder` | Urgent copy brings users back | `daily_return` | - | `reminder_opt_out` | `urgent` wins primary but breaches the guardrail | win-with-guardrail-breach -> must NOT auto-ship |

Suggested run: 1 clean, 3 plain from the start, plus run #5 and #3 longest. For a sample-size check run the
simulator with `--users 150` (underpowered) then `--users 2000`.

## 6. Generate data
```powershell
py -m learnloop.sim --dry-run          # no network: shows exposures per arm
py -m learnloop.sim --users 600        # real events into your environment
py -m streamlit run app.py             # hand-test; Simulator page does the same as the CLI
```
Events can lag a few minutes; recompute the experiment results in the console after a run.

## 7. Tweaking who wins - `learnloop/knobs.py`
* Make `three_tier` the winner: set its `subscription_started` to `0.16`.
* A/A test (no true difference): make every arm of one experiment identical.
* Bad day for everything: `GLOBAL_LIFT = 0.5`. Raise guardrails: `GUARDRAIL_FACTOR = 2.0`.
* Fewer users (underpowered): `SIM_USERS = 150`.
* Variant keys in `knobs.py` must equal the flag values above (`lesson_length` arms are `10min` / `5min` = the JSON `minutes`).

## 8. Guardian tests worth doing
* Kill switch: flip `maintenance_mode` and confirm the guardian reports/handles it.
* End an experiment (e.g. #3, roll back to control) -> `guardian cleanup` should remove the `quiz_timer` branch in `app.py` and the `learnloop` helper `parse_quiz_timer` usage while leaving `track(` calls alone.
* `legacy_leaderboard` is a plain stale flag: cleanup without any experiment.
* Change a metric name in the console (typo) -> the guardian should notice zero events.
