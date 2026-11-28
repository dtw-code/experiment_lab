# LearnLoop (experiment lab)

A small Streamlit micro-learning app whose job is to exercise the experiment guardian. Five running
Flagsmith experiments, **one for each verdict the guardian can reach**, plus six plain flags.

| Read this | For |
|---|---|
| **[EXPERIMENTS.md](EXPERIMENTS.md)** | what each experiment changes on screen, and the verdict it produces |
| [SETUP.md](SETUP.md) | the flags, metrics and experiments as they exist in the console |
| `learnloop/knobs.py` | the numbers that decide who wins — each one has a test guarding its verdict |

```powershell
py -m pip install -r requirements.txt
```

```powershell
py -m streamlit run app.py
```

```powershell
py -m learnloop.sim --users 3000
```

```powershell
py -m pytest -q
```

## Shape of the code

    app.py                    the four learner pages plus a simulator page
    learnloop/flags.py        the only three Flagsmith calls: read_experiment_flag, read_flag, track_event
    learnloop/experiments.py  what each arm changes, as pure functions — one block per flag
    learnloop/knobs.py        the calibrated outcome table
    learnloop/sim.py          headless traffic: one identity request per learner, threaded
    tests/test_exp_<flag>.py  one file per experiment flag; nothing about a flag lives outside its own file

That last line is deliberate. `cleanup.yaml` tells the guardian how to find a flag reference
(`sdk_calls`) and what it must never touch (`keep_patterns`: every `flags.track_event(` line, because
a conversion metric outlives the experiment that measured it). Keeping each flag to one block per
file, and one test file of its own, is what makes `guardian cleanup` able to remove an experiment
cleanly and prove it by running `python -m pytest -q` before and after.
