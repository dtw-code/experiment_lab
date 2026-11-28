"""The Flagsmith client boundary: key resolution, defaults, and the offline behaviour.

This file knows about no single experiment, so a cleanup never touches it. It does assert that the
default served for an experiment flag is its CONTROL arm, which is what makes the app safe to run
before the flags exist and what keeps the whole test suite offline.
"""
import json

import pytest

from learnloop import flags


class FakePath:
    def __init__(self, content=None, error=None):
        self.content, self.error = content, error

    def __truediv__(self, other):
        return self

    def read_text(self):
        if self.error:
            raise self.error
        return self.content


# ---- where the environment key comes from -----------------------------------------------------
def test_the_environment_variable_wins_over_the_file(monkeypatch):
    monkeypatch.setenv("FLAGSMITH_ENVIRONMENT_KEY", "env_var_override_key")
    assert flags.environment_key() == "env_var_override_key"


def test_the_key_is_read_from_flagsmith_json_otherwise(monkeypatch):
    monkeypatch.setattr(flags, "ROOT", FakePath(content=json.dumps({"environment": "file_json_key"})))
    assert flags.environment_key() == "file_json_key"


@pytest.mark.parametrize("path", [
    FakePath(error=FileNotFoundError("flagsmith.json not found")),
    FakePath(content="invalid-json-content"),
])
def test_a_missing_or_broken_file_leaves_no_key(monkeypatch, path):
    monkeypatch.setattr(flags, "ROOT", path)
    assert flags.environment_key() is None


# ---- the defaults ------------------------------------------------------------------------------
def test_every_experiment_flag_defaults_to_its_control_arm():
    for name, control in flags.EXPERIMENT_FLAGS.items():
        served = flags._default_handler(name)
        assert served.enabled is True
        assert served.value == control, f"{name} must default to control, not a variant"


def test_the_four_experiment_flags_are_the_ones_the_console_runs():
    assert set(flags.EXPERIMENT_FLAGS) == {
        "pricing_layout", "help_widget", "lesson_loading", "streak_reminder"}


def test_plain_flag_defaults_are_served_as_declared():
    assert flags._default_handler("maintenance_mode").enabled is False
    assert flags._default_handler("daily_goal_xp").value == "20"


def test_an_unknown_flag_is_off_with_no_value():
    served = flags._default_handler("non_existent_flag")
    assert (served.enabled, served.value) == (False, None)


# ---- offline behaviour -------------------------------------------------------------------------
def test_reading_an_experiment_flag_offline_serves_control():
    assert flags.read_experiment_flag("pricing_layout", "uid-1") == (True, "monthly_first")
    assert flags.read_experiment_flag("lesson_loading", "uid-1") == (True, "eager")


def test_reading_a_plain_flag_offline_serves_its_default():
    assert flags.read_flag("maintenance_mode", "uid-1") == (False, None)
    assert flags.read_flag("unregistered_flag", "uid-1") == (False, None)


def test_tracking_and_flushing_offline_are_no_ops():
    flags.track_event("quiz_passed", "uid-1")
    flags.track_event("lesson_load_ms", "uid-1", 1500)
    flags.flush()


def test_resolving_an_identity_offline_yields_nothing():
    assert flags.resolve_identity("uid-1") is None


def test_arm_of_without_a_resolved_identity_serves_control():
    assert flags.arm_of(None, "pricing_layout", "uid-1") == "monthly_first"


# ---- parse_int ---------------------------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [
    ("20", 20), (" 50 ", 50), (7, 7), ("abc", 99), (None, 99), ("", 99),
])
def test_parse_int_falls_back_on_anything_unparseable(raw, expected):
    assert flags.parse_int(raw, 99) == expected
