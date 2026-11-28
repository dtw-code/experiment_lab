"""The six non-experiment flags: kill switch, overrides, remote config, staged rollout, stale flag.

None of these is part of an experiment, so none of them is removed when an experiment ends. They are
here because the guardian's other paths need them: `maintenance_mode` is the kill switch,
`legacy_leaderboard` is a stale fully-rolled-out flag that `guardian cleanup` should offer to delete
on its own, and `ai_tutor` is a staged percentage rollout that must never be mistaken for a test.
"""
from conftest import goto


def test_maintenance_mode_stops_the_whole_app(plain, app):
    plain(maintenance_mode=(True, None))
    at = app().run()
    assert not at.exception
    assert any("down for maintenance" in e.value for e in at.error)
    assert len(at.title) == 0


def test_the_app_renders_normally_with_maintenance_off(plain, app):
    plain(maintenance_mode=(False, None))
    at = app().run()
    assert any("LearnLoop" in t.value for t in at.title)
    assert len(at.error) == 0


def test_support_chat_shows_the_sidebar_banner_when_overridden(plain, app):
    plain(support_chat=(True, None))
    assert any("Priority support chat" in s.value for s in app().run().sidebar.success)


def test_support_chat_is_hidden_by_default(app):
    assert not any("Priority support chat" in s.value for s in app().run().sidebar.success)


def test_daily_goal_xp_is_read_from_the_remote_config(plain, app):
    plain(daily_goal_xp=(True, "50"))
    assert any("50 XP" in str(m.value) for m in app().run().metric)


def test_a_non_numeric_daily_goal_falls_back_to_twenty(plain, app):
    plain(daily_goal_xp=(True, "not_a_number"))
    assert any("20 XP" in str(m.value) for m in app().run().metric)


def test_the_stale_leaderboard_renders_while_the_flag_is_on(plain, app):
    plain(legacy_leaderboard=(True, None))
    assert any("Leaderboard" in s.value for s in app().run().subheader)


def test_turning_the_stale_leaderboard_off_removes_it(plain, app):
    plain(legacy_leaderboard=(False, None))
    assert not any("Leaderboard" in s.value for s in app().run().subheader)


def test_beta_exam_mode_is_a_segment_banner_on_the_quiz(plain, app):
    plain(beta_exam_mode=(True, None))
    at = goto(app().run(), "Quiz")
    assert any("Exam mode (beta)" in i.value for i in at.info)


def test_the_ai_tutor_appears_only_for_the_rolled_out_value(plain, app):
    plain(ai_tutor=(True, "on"))
    at = goto(app().run(), "Lesson")
    assert any("AI tutor" in b.label for b in at.button)


def test_the_ai_tutor_is_absent_for_the_default_value(plain, app):
    plain(ai_tutor=(False, "off"))
    at = goto(app().run(), "Lesson")
    assert not any("AI tutor" in b.label for b in at.button)
