# fair-check

Claude skill that checks whether a research project folder is FAIR and builds
a deposit version, following the booklet *Hands-on Open Science*
(Università di Padova, https://mar-cald.github.io/fair/).

- `SKILL.md`: the workflow (inventory, triage, report); read every time the skill runs.
- `references/`: details read only when needed (one file per area, plus the booklet rules and the experiment-software notes).
- `scripts/`: the Python tools (scan, run code, manuscript numbers, deposit build, dictionaries, Psych-DS).
- `assets/licenses/`: official license texts.
- `evals/`: test cases. Each folder is a small made-up project with known problems, the request, and what a good report must say (`graders/`); they run with `claude plugin eval .` or by hand with skill-creator. `evals/check_scripts.py` checks the Python scripts alone on the same folders, without a model, in a few seconds: run it after every change to `scripts/`.
