# LearnLoop — console setup

**Everything in this file already exists** in project **56888 / Development (121707)**, created on
2026-11-28 by `spikes/seed_lab.py` in the guardian repo. This is the record of what was created and
how to recreate it, not a to-do list. What each experiment *does*, and the verdict it reaches:
[EXPERIMENTS.md](EXPERIMENTS.md).

Flag **names, values and event names are case-sensitive and must match the code**
(`learnloop/flags.py` and `learnloop/knobs.py`).

## 0. Point the app at the environment

`flagsmith.json` holds the client-side environment key (`"environment"`), or set
`FLAGSMITH_ENVIRONMENT_KEY` to override it. Until a flag exists the app serves its built-in control
default and sends no exposure, so order of creation never matters.

## 1. Experiment flags (all **enabled**, **MULTIVARIATE**, control + one variant at 50/50)

The flag's **default value is the control arm**; the multivariate option is `Variant_1`.

| Flag | id | Control (flag default) | `Variant_1` | Exp |
|---|---|---|---|---|
| `pricing_layout` | 308281 | `monthly_first` | `annual_first` | 1724 |
| `quiz_timer` | 308282 | `none` | `30` | 1725 |
| `help_widget` | 308283 | `link` | `chat_hint` | 1726 |
| `lesson_loading` | 308284 | `eager` | `prefetch` | 1727 |
| `streak_reminder` | 308285 | `none` | `gentle` | 1728 |

> **The variant's `key` matters.** `create_feature` accepts `multivariate_options[].key` and silently
> stores `null`; `update_feature_multivariate_option` does set it. A null key means the SDK sends **no
> exposure at all** (`get_experiment_flag` requires `flag.variant`), so the experiment collects
> nothing. `seed_lab.py` sets the keys in a second pass for exactly this reason.

## 2. Metrics

Five **occurrence**, one **mean**. The event name is the metric's `definition.event`, which is what
`flags.track_event(...)` sends — not the display name.

| Metric | id | Event | Aggregation | Direction | Used by |
|---|---|---|---|---|---|
| `subscription_started` | 1767 | `subscription_started` | Occurrence | up | E1 |
| `quiz_passed` | 1768 | `quiz_passed` | Occurrence | up | E2 |
| `support_ticket_opened` | 1769 | `support_ticket_opened` | Occurrence | **down** | E3 |
| `lesson_load_ms` | 1770 | `lesson_load_ms` | **Mean** | **down** | E4 |
| `daily_return` | 1771 | `daily_return` | Occurrence | up | E5 |
| `streak_continued` | 1772 | `streak_continued` | Occurrence | up | E5 |

`lesson_load_ms` is the only metric whose events carry a numeric `value` (milliseconds). The MCP
`create_metric` tool does **not** declare `definition`, so it is stripped and the API answers
`400 definition: This field is required` — metrics have to be created through
`POST /api/v1/environments/{env_key}/experiment-metrics/`.

## 3. Experiments

Each is `MULTIVARIATE`, rollout 100%, `Variant_1` at 50% (control takes the rest), no audience
segment, status **running**.

| Exp | id | Flag | Metric(s) | `expected_direction` |
|---|---|---|---|---|
| E1 pricing layout | 1724 | `pricing_layout` | 1767 | `increase` |
| E2 quiz timer | 1725 | `quiz_timer` | 1768 | `increase` |
| E3 help widget | 1726 | `help_widget` | 1769 | `decrease` |
| E4 lesson loading | 1727 | `lesson_loading` | 1770 | `decrease` |
| E5 streak reminder | 1728 | `streak_reminder` | 1771, 1772 | `increase`, `increase` |

E5 is the only one with two metrics, and that is what makes it the INCONCLUSIVE case.

Start an experiment with `POST /api/v1/environments/{env_key}/experiments/{id}/start/`.

## 4. Plain (non-experiment) flags

Not created in this project yet; the app serves the defaults below and runs fine without them. Create
them when you want to exercise the guardian's non-experiment paths.

| Flag | Enabled | Value | Extra setup | What it proves |
|---|---|---|---|---|
| `maintenance_mode` | off | – | none | kill switch |
| `beta_exam_mode` | off | – | segment override `pro_users` → enabled | segment targeting |
| `support_chat` | off | – | identity override `vip-learner` → enabled | identity override |
| `daily_goal_xp` | on | `20` | segment override `power_users` → `50` | remote config + value override |
| `ai_tutor` | on | `off` | multivariate `on` at 10% | staged rollout that is **not** an experiment |
| `legacy_leaderboard` | on | – | tag `stale`, 100% everywhere | stale flag → `guardian cleanup` candidate |

Segments, if you create them: `pro_users` (trait `plan` in `pro,enterprise`), `new_learners`
(`days_since_signup <= 7`), `power_users` (`streak_days >= 30`).

## 5. Generate data

```powershell
py -m learnloop.sim --dry-run
```

```powershell
py -m learnloop.sim --users 3000
```

`POST /api/v1/events/` answers `404 This environment does not store events in Flagsmith` — events
reach the warehouse through the **SDK** (`Flagsmith(enable_events=True)` + `track_event`), which is
what the app and the simulator both do. Results lag a few minutes; recompute in the console or run
`guardian refresh <id>`.

## 6. Recreating all of it

From the guardian repo (it holds the Management API key):

```powershell
.venv\Scripts\python.exe spikes\seed_lab.py --apply --start
```

Idempotent: it creates only what is missing and writes the id map to `out/lab_ids.json`.
