"""Shared fixtures. Nothing in this suite is allowed to touch the network.

Every test runs with the Flagsmith singleton cleared and `flags.client()` stubbed to None, so the app
serves its built-in control defaults. A test that wants a specific arm says so with the `arm` fixture,
which is also what lets `guardian cleanup` delete one experiment's test file without any other test
noticing.
"""
import pytest

from learnloop import flags


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No singleton, no key, no client - so no test can reach Flagsmith by accident."""
    flags._client = None
    monkeypatch.delenv("FLAGSMITH_ENVIRONMENT_KEY", raising=False)
    monkeypatch.setattr(flags, "client", lambda: None)
    yield
    flags._client = None


@pytest.fixture
def arm(monkeypatch):
    """Serve a chosen arm for one experiment flag; every other flag keeps its control default.

        def test_x(arm, app):
            arm("quiz_timer", "30")
            at = app().run()
    """
    def serve(name: str, value):
        def read_experiment_flag(flag_name, user_id, traits=None):
            if flag_name == name:
                return True, value
            return flags.DEFAULTS.get(flag_name, (True, None))
        monkeypatch.setattr(flags, "read_experiment_flag", read_experiment_flag)
    return serve


@pytest.fixture
def plain(monkeypatch):
    """Serve chosen values for plain flags; the rest keep their defaults."""
    def serve(**overrides):
        def read_flag(flag_name, user_id, traits=None):
            if flag_name in overrides:
                return overrides[flag_name]
            return flags.DEFAULTS.get(flag_name, (False, None))
        monkeypatch.setattr(flags, "read_flag", read_flag)
    return serve


@pytest.fixture
def tracked(monkeypatch):
    """Collect (event, value) pairs instead of sending them."""
    events: list[tuple[str, object]] = []
    monkeypatch.setattr(flags, "track_event",
                        lambda event, user_id, value=None, traits=None: events.append((event, value)))
    return events


@pytest.fixture
def app():
    """A fresh Streamlit AppTest for app.py."""
    from streamlit.testing.v1 import AppTest
    return lambda: AppTest.from_file("app.py", default_timeout=30)


def goto(at, page: str):
    """Switch the sidebar to a page and rerun."""
    at.sidebar.radio[0].set_value(page).run()
    return at
