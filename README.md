# LearnLoop (experiment lab)
Tiny Streamlit micro-learning app for exercising the experiment guardian: 5 pages, 5 experiments, 6 plain flags.
Setup values for the Flagsmith console: `SETUP.md`. Bias the results: `learnloop/knobs.py`.

    py -m pip install -r requirements.txt
    py -m streamlit run app.py
    py -m learnloop.sim --users 600
    py -m pytest -q
