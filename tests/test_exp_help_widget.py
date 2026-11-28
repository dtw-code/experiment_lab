"""E3 `help_widget` - the experiment built to reach SYSTEMIC_FAILURE.

The point is that the VARIANT is not the problem. `support_ticket_opened` is declared a failure_rate
with an absolute ceiling of 0.05 in the guardian's policy, and both arms sit around 0.21, so control
breaches it too. The guardian is supposed to say "a rollback would not help" and only notify.
"""
from conftest import goto

from learnloop import experiments, knobs

CEILING = 0.05   # policy.yaml metrics."support_ticket_opened".abs_ceiling


# ---- the arm logic, pure ----------------------------------------------------------------------
def test_control_shows_no_extra_hint():
    assert experiments.help_widget_hint("link") is None


def test_the_variant_shows_a_self_service_hint():
    assert "rereading" in experiments.help_widget_hint("chat_hint")


def test_an_unknown_arm_behaves_like_control():
    assert experiments.help_widget_hint("inline_faq") is None
    assert experiments.help_widget_hint(None) is None


# ---- the knobs that make this SYSTEMIC rather than HARMFUL ------------------------------------
def test_every_arm_breaches_the_ceiling_including_control():
    arms = knobs.EXPERIMENTS["help_widget"]
    rates = {name: table["support_ticket_opened"] for name, table in arms.items()}
    assert min(rates.values()) > CEILING * 2, (
        "control itself must breach the ceiling with room to spare, or the verdict drops to "
        f"HARMFUL_VARIANT: {rates}")


def test_the_two_arms_barely_differ():
    arms = knobs.EXPERIMENTS["help_widget"]
    control, variant = arms["link"]["support_ticket_opened"], arms["chat_hint"]["support_ticket_opened"]
    assert abs(variant - control) / control < 0.10, \
        "a real difference would let a harm or winner verdict preempt SYSTEMIC_FAILURE"


# ---- the page --------------------------------------------------------------------------------
def test_the_lesson_page_shows_the_hint_on_the_variant(arm, app):
    arm("help_widget", "chat_hint")
    at = goto(app().run(), "Lesson")
    assert not at.exception
    assert any("rereading card 3" in c.value for c in at.caption)


def test_the_lesson_page_shows_no_hint_on_control(arm, app):
    arm("help_widget", "link")
    at = goto(app().run(), "Lesson")
    assert not any("rereading card 3" in c.value for c in at.caption)


def test_contacting_support_records_a_ticket_on_either_arm(arm, app, tracked):
    arm("help_widget", "link")
    at = goto(app().run(), "Lesson")
    next(b for b in at.button if b.label == "Contact support").click().run()
    assert ("support_ticket_opened", None) in tracked
