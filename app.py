"""LearnLoop - a tiny micro-learning app used to exercise the experiment guardian.

Run:  py -m streamlit run app.py
Five pages, five experiments, six plain flags. See SETUP.md for exactly what to create in the Flagsmith console.
Tweak who wins in learnloop/knobs.py (simulator) - the UI buttons below are for hand-testing a single user.
"""
import random
import uuid

import streamlit as st

from learnloop import flags, knobs, sim

st.set_page_config(page_title="LearnLoop", page_icon="🔁", layout="centered")

# ---------------------------------------------------------------- identity & traits (drives segments)
ss = st.session_state
ss.setdefault("uid", f"user-{uuid.uuid4()}")
ss.setdefault("resolved", {})
ss.setdefault("fired", set())

with st.sidebar:
    st.header("🧪 Identity & traits")
    uid = st.text_input("User ID (try `vip-learner` for the identity override)", value=ss.uid)
    if uid and uid != ss.uid:
        ss.uid, ss.resolved, ss.fired = uid, {}, set()
        st.rerun()
    plan = st.selectbox("plan", ["free", "pro", "enterprise"])
    country = st.selectbox("country", ["IN", "US", "UK", "DE"])
    days = st.number_input("days_since_signup", 0, 1000, 3)
    streak = st.number_input("streak_days", 0, 1000, 5)
    page = st.radio("Page", ["Home", "Lesson", "Quiz", "Pricing", "Simulator"])

traits = {"plan": plan, "country": country, "days_since_signup": int(days), "streak_days": int(streak)}


def exp(name: str):
    """Experiment flag, exposure recorded at most once per user per session."""
    if name not in ss.resolved:
        ss.resolved[name] = flags.experiment(name, ss.uid, traits)
    return ss.resolved[name]


def once(event: str, value=None) -> None:
    """Track an event once per user per session so button mashing cannot inflate a metric."""
    if event not in ss.fired:
        ss.fired.add(event)
        flags.track(event, ss.uid, value, traits)
        st.toast(f"tracked `{event}`" + (f" = {value}" if value is not None else ""))


# ---------------------------------------------------------------- global flags (kill switch, overrides)
on_maint, _ = flags.flag("maintenance_mode", ss.uid, traits)
if on_maint:
    st.error("🛠️ LearnLoop is down for maintenance. (flag `maintenance_mode` is ON)")
    st.stop()

with st.sidebar:
    if flags.flag("support_chat", ss.uid, traits)[0]:
        st.success("💬 Priority support chat is on for you (flag `support_chat`)")

st.title("🔁 LearnLoop")


# ---------------------------------------------------------------- pages
def home():
    goal = flags.parse_int(flags.flag("daily_goal_xp", ss.uid, traits)[1], 20)
    st.metric("Daily goal (flag `daily_goal_xp`)", f"{goal} XP")

    # E5 streak_reminder - copy test with a guardrail
    _, reminder = exp("streak_reminder")
    copy = {
        "gentle": "🌱 Nice streak! A 5-minute lesson keeps it growing.",
        "urgent": f"🔥 Your {streak}-day streak ENDS TONIGHT. Study now or lose it!",
    }.get(str(reminder))
    if copy:
        st.warning(copy)
        c1, c2 = st.columns(2)
        if c1.button("I'll come back tomorrow"):
            once("daily_return")
        if c2.button("Turn reminders off"):
            once("reminder_opt_out")

    # E4 onboarding_flow - only exposed to new learners (segment: new_learners)
    if int(days) <= 7:
        _, flow = exp("onboarding_flow")
        st.subheader("Welcome! 👋")
        if flow == "checklist":
            st.checkbox("Pick a topic")
            st.checkbox("Finish your first lesson")
            st.checkbox("Set a daily goal")
        else:
            st.info("Classic tour: Step 1 of 3 - choose a topic from the menu.")
        c1, c2 = st.columns(2)
        if c1.button("Finish onboarding"):
            once("onboarding_completed")
        if c2.button("Skip onboarding"):
            once("onboarding_skipped")

    # Stale flag on purpose: fully rolled out long ago -> cleanup candidate for the guardian.
    if flags.flag("legacy_leaderboard", ss.uid, traits)[0]:
        st.subheader("🏆 Leaderboard")
        st.table({"Learner": ["ana", "bo", "chen"], "XP": [980, 940, 910]})


def lesson():
    # E2 lesson_length - JSON remote config
    _, raw = exp("lesson_length")
    cfg = flags.parse_lesson_length(raw)
    st.subheader(f"Lesson: Python lists ({cfg['minutes']} min, {cfg['cards']} cards)")
    for i in range(cfg["cards"]):
        st.caption(f"Card {i + 1}/{cfg['cards']}")
    if st.button("Start lesson"):
        once("lesson_started")
    if st.button("Finish lesson"):
        once("lesson_completed", cfg["minutes"])
    if flags.flag("ai_tutor", ss.uid, traits)[1] == "on":  # staged rollout, not an experiment
        st.button("🤖 Ask the AI tutor")


def quiz():
    # E3 quiz_timer - numeric value-as-string
    _, raw = exp("quiz_timer")
    seconds = flags.parse_quiz_timer(raw)
    st.subheader("Quiz: 3 questions")
    st.caption(f"⏱️ {seconds}s timer" if seconds else "Untimed")
    if flags.flag("beta_exam_mode", ss.uid, traits)[0]:  # segment flag: pro_users
        st.info("🧪 Exam mode (beta) is available to your plan.")
    st.radio("What does `len([1,2,3])` return?", ["2", "3", "4"], key="q1")
    c1, c2 = st.columns(2)
    if c1.button("Submit"):
        if ss.q1 == "3":
            once("quiz_passed")
        else:
            st.error("Not quite.")
    if c2.button("Give up"):
        once("quiz_abandoned")


def pricing():
    # E1 pricing_layout - 3-arm string; revenue is a numeric metric
    _, layout = exp("pricing_layout")
    st.subheader("Go Pro")
    tiers = {
        "monthly_first": [("Monthly", 9), ("Annual", 79)],
        "annual_first": [("Annual (save 27%)", 79), ("Monthly", 9)],
        "three_tier": [("Basic", 5), ("Pro", 9), ("Team", 24)],
    }.get(str(layout), [("Monthly", 9), ("Annual", 79)])
    for name, price in tiers:
        if st.button(f"Subscribe - {name}: ${price}"):
            once("subscription_started")
            once("revenue", price)


def simulator():
    st.subheader("Simulator")
    st.caption("Uses learnloop/knobs.py. Opens many identities, so each run adds real events to your environment.")
    n = st.number_input("Users", 10, 5000, knobs.SIM_USERS, step=50)
    if st.button("Run simulation"):
        bar = st.progress(0)
        rng = random.Random(knobs.SEED)
        tally = {}
        for i in range(int(n)):
            for e, arm in sim.simulate_user(rng):
                tally.setdefault(e, {}).setdefault(arm, 0)
                tally[e][arm] += 1
            bar.progress((i + 1) / int(n))
        flags.flush()
        st.json(tally)


{"Home": home, "Lesson": lesson, "Quiz": quiz, "Pricing": pricing, "Simulator": simulator}[page]()

with st.expander("Debug: resolved experiments"):
    st.json({k: list(v) for k, v in ss.resolved.items()})
