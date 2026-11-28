"""Flagsmith client + every flag this app reads, in one place.

Two reads and one write, and nothing else here talks to Flagsmith:

    read_experiment_flag(name, uid, traits)   an experiment arm, and it records the exposure
    read_flag(name, uid, traits)              a plain flag
    track_event(event, uid, value, traits)    a conversion event

Those names are what `cleanup.yaml` points the guardian at: `sdk_calls` is how a flag reference is
recognised, and `keep_patterns` protects every `track_event(` line from being touched by a cleanup.

Offline-safe: if a flag does not exist in the environment yet, the default below is served and NO
exposure is sent (a DefaultFlag counts as "feature not found"), so the app runs with no network and
the tests never need one.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flagsmith import Flagsmith
from flagsmith.analytics import EventProcessorConfig
from flagsmith.models import DefaultFlag, Flag

ROOT = Path(__file__).resolve().parent.parent

# The five experiment flags, one running Flagsmith experiment each. The default value IS the control
# arm, so an app with no network behaves exactly like the control group.
EXPERIMENT_FLAGS = {
    "pricing_layout": "monthly_first",   # E1 -> WINNER
    "help_widget": "link",               # E3 -> SYSTEMIC_FAILURE
    "lesson_loading": "eager",           # E4 -> SEVERE_HARM (the mean metric)
    "streak_reminder": "none",           # E5 -> INCONCLUSIVE
}
# Plain flags: kill switch, segment/identity overrides, remote config, staged rollout, stale flag.
# None of these is an experiment; they exercise the guardian's other paths.
PLAIN_FLAGS = {
    "maintenance_mode": (False, None),
    "beta_exam_mode": (False, None),
    "support_chat": (False, None),
    "daily_goal_xp": (True, "20"),
    "ai_tutor": (False, "off"),
    "legacy_leaderboard": (True, None),
}
DEFAULTS = {**{k: (True, v) for k, v in EXPERIMENT_FLAGS.items()}, **PLAIN_FLAGS}


def _default_handler(name: str) -> DefaultFlag:
    enabled, value = DEFAULTS.get(name, (False, None))
    return DefaultFlag(enabled=enabled, value=value)


def environment_key() -> str | None:
    """FLAGSMITH_ENVIRONMENT_KEY wins; otherwise flagsmith.json (the shape the Flagsmith CLI writes)."""
    env = os.environ.get("FLAGSMITH_ENVIRONMENT_KEY")
    if env:
        return env
    try:
        return json.loads((ROOT / "flagsmith.json").read_text()).get("environment")
    except (OSError, ValueError):
        return None


_client: Flagsmith | None = None


def client() -> Flagsmith | None:
    global _client
    if _client is None:
        key = environment_key()
        if not key:
            return None
        _client = Flagsmith(
            environment_key=key,
            enable_events=True,
            event_processor_config=EventProcessorConfig(max_buffer_items=50000, flush_interval_seconds=5.0),
            default_flag_handler=_default_handler,
        )
    return _client


# ---- the three calls the guardian knows about -------------------------------------------------------------

def read_experiment_flag(name: str, user_id: str, traits: dict | None = None):
    """Resolve an experiment flag and record one exposure. Returns (enabled, value)."""
    c = client()
    if c is None:
        return DEFAULTS[name]
    f = c.get_experiment_flag(name, identifier=user_id, traits=traits)
    return f.enabled, f.value


def read_flag(name: str, user_id: str, traits: dict | None = None):
    """Resolve a plain (non-experiment) flag. Returns (enabled, value)."""
    c = client()
    if c is None:
        return DEFAULTS.get(name, (False, None))
    f = c.get_identity_flags(user_id, traits=traits).get_flag(name)
    return f.enabled, f.value


def track_event(event: str, user_id: str, value=None, traits: dict | None = None) -> None:
    """Record a conversion event. `value` is what a MEAN or SUM metric aggregates."""
    c = client()
    if c is not None:
        c.track_event(event, identifier=user_id, value=value, traits=traits)


def flush() -> None:
    c = client()
    if c is not None:
        c.flush_events()


# ---- bulk path, used only by the simulator ----------------------------------------------------------------
# Each read above costs one HTTP request. A simulator run is tens of thousands of reads, so it resolves
# an identity ONCE and records its own exposures - the same two steps `get_experiment_flag` takes
# internally, with the same guards, so the data Flagsmith receives is identical.

def resolve_identity(user_id: str, traits: dict | None = None):
    """Every flag for one identity in a single request; None when there is no environment key."""
    c = client()
    if c is None:
        return None
    return c.get_identity_flags(user_id, traits=traits)


def arm_of(resolved, name: str, user_id: str, traits: dict | None = None) -> str | None:
    """The arm VALUE this identity sees for `name`, recording the exposure. None if not enrolled.

    Mirrors `Flagsmith.get_experiment_flag`: an exposure is sent only for a real, enabled flag whose
    identity is in a running experiment with a variant.
    """
    if resolved is None:
        return DEFAULTS[name][1]
    f = resolved.get_flag(name)
    if not isinstance(f, Flag) or not f.enabled or f.variant is None \
            or not (f.experiment and f.experiment.in_experiment):
        return None
    c = client()
    if c is not None:
        c.track_exposure_event(feature_name=name, identifier=user_id, value=f.variant, traits=traits,
                               metadata={"experiment_id": f.experiment.id})
    return f.value


# ---- pure helpers (unit-tested, no network) ---------------------------------------------------------------

def parse_int(raw, default: int) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default
