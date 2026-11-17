---
name: "fair-check"
description: "Checks whether a research project folder is FAIR and ready to deposit on Zenodo, PsychArchives or another repository, following the Unipd \"Hands-on Open Science\" booklet, then builds a clean deposit version. It first asks what to check (default: everything). It adapts to the material: data (consistency, names, formats, README, dictionary, license, personal data), code (does it run, packages, seeds), manuscript (do the reported numbers come out of the code). Use it whenever someone asks to check, review, clean up or make FAIR a research folder, dataset or OSF/GitHub/Zenodo deposit, or asks if their data, code or preprint are ready to share, even without saying \"FAIR\"; also for Italian requests like \"controlla la mia cartella\" or \"prepara la cartella per Zenodo\"."
---

# FAIR check and deposit version of a research project

The question behind every check: *can a person who does not know the authors,
and cannot write to them, find these data, open them, understand them and
reuse them?* Every finding says what that person would run into, and how to
fix it.

The rules come from the booklet *Hands-on Open Science* (Università di Padova,
https://mar-cald.github.io/fair/), summarised in `references/fair-rules.md`.
Read a section of it (see its Contents) only when a finding needs the rule
itself: which license fits, what a README must contain, the deposit layout.
Points marked *(skill)* there extend the booklet.

The scripts in `scripts/` do the mechanical work: they read the files, count,
recompute and run the code, and print short summaries. Do not redo by hand
what a script reports, and do not open its full JSON except for the detail of
one point (each summary gives the file and the key).

## Four rules that hold everywhere

1. **The researcher's folder is never modified.** It is often the only copy.
   Everything the skill writes goes to a temporary directory or to the deposit
   version, a separate folder.
2. **Change as little as possible.** People do not trust a deposit in which
   they no longer recognise their own files and code. Every change to their
   code is the smallest one that solves the problem, keeps their style (their
   own style skill if they have one, otherwise the style of their existing
   scripts), and is listed in the hand-over. Corrections to their data are
   proposed, never applied without agreement.
3. **Talk and write the report in the researcher's language** (often Italian).
   File names, column names and code stay as they are.
4. **A flag is a question, not a finding.** Whatever a script, an error
   message or a first comparison turns up is a hypothesis about the folder. It
   becomes a finding only after you have tried to explain it with what the
   folder contains (see "Before the report"). A wrong alarm is not harmless
   caution: the researcher spends time chasing it and may start doubting
   results that are correct, and a wrong alarm about a reported number is the
   most damaging thing this skill can produce. The aim is not fewer findings,
   but findings that hold.

## Step 0 — Inventory

If the folder is not given, ask. Extract attached zips, and archives inside the
project, into a temporary directory. Then:

```bash
python3 <skill-dir>/scripts/fair_scan.py <project-folder> --out <tmp>/fair_scan.json
```

It prints a short summary (also saved as `<tmp>/fair_scan_summary.md`): work
from it. It opens with what this environment can do: a missing R, `pdftotext`,
`openpyxl` or `pyreadstat` is a limit of this environment, not a problem of the
folder ("not checked here, because R is not available", never "the code does
not run"). Findings are grouped by report section, each with the booklet page
to link, and labelled **[certain]** (established by the scan: report it after a
glance) or **[to check]** (a rule that fired and may not apply: verify it in the
data, the README or the code, and drop it if it does not hold: 999 is a
missing-value code in an age column, not in trial numbers; `rt` in a table of
results is not a reaction time). "Small things" get one sentence each in the
report.

The judgement is yours: is it a problem for a stranger reusing the data, how
serious, what to do. Read what a scan cannot judge: the README in full, the
code where a finding points, the manuscript. Then look beyond the list: does
the experiment make sense as recorded (conditions and stimuli vary as the
design says, accuracy follows from the response), does the analysis fit the
design (trials of the same person treated as independent observations), does
the code do what the text says? A short script on counts and summaries
answers these; report what you find even if no rule asked for it. **Never print data files whole**
(`cat`, long `head`): they can be large and hold personal data. For a check
the scan does not do, write a short script that prints counts or summaries,
and never the values of columns flagged as personal data. Absent material is not a problem
unless it is needed (a data-only deposit is complete without code).

## Step 0b — Triage

The summary ends with **the questions to ask** for this folder, with their
defaults. Ask them in **one round** (with the question tool if available,
otherwise one message with numbered questions and their defaults), skipping
those the request already answers ("solo il codice"). If the answer is "fai
tutto", or no answer comes (nobody there, a scheduled run), use the defaults.
The report says at the top which choices were used. Areas not chosen are "not
checked, on request", not problems. Whenever data are checked or the deposit
is built, check personal data too: a public deposit cannot be taken back. If
the manuscript numbers are chosen without the code, use the outputs already in
the folder, or ask to run the code. Material the researcher gives
(preregistration, protocol) is evidence, not copied into the deposit unless
asked. The skill's own tools stay Python whatever language is chosen.

## Step 1 — Check

Every command costs a round trip in which the whole conversation is read
again: group what you can. Read the files a scan cannot judge together, in one
command (the README, the scripts, the manuscript; never the data files whole).
If code or manuscript are chosen, run their checks in one call:

```bash
python3 <skill-dir>/scripts/check_all.py <project-folder> --tmp <tmp> --areas code,manuscript [--scripts <in run order>]
```

It runs the scripts in a copy (and again with `setwd()` removed, if that is
what stops them), checks the manuscript against itself and looks for its
numbers in the output of the run that worked. Leave out an area not chosen.

For each chosen area, read the instruction file the summary names, and follow
it: `references/check-data.md`, `check-code.md`, `check-manuscript.md`. For
files from experiment or survey software, the summary also names the sections
of `references/software-exports.md` to read; their checks (rows to filter,
units, exclusions, platform IDs, accuracy against the response) are already in
the scan summary.

## Before the report — explain every discrepancy

The checks say where to look, not what is wrong. A recomputed correlation that
differs from Table 2, a reversed item that is not the reverse of its original,
a total that does not match its items, a value outside the range, a script that
stops, a file that seems missing: each is the start of a diagnosis. Do this
before writing the report: a report drafted from preliminary results tends to
keep them.

For each discrepancy, list the explanations that could produce it and test
them, most likely first, with the material in the folder: the script that
produced the number or the column (what the code does defines what the
manuscript reports), the README, the dictionary, the methods section. Then
rerun the computation with the sample, variable and method you found. For a
correlation, a mean, an SD or an N that can be computed from a data file, run
`recompute.py` before writing code of your own: in one call it tries Pearson,
Spearman and Kendall, with and without the exclusions you give, missing-value
codes as values or as missing, complete cases or pairwise, the SD with n or
n − 1, and says which variant gives the reported value:

```bash
python3 <skill-dir>/scripts/recompute.py r <data> <x> <y> --reported .34 --where "excluded == 0"
python3 <skill-dir>/scripts/recompute.py desc <data> <col> --mean 23.8 --sd 4.1 --n 180 --where "..."
python3 <skill-dir>/scripts/recompute.py n <data> --n 180 --id <participant column> --where "..."
```

The usual explanations:

- **a different method**: Spearman or Kendall instead of Pearson (the most
  common cause of a correlation that does not match: look for
  `method = "spearman"`, "rank", "non-parametric", a note under the table),
  partial vs zero-order, Welch vs Student, one- vs two-tailed, type of sums of
  squares, a different prior or model;
- **a different variable**: the processed file instead of the raw one, a
  standardised, centred or log version, a score on a subset of items or with
  prorated missing items; a reversed item uses the *scale's* minimum and
  maximum (from the README, the dictionary or the manuscript), not the values
  observed, and may already be reversed in the export or in the code;
- **a different sample**: the exclusions the scripts or the manuscript apply,
  a subgroup, one time point or condition, complete cases vs pairwise, trials
  vs participant means; missing-value codes (999, -99) counted as values;
- **another form or version**: rounding, percent vs proportion, ms vs s, BF01
  vs BF10, log BF, a sign flipped by the reference level (`manuscript_numbers.py`
  tests these already), or a folder that is not the version behind the
  manuscript;
- for code: an error from this environment (a missing package, a path, a
  missing interpreter), or from an earlier script that failed (`run_code.py`
  marks these).

Then decide, and say on what basis:

- **explained**: not a problem with the results, possibly a documentation
  finding ("the README does not say the correlations are Spearman");
  optionally list the apparent discrepancies you resolved, in one line;
- **confirmed**: no explanation reproduces the reported value. Report it with
  the evidence and the explanations ruled out ("not Spearman, not rounding, not
  the exclusions in `02_clean.R`: on the 180 participants analysed r = .21,
  Table 2 reports .34");
- **unresolved**: you could not test every plausible explanation (no code, no
  R, data not in the folder). Say what you tried and what remains, as a
  question for the researcher, not as an error.

Only confirmed discrepancies go under "Results that may be affected";
unresolved ones go in their own section, worded as open questions. Stop when
the evidence settles the question, not when the first check fails.

## Step 2 — Report

One status per area: ✅ fine, ⚠️ needs work, ❌ missing or blocking (without
emoji: "ok", "da sistemare", "mancante" in the researcher's language). Under
each, concrete findings: file, column, line, what a reuser would run into.
Fine areas get one line. Leave out areas not present or not chosen (list the
latter in the opening paragraph). Every heading and the text are in the
researcher's language ("Riepilogo", "Dati e coerenza", "Che cosa sistemare per
primo"); the labels [certain] and [to check] are for you, never in the report.

**Two kinds of problem.** Most findings make the folder hard to reuse (no
README, a file in Excel). A few mean that a number may be wrong: a data error
that reaches the analysis, a total computed differently from its items, a
manuscript value that does not come out of the data or the code, an exclusion
the text describes and the code does not do. Once confirmed, these go in their
own block at the top, "Results that may be affected".

**Evidence for every claim about the data or the numbers**: the count or value
behind it ("in 211 of 234 rows", "file 96.16, Table 1 89.77", "participants
P045, P088"), never "some rows" or "probably". Write findings as facts and
actions ("`data/questionario.xlsx` has no open copy: a reader without Excel
cannot open it"), never generic advice. Each section links its booklet page
once (from the scan summary).

```markdown
# FAIR check — <project name>

<One paragraph: what the folder contains, which checks were done (material
found and triage choices), whether a stranger could reuse it today, the single
biggest obstacle.>

## Results that may be affected
<only confirmed discrepancies that may change a number: what, where in the
manuscript, value reported vs value in the data or output, evidence,
explanations ruled out, what to do. The researcher may have to correct the
paper, not only the folder. Leave the block out if there are none; if there
are, the report ends by asking whether to rerun the analysis with the
corrections (step 2b).>

## Open questions
<only if any: unresolved discrepancies, what was tried, what remains>

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ✅/⚠️/❌ | ... |
| Folder structure and names | ... | ... |
| Formats | ... | ... |
| README | ... | ... |
| Data dictionary | ... | ... |
| License | ... | ... |
| Code runs | ... | ... |
| Declared packages | ... | ... |
| Manuscript and reported numbers | ... | ... |
| Personal data and third-party material | ... | ... |

## 1. Data files and consistency
## 2. Folder structure and names
## 3. Formats
## 4. README
## 5. Data dictionary
## 6. License
## 7. Code
## 8. Manuscript and reported numbers
<a table: statistic, where in the manuscript, reported value, value in the
output (with the script), status>
## 9. Personal data and third-party material

## What to fix first
<at most 5-6 concrete actions, ordered by how much they block reuse>

## The deposit version
<what step 3 will build, and the decisions needed from the researcher>
```

Show the report in the conversation; if wanted as a file, save it outside the
project folder.

## Step 2b — Rerun the analysis with the corrections (ask first)

If the report has confirmed results that may be affected (a data error that
reaches the analysis, a score computed wrongly, a bug in a script, an
exclusion the text describes and the code does not do), ask at the end of the
report whether to rerun the analysis with the corrections, to see how much
the results change. If nobody answers, do not: it can take time, and the
corrections are the researcher's decision.

If yes, in a copy only (`run_code.py ... --keep`): apply each correction the
smallest way (in the cleaning script, or in the copy of the data when there
is no code), rerun the scripts into a new logs folder, and compare the two
runs:

```bash
python3 <skill-dir>/scripts/compare_runs.py <tmp>/logs <tmp>/logs_fixed --manuscript <tmp>/manuscript.txt
```

It lists the numbers that change and, first, those the manuscript reports.
Report, for each correction, which reported results change and by how much
("r = .34 → .29, p = .003 → .02"), whether a conclusion of the paper changes,
and which results stay the same. With several corrections, rerun once with
all of them, and once per correction only if the researcher wants to know
which one matters. With no code, recompute the affected numbers with
`recompute.py` on the corrected copy of the data. The researcher's folder
stays as it is; whether the corrections go into the deposit is decided in
step 3.

## Step 3 — Deposit version

Read `references/deposit.md`: plan and decisions, build, dictionaries, README
and LICENSE, verification, zip and hand-over.
