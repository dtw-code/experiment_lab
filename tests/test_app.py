from streamlit.testing.v1 import AppTest


def run_app(flag_overrides=None, experiment_overrides=None, page="Home", days=3, streak=5):
    """Helper to run app.py with injected flag boundaries and UI settings."""
    flag_dict = flag_overrides or {}
    exp_dict = experiment_overrides or {}

    def mock_flag(name, uid, traits=None):
        if name in flag_dict:
            return flag_dict[name]
        from learnloop.flags import DEFAULTS
        return DEFAULTS.get(name, (False, None))

    def mock_experiment(name, uid, traits=None):
        if name in exp_dict:
            return exp_dict[name]
        from learnloop.flags import DEFAULTS
        return DEFAULTS.get(name, (True, None))

    at = AppTest.from_file("app.py", default_timeout=10)
    return at, mock_flag, mock_experiment


# -----------------------------------------------------------------------------
# 1. maintenance_mode
# -----------------------------------------------------------------------------

def test_app_halts_execution_when_maintenance_mode_is_active(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, None) if name == "maintenance_mode" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not at.exception
    assert any("down for maintenance" in e.value for e in at.error)
    assert len(at.title) == 0


def test_app_renders_main_content_when_maintenance_mode_is_inactive(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not at.exception
    assert any("LearnLoop" in t.value for t in at.title)
    assert len(at.error) == 0


# -----------------------------------------------------------------------------
# 2. support_chat
# -----------------------------------------------------------------------------

def test_app_displays_priority_support_banner_when_support_chat_is_enabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, None) if name == "support_chat" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("Priority support chat is on" in s.value for s in at.sidebar.success)


def test_app_hides_priority_support_banner_when_support_chat_is_disabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not any("Priority support chat is on" in s.value for s in at.sidebar.success)


# -----------------------------------------------------------------------------
# 3. daily_goal_xp
# -----------------------------------------------------------------------------

def test_app_displays_custom_xp_metric_when_daily_goal_is_configured(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, "50") if name == "daily_goal_xp" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("50 XP" in str(m.value) for m in at.metric)


def test_app_falls_back_to_default_xp_when_daily_goal_flag_is_non_numeric(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, "not_a_number") if name == "daily_goal_xp" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("20 XP" in str(m.value) for m in at.metric)


# -----------------------------------------------------------------------------
# 4. legacy_leaderboard
# -----------------------------------------------------------------------------

def test_app_displays_leaderboard_table_when_legacy_leaderboard_is_enabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, None) if name == "legacy_leaderboard" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("Leaderboard" in s.value for s in at.subheader)


def test_app_hides_leaderboard_table_when_legacy_leaderboard_is_disabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, None) if name == "legacy_leaderboard" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not any("Leaderboard" in s.value for s in at.subheader)


# -----------------------------------------------------------------------------
# 5. streak_reminder
# -----------------------------------------------------------------------------

def test_app_displays_gentle_streak_reminder_banner_and_tracking_buttons(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "gentle") if name == "streak_reminder" else (True, "control"))
    tracked = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, *a, **k: tracked.append(evt))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("Nice streak!" in w.value for w in at.warning)
    return_btn = next(b for b in at.button if b.label == "I'll come back tomorrow")
    return_btn.click().run()
    assert "daily_return" in tracked


def test_app_displays_urgent_streak_reminder_banner_and_tracking_buttons(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "urgent") if name == "streak_reminder" else (True, "control"))
    tracked = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, *a, **k: tracked.append(evt))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("ENDS TONIGHT" in w.value for w in at.warning)
    opt_out_btn = next(b for b in at.button if b.label == "Turn reminders off")
    opt_out_btn.click().run()
    assert "reminder_opt_out" in tracked


def test_app_hides_streak_reminder_when_reminder_flag_is_none(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "none") if name == "streak_reminder" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not any("streak" in str(w.value).lower() for w in at.warning)


# -----------------------------------------------------------------------------
# 6. onboarding_flow
# -----------------------------------------------------------------------------

def test_app_renders_checklist_onboarding_for_new_signup(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "checklist") if name == "onboarding_flow" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    labels = [c.label for c in at.checkbox]
    assert "Pick a topic" in labels
    assert "Finish your first lesson" in labels
    assert "Set a daily goal" in labels


def test_app_renders_classic_tour_onboarding_for_new_signup(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "classic") if name == "onboarding_flow" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert any("Classic tour: Step 1 of 3" in i.value for i in at.info)


def test_app_skips_onboarding_section_for_experienced_learners(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    at = AppTest.from_file("app.py", default_timeout=10).run()
    # Change days_since_signup to 14 in sidebar
    at.sidebar.number_input[0].set_value(14).run()
    assert not any("Welcome! 👋" in s.value for s in at.subheader)


# -----------------------------------------------------------------------------
# 7. lesson_length
# -----------------------------------------------------------------------------

def test_app_renders_custom_lesson_length_configuration(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, '{"minutes": 5, "cards": 3}') if name == "lesson_length" else (True, "control"))
    tracked = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, uid, val=None, *a, **k: tracked.append((evt, val)))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()

    assert any("5 min, 3 cards" in s.value for s in at.subheader)
    captions = [c.value for c in at.caption]
    assert "Card 3/3" in captions
    assert "Card 4/3" not in captions

    finish_btn = next(b for b in at.button if b.label == "Finish lesson")
    finish_btn.click().run()
    assert ("lesson_completed", 5) in tracked


# -----------------------------------------------------------------------------
# 8. help_widget
# -----------------------------------------------------------------------------

def test_app_renders_inline_faq_expander_in_lesson_help(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "inline_faq") if name == "help_widget" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()
    assert any("Quick answers" in str(getattr(exp, "label", "")) for exp in at.expander)


def test_app_renders_chat_hint_caption_in_lesson_help(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "chat_hint") if name == "help_widget" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()
    assert any("💡 Stuck? Try rereading card 3." in c.value for c in at.caption)


def test_app_renders_standard_support_link_in_lesson_help(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "link") if name == "help_widget" else (True, "control"))
    tracked = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, *a, **k: tracked.append(evt))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()
    assert not any("Quick answers" in str(getattr(exp, "label", "")) for exp in at.expander)
    contact_btn = next(b for b in at.button if b.label == "Contact support")
    contact_btn.click().run()
    assert "support_ticket_opened" in tracked


# -----------------------------------------------------------------------------
# 9. ai_tutor
# -----------------------------------------------------------------------------

def test_app_renders_ai_tutor_button_when_staged_rollout_is_on(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, "on") if name == "ai_tutor" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()
    assert any("Ask the AI tutor" in b.label for b in at.button)


def test_app_hides_ai_tutor_button_when_staged_rollout_is_off(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, "off") if name == "ai_tutor" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Lesson").run()
    assert not any("Ask the AI tutor" in b.label for b in at.button)


# -----------------------------------------------------------------------------
# 10. quiz_timer
# -----------------------------------------------------------------------------

def test_app_displays_countdown_timer_when_quiz_timer_is_configured(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "60") if name == "quiz_timer" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Quiz").run()
    assert any("⏱️ 60s timer" in c.value for c in at.caption)


def test_app_displays_untimed_caption_when_quiz_timer_is_none(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "none") if name == "quiz_timer" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Quiz").run()
    assert any("Untimed" in c.value for c in at.caption)


# -----------------------------------------------------------------------------
# 11. beta_exam_mode
# -----------------------------------------------------------------------------

def test_app_displays_beta_exam_banner_when_enabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (True, None) if name == "beta_exam_mode" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Quiz").run()
    assert any("Exam mode (beta) is available" in i.value for i in at.info)


def test_app_hides_beta_exam_banner_when_disabled(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, None) if name == "beta_exam_mode" else (False, None))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Quiz").run()
    assert not any("Exam mode (beta) is available" in i.value for i in at.info)


# -----------------------------------------------------------------------------
# 12. pricing_layout
# -----------------------------------------------------------------------------

def test_app_renders_annual_first_pricing_layout(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "annual_first") if name == "pricing_layout" else (True, "control"))
    tracked = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, uid, val=None, *a, **k: tracked.append((evt, val)))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Pricing").run()
    button_labels = [b.label for b in at.button]
    assert any("Annual (save 27%): $79" in lbl for lbl in button_labels)

    annual_btn = next(b for b in at.button if "Annual (save 27%)" in b.label)
    annual_btn.click().run()
    assert ("subscription_started", None) in tracked
    assert ("revenue", 79) in tracked


def test_app_renders_three_tier_pricing_layout(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "three_tier") if name == "pricing_layout" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Pricing").run()
    button_labels = [b.label for b in at.button]
    assert any("Basic: $5" in lbl for lbl in button_labels)
    assert any("Pro: $9" in lbl for lbl in button_labels)
    assert any("Team: $24" in lbl for lbl in button_labels)


def test_app_renders_monthly_first_pricing_layout(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (True, "monthly_first") if name == "pricing_layout" else (True, "control"))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    at.sidebar.radio[0].set_value("Pricing").run()
    button_labels = [b.label for b in at.button]
    assert any("Monthly: $9" in lbl for lbl in button_labels)
    assert any("Annual: $79" in lbl for lbl in button_labels)


# -----------------------------------------------------------------------------
# 13. Analytics & Deduplication
# -----------------------------------------------------------------------------

def test_app_analytics_track_fires_and_deduplicates_repeated_clicks(monkeypatch):
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    tracked_events = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, *a, **k: tracked_events.append(evt))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    finish_button = next(b for b in at.button if b.label == "Finish onboarding")
    finish_button.click().run()
    assert tracked_events.count("onboarding_completed") == 1

    # Second click must not re-fire
    finish_button.click().run()
    assert tracked_events.count("onboarding_completed") == 1


def test_app_analytics_survives_missing_flags_and_falls_back_cleanly(monkeypatch):
    # Simulate an environment where Flagsmith serves empty/disabled flags
    monkeypatch.setattr("learnloop.flags.client", lambda: None)
    monkeypatch.setattr("learnloop.flags.flag", lambda name, *a, **k: (False, None))
    monkeypatch.setattr("learnloop.flags.experiment", lambda name, *a, **k: (False, None))

    tracked_events = []
    monkeypatch.setattr("learnloop.flags.track", lambda evt, *a, **k: tracked_events.append(evt))

    at = AppTest.from_file("app.py", default_timeout=10).run()
    assert not at.exception
    # Even with all flags disabled, clicking buttons tracks events without errors
    finish_btn = next(b for b in at.button if b.label == "Finish onboarding")
    finish_btn.click().run()
    assert "onboarding_completed" in tracked_events
