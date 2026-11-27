"""Flagsmith client + every flag the app reads, in one place.

Offline-safe: if a flag does not exist in the environment yet, the default below is served and NO exposure is sent
(a DefaultFlag counts as "feature not found" for get_experiment_flag), so you can create flags in the console one at
a time while the app keeps running.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from flagsmith import Flagsmith
from flagsmith.analytics import EventProcessorConfig
from flagsmith.models import DefaultFlag

ROOT = Path(__file__).resolve().parent.parent

# Experiments: default value == the control variant.
EXPERIMENT_FLAGS = {
    "pricing_layout": "monthly_first",
    "lesson_length": '{"minutes": 10, "cards": 8}',
    "quiz_timer": "none",
    "onboarding_flow": "classic",
    "streak_reminder": "none",
}
# Plain flags: kill switch, segment/identity overrides, remote config, staged rollout, stale (cleanup) flags.
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
    """FLAGSMITH_ENVIRONMENT_KEY wins; otherwise flagsmith.json (same shape the Flagsmith CLI writes)."""
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


def experiment(name: str, user_id: str, traits: dict | None = None):
    """Resolve an experiment flag and record an exposure. Returns (enabled, value)."""
    c = client()
    if c is None:
        return DEFAULTS[name]
    f = c.get_experiment_flag(name, identifier=user_id, traits=traits)
    return f.enabled, f.value


def flag(name: str, user_id: str, traits: dict | None = None):
    """Resolve a normal (non-experiment) flag. Returns (enabled, value)."""
    c = client()
    if c is None:
        return DEFAULTS.get(name, (False, None))
    f = c.get_identity_flags(user_id, traits=traits).get_flag(name)
    return f.enabled, f.value


def track(event: str, user_id: str, value=None, traits: dict | None = None) -> None:
    c = client()
    if c is not None:
        c.track_event(event, identifier=user_id, value=value, traits=traits)


def flush() -> None:
    c = client()
    if c is not None:
        c.flush_events()


# ---- pure helpers (unit-tested, no network) ----------------------------------------------------------------

def parse_lesson_length(raw) -> dict:
    cfg = {"minutes": 10, "cards": 8}
    try:
        parsed = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, dict):
            cfg.update({k: parsed[k] for k in ("minutes", "cards") if k in parsed})
    except (TypeError, ValueError):
        pass
    return cfg


def lesson_arm(cfg: dict) -> str:
    """Arm key used in knobs.EXPERIMENTS['lesson_length'], derived from the JSON config."""
    return f"{cfg['minutes']}min"


def parse_quiz_timer(raw) -> int | None:
    """None = untimed. Accepts 'none', '', '60', 60."""
    try:
        seconds = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    return seconds if seconds > 0 else None


def parse_int(raw, default: int) -> int:
    try:
        return int(str(raw).strip())
    except (TypeError, ValueError):
        return default
