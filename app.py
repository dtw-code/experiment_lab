"""LearnLoop - a micro-learning app that exists to exercise the experiment guardian.

    py -m streamlit run app.py

Four learner pages plus a simulator, five running experiments, six plain flags. What each experiment
changes on screen and which verdict it is built to produce: EXPERIMENTS.md. What to create in the
Flagsmith console: SETUP.md. Which arm wins: learnloop/knobs.py.

The buttons here are for hand-testing one learner; `py -m learnloop.sim` produces the real traffic.
"""
import random
import uuid

import streamlit as st

from learnloop import experiments, flags, knobs, sim

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


def arm(name: str):
    """This learner's arm for an experiment flag; the exposure is recorded once per session."""
    if name not in ss.resolved:
        ss.resolved[name] = flags.read_experiment_flag(name, ss.uid, traits)[1]
    return ss.resolved[name]


def first_time(event: str) -> bool:
    """True once per session per event, so button mashing cannot inflate a metric.

    Every conversion below is then a literal `flags.track_event(` call, which is what `cleanup.yaml`
    protects with `keep_patterns`: a cleanup may delete a flag's branch but never the line that
    records the metric.
    """
    if event in ss.fired:
        return False
    ss.fired.add(event)
    st.toast(f"tracked `{event}`")
    return True


# ---------------------------------------------------------------- global flags (kill switch, overrides)
if flags.read_flag("maintenance_mode", ss.uid, traits)[0]:
    st.error("🛠️ LearnLoop is down for maintenance. (flag `maintenance_mode` is ON)")
    st.stop()

with st.sidebar:
    if flags.read_flag("support_chat", ss.uid, traits)[0]:
        st.success("💬 Priority support chat is on for you (flag `support_chat`)")

st.title("🔁 LearnLoop")


# ---------------------------------------------------------------- pages
def home():
    goal = flags.parse_int(flags.read_flag("daily_goal_xp", ss.uid, traits)[1], 20)
    st.metric("Daily goal (flag `daily_goal_xp`)", f"{goal} XP")

    # E5 streak_reminder -> INCONCLUSIVE. Two goal metrics, daily_return and streak_continued.
    copy = experiments.streak_reminder_copy(arm("streak_reminder"), int(streak))
    st.subheader("Today")
    if copy:
        st.warning(f"🌱 {copy}")
    c1, c2 = st.columns(2)
    if c1.button("I'll come back tomorrow") and first_time("daily_return"):
        flags.track_event("daily_return", ss.uid, None, traits)
    if c2.button("Keep the streak alive") and first_time("streak_continued"):
        flags.track_event("streak_continued", ss.uid, None, traits)

    # Stale flag on purpose: fully rolled out long ago, so `guardian cleanup` should offer to remove it.
    if flags.read_flag("legacy_leaderboard", ss.uid, traits)[0]:
        st.subheader("🏆 Leaderboard")
        st.table({"Learner": ["ana", "bo", "chen"], "XP": [980, 940, 910]})


def lesson():
    st.subheader("Lesson: Python lists (10 min, 8 cards)")
    for i in range(8):
        st.caption(f"Card {i + 1}/8")

    # E4 lesson_loading -> SEVERE_HARM. Primary metric lesson_load_ms is the MEAN of a numeric value.
    load_arm = arm("lesson_loading")
    st.caption(f"Content loading: {load_arm}")
    load_ms = experiments.lesson_loading_ms(load_arm)
    if st.button("Start lesson") and first_time("lesson_load_ms"):
        flags.track_event("lesson_load_ms", ss.uid, load_ms, traits)
    if st.button("Finish lesson"):
        st.success("Lesson finished.")

    # E3 help_widget -> SYSTEMIC_FAILURE. The ticket rate breaches its ceiling on control too.
    st.divider()
    hint = experiments.help_widget_hint(arm("help_widget"))
    if hint:
        st.caption(f"💡 {hint}")
    if st.button("Contact support") and first_time("support_ticket_opened"):
        flags.track_event("support_ticket_opened", ss.uid, None, traits)

    if flags.read_flag("ai_tutor", ss.uid, traits)[1] == "on":   # staged rollout, not an experiment
        st.button("🤖 Ask the AI tutor")


def quiz():
    # E2 quiz_timer -> HARMFUL_VARIANT. Primary metric quiz_passed.
    seconds = experiments.quiz_timer_seconds(arm("quiz_timer"))
    st.subheader("Quiz: 3 questions")
    st.caption(f"⏱️ {seconds}s timer" if seconds else "Untimed")

    if flags.read_flag("beta_exam_mode", ss.uid, traits)[0]:     # segment flag: pro_users
        st.info("🧪 Exam mode (beta) is available to your plan.")
    st.radio("What does `len([1,2,3])` return?", ["2", "3", "4"], key="q1")
    if st.button("Submit"):
        if ss.q1 == "3":
            if first_time("quiz_passed"):
                flags.track_event("quiz_passed", ss.uid, None, traits)
        else:
            st.error("Not quite.")


def pricing():
    # E1 pricing_layout -> WINNER. Primary metric subscription_started.
    st.subheader("Go Pro")
    for name, price in experiments.pricing_layout_tiers(arm("pricing_layout")):
        if st.button(f"Subscribe - {name}: ${price}") and first_time("subscription_started"):
            flags.track_event("subscription_started", ss.uid, None, traits)


def simulator():
    st.subheader("Simulator")
    st.caption("Uses learnloop/knobs.py. Opens many identities, so each run adds real events to your "
               "environment. The CLI (`py -m learnloop.sim`) is faster for large runs.")
    n = st.number_input("Learners", 10, 20000, knobs.SIM_USERS, step=100)
    if st.button("Run simulation"):
        bar = st.progress(0)
        rng = random.Random(knobs.SEED)
        tally = {}
        for i in range(int(n)):
            for flag, a in sim.simulate_learner(rng):
                tally.setdefault(flag, {}).setdefault(a, 0)
                tally[flag][a] += 1
            bar.progress((i + 1) / int(n))
        flags.flush()
        st.json(tally)


{"Home": home, "Lesson": lesson, "Quiz": quiz, "Pricing": pricing, "Simulator": simulator}[page]()

with st.expander("Debug: resolved experiment arms"):
    st.json({k: str(v) for k, v in ss.resolved.items()})
