import json
from learnloop import flags


class FakePath:
    def __init__(self, content=None, error=None):
        self.content = content
        self.error = error

    def __truediv__(self, other):
        return self

    def read_text(self):
        if self.error:
            raise self.error
        return self.content


def test_environment_key_prefers_environment_variable_over_file(monkeypatch):
    monkeypatch.setenv("FLAGSMITH_ENVIRONMENT_KEY", "env_var_override_key")
    assert flags.environment_key() == "env_var_override_key"


def test_environment_key_reads_from_flagsmith_json_when_env_var_absent(monkeypatch):
    monkeypatch.delenv("FLAGSMITH_ENVIRONMENT_KEY", raising=False)
    monkeypatch.setattr(flags, "ROOT", FakePath(content=json.dumps({"environment": "file_json_key"})))

    assert flags.environment_key() == "file_json_key"


def test_environment_key_returns_none_when_both_file_and_env_var_missing(monkeypatch):
    monkeypatch.delenv("FLAGSMITH_ENVIRONMENT_KEY", raising=False)
    monkeypatch.setattr(flags, "ROOT", FakePath(error=FileNotFoundError("flagsmith.json not found")))

    assert flags.environment_key() is None


def test_environment_key_returns_none_when_file_contains_invalid_json(monkeypatch):
    monkeypatch.delenv("FLAGSMITH_ENVIRONMENT_KEY", raising=False)
    monkeypatch.setattr(flags, "ROOT", FakePath(content="invalid-json-content"))

    assert flags.environment_key() is None


def test_default_flag_handler_returns_configured_defaults_for_experiments_and_plain_flags():
    pricing_flag = flags._default_handler("pricing_layout")
    assert pricing_flag.enabled is True
    assert pricing_flag.value == "monthly_first"

    maint_flag = flags._default_handler("maintenance_mode")
    assert maint_flag.enabled is False
    assert maint_flag.value is None

    xp_flag = flags._default_handler("daily_goal_xp")
    assert xp_flag.enabled is True
    assert xp_flag.value == "20"


def test_default_flag_handler_returns_disabled_none_for_unregistered_flag():
    unregistered = flags._default_handler("non_existent_flag")
    assert unregistered.enabled is False
    assert unregistered.value is None


def test_offline_experiment_resolution_returns_control_default_without_client(monkeypatch):
    monkeypatch.setattr(flags, "client", lambda: None)
    assert flags.experiment("pricing_layout", "uid-1") == (True, "monthly_first")
    assert flags.experiment("lesson_length", "uid-1") == (True, '{"minutes": 10, "cards": 8}')


def test_offline_flag_resolution_returns_default_without_client(monkeypatch):
    monkeypatch.setattr(flags, "client", lambda: None)
    assert flags.flag("maintenance_mode", "uid-1") == (False, None)
    assert flags.flag("daily_goal_xp", "uid-1") == (True, "20")
    assert flags.flag("unregistered_flag", "uid-1") == (False, None)


def test_offline_tracking_and_flush_safely_no_op_when_client_is_none(monkeypatch):
    monkeypatch.setattr(flags, "client", lambda: None)
    # Should safely return without error
    flags.track("lesson_started", "uid-1")
    flags.flush()
