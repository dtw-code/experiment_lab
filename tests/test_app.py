from streamlit.testing.v1 import AppTest


def test_app_renders_home_page_with_daily_goal_by_default(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not at.exception
    assert any("LearnLoop" in t.value for t in at.title)
    # Check that daily goal metric is rendered with default 20 XP
    metrics = [m.value for m in at.metric]
    assert any("20 XP" in str(m) for m in metrics)


def test_app_halts_immediately_when_maintenance_mode_is_enabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)

    def mock_flag(name, uid, traits=None):
        if name == "maintenance_mode":
            return True, None
        return False, None

    monkeypatch.setattr("learnloop.flags.flag", mock_flag)

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not at.exception
    # Maintenance error should be displayed
    assert any("down for maintenance" in e.value for e in at.error)
    # Main page title should never be reached due to st.stop()
    assert len(at.title) == 0


def test_app_once_tracking_prevents_duplicate_events_in_session(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    tracked_events = []

    def mock_track(event, uid, value=None, traits=None):
        tracked_events.append(event)

    monkeypatch.setattr("learnloop.flags.track", mock_track)

    at = AppTest.from_file("app.py", default_timeout=10).run()
    # Click "Finish onboarding" button
    finish_button = next(b for b in at.button if b.label == "Finish onboarding")
    finish_button.click().run()

    assert tracked_events.count("onboarding_completed") == 1

    # Clicking the button a second time should not fire another track event
    finish_button.click().run()
    assert tracked_events.count("onboarding_completed") == 1
