import runpy
import sys
import pytest
from learnloop import flags


def test_cli_exits_with_error_when_run_live_without_environment_key(monkeypatch):
    monkeypatch.setattr(flags, "client", lambda: None)
    monkeypatch.setattr(sys, "argv", ["sim", "--users", "10"])
    monkeypatch.delitem(sys.modules, "learnloop.sim", raising=False)
    with pytest.raises(SystemExit, match="No environment key"):
        runpy.run_module("learnloop.sim", run_name="__main__")


def test_cli_succeeds_in_dry_run_mode_without_environment_key(monkeypatch, capsys):
    monkeypatch.setattr(flags, "client", lambda: None)
    monkeypatch.setattr(sys, "argv", ["sim", "--dry-run", "--users", "5"])
    monkeypatch.delitem(sys.modules, "learnloop.sim", raising=False)
    runpy.run_module("learnloop.sim", run_name="__main__")
    captured = capsys.readouterr()
    assert "simulating 5 users (dry_run=True)" in captured.out
    assert "done." in captured.out
