---
name: "fair-check"
description: 'Checks whether a research project folder is FAIR and ready to deposit on Zenodo, PsychArchives or another repository, following the Unipd "Hands-on Open Science" booklet, then builds a clean deposit version. It first asks what to check (default: everything). It adapts to the material: data (consistency, names, formats, README, dictionary, license, personal data), code (does it run, packages, seeds), manuscript (do the reported numbers come out of the code). It reads exports from Qualtrics, PsychoPy, jsPsych, Gorilla, OpenSesame and E-Prime. The deposit has fixed folders, standard file names, CSV dictionaries, a README, licenses (CC0 data, GPL-3.0 code, CC BY 4.0 preprint), optionally Psych-DS, and a zip. Use it whenever someone asks to check, review, clean up or make FAIR a research folder, dataset or OSF/GitHub/Zenodo deposit, or asks if their data, code or preprint are ready to share, even without saying "FAIR"; also for Italian requests like "controlla la mia cartella" or "prepara la cartella per Zenodo".'
---

# FAIR check and deposit version of a research project

The question behind every check: *can a person who does not know the authors,
and cannot write to them, find these data, open them, understand them and
reuse them?* Every finding says what that person would run into, and how to
fix it.

The rules come from the booklet *Hands-on Open Science* (Università di Padova,
https://mar-cald.github.io/fair/), summarised in `references/fair-rules.md`.
Each report section links its booklet page once:

| Report section | Page to link |
|:--|:--|
| 1. Data, 2. Structure and names | https://mar-cald.github.io/fair/struttura-1.html#regole-generali (folders: `#struttura`) |
| 3. Formats | https://mar-cald.github.io/fair/struttura-1.html#in-che-formato-salvarli |
| 4. README | https://mar-cald.github.io/fair/struttura-1.html#readme |
| 5. Data dictionary | https://mar-cald.github.io/fair/struttura-1.html#data-dictionary |
| 6. License | https://mar-cald.github.io/fair/licenze.html |
| 7. Code | https://mar-cald.github.io/fair/esempio.html |
| 8. Manuscript, 9. Personal data | https://mar-cald.github.io/fair/risorse.html#checklist-prima-di-depositare |
| Deposit on Zenodo; Psych-DS | https://mar-cald.github.io/fair/zenodo.html; https://mar-cald.github.io/fair/struttura-2.html |

Read a section of `fair-rules.md` (see its Contents) only when a finding needs
the rule itself: which license fits, what a README must contain, the deposit
layout. Points marked *(skill)* there extend the booklet: no page to link.

If the scan recognises files from Qualtrics, PsychoPy, jsPsych, Gorilla,
OpenSesame or E-Prime, read section 0 of `references/software-exports.md` and
only the section of the program found (1 Qualtrics, 2 PsychoPy, 3 jsPsych,
4 Gorilla, 5 OpenSesame, 6 E-Prime, 7 others), not the whole file.

The details of each step are in separate files, read **only for the areas the
researcher chose** in the triage:

| Area | Read |
|:--|:--|
| Data and documentation (1a–1e, 1h) | `references/check-data.md` |
| Code (1f–1g) | `references/check-code.md` |
| Manuscript (1i) | `references/check-manuscript.md` |
| Deposit version (step 3) | `references/deposit.md` |

## Three rules that hold everywhere

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

## Step 0 — Inventory

If the folder is not given, ask. Extract attached zips, and archives inside the
project, into a temporary directory. Then:

```bash
python3 <skill-dir>/scripts/fair_scan.py <project-folder> --out <tmp>/fair_scan.json
```

It prints a **short summary** (also saved as `<tmp>/fair_scan_summary.md`):
work from it. The full JSON can be 100,000+ characters; open it only for the
detail of one point (the summary and the reference files name the key, e.g.
`data[3]`, `cross_file_participants`), never read it whole.

The summary has:

- **What this environment can do.** Missing R, `pdftotext`, `openpyxl` or
  `pyreadstat` are limits of this environment, not problems of the folder: the
  report says "not checked here, because …" (e.g. "the scripts were not run: R
  is not available in this environment"), never "the code does not run". Files
  not read are listed there too.
- **Findings by report section** (1–9), each with its file, column or line,
  labelled **[certain]** (established by the scan: a date of birth, an LFS
  placeholder, `setwd()`, a file read by a script and missing) or
  **[to check]** (a rule that fired and may not apply: a value beyond the range
  of the other items, two files coding a column differently, a column whose
  role was guessed from its name). Report [certain] findings after a glance;
  verify each [to check] one in the data, the README or the code, and drop it
  if it does not hold (999 is a missing-value code in an age column, not in
  trial numbers; `rt` in a table of results is not a reaction time).
- **Small things**, grouped (constant or empty columns, spaces around values):
  one sentence each in the report, not one finding per column.

The summary lists what the scan found; the judgement is yours: is it a
problem for a stranger reusing the data, how serious, what to do. Read what a
scan cannot judge: the README in full, the code where a finding points, the
manuscript. Which areas exist depends on the material found: do not mark
absent material as a problem unless it is needed (a data-only deposit is
complete without code).

## Step 0b — Triage

Doing everything costs time and tokens (running the code, a Bayesian model
taking an hour, checking every number of a manuscript). After the scan, which
is quick, and before any check, ask what to do: in **one round** (with the
question tool if available, otherwise one message with numbered questions and
their defaults), only the questions that apply to this folder, skipping those
the request already answers ("solo il codice", "solo il report"). If the
answer is "fai tutto", or no answer comes (nobody there, a scheduled run), use
the defaults. The report says at the top which choices were used.

1. **What should I do?** Data and documentation · does the code run · the
   manuscript numbers · the deposit version. *Default: everything.* Areas not
   chosen are "not checked, on request", not problems. Whenever data are checked
   or the deposit is built, the personal-data check (1h) is done too: a public
   deposit cannot be taken back. If the manuscript numbers are chosen without the code, use the
   outputs already in the folder, or ask to run the code.
2. **Do you have anything that helps me understand the study?**
   Preregistration, protocol, codebook, notes, the manuscript if not in the
   folder. *Default: no.* Used as evidence; not copied into the deposit unless
   asked.
3. **Should the deposit follow the Psych-DS standard?** *Default: no.*
   - *No*: folders (section 9 of the rules) and file names (sections 1 and 10:
     `study-x_task-y_data`) follow the standard anyway, but open formats keep
     their extension (`.csv`, `.tsv`, `.txt`, `.json`: all fine for FAIR) and
     no `.json` metadata file is created.
   - *Yes*: also data as comma-separated UTF-8 `_data.csv` and
     `dataset_description.json`; the deposit passes the Psych-DS validator.
4. **Where will you deposit it?** Zenodo (default), PsychArchives, other.

Only if the code is checked or the deposit is built, and there is code:

5. **R or Python?** For code the skill writes from scratch (a script making
   open copies, a cleaning script in a project without code). *Default: the
   language of the project's scripts; R if there are none.* The skill's own
   tools stay Python.
6. **Should I split long scripts?** *Default: yes.* Split by phase (cleaning,
   analysis, figures) at the points where one phase ends, without rewriting:
   the end of a piece saves what the next needs (`write.csv()` of the processed
   data, `saveRDS()` of a model), the start of the next reads it. If no, the
   script stays whole.
7. **Models already estimated?** (only with heavy models: brms, Stan,
   simulations, bootstraps) If saved fits exist: *default: do not re-estimate,
   use them.* If none: longer timeout, or skip.

## Step 1 — Check

For each chosen area, read its file (table above) and follow it.

## Step 2 — Report

One status per area: ✅ fine, ⚠️ needs work, ❌ missing or blocking (if you do
not use emoji, the words "ok", "da sistemare", "mancante" in the researcher's
language). Under each, concrete findings: file, column, line, what a reuser
would run into. Fine areas get one line. Leave out areas not present or not
chosen (list the latter in the opening paragraph).

The template below is in English: write every heading, the summary table and
the text in the researcher's language (in Italian: "Riepilogo", "Dati e
coerenza", "Che cosa sistemare per primo" ...). The scan's labels [certain] and
[to check] are for you: never copy them into the report; a finding you checked
is stated as a fact, one you could not settle says what remains to verify.

**Two kinds of problem.** Most findings make the folder hard to reuse (no
README, a file in Excel). A few mean that a number may be wrong: a data error
that reaches the analysis, a total computed differently from its items, a
manuscript value that does not come out of the data or the code, an exclusion
the text describes and the code does not do. These go in their own block at
the top, "Results that may be affected", with the number in the manuscript,
the number in the data or output, and which table or sentence changes: the
researcher may have to correct the paper, not only the folder. If there are
none, leave the block out.

**Evidence for every claim about the data or the numbers.** Each one carries
the count or value behind it, from the scan or from a check you ran: "in 211
of 234 rows", "file 96.16, Table 1 89.77", "participants P045, P088".
Never "some rows" or "probably": if you did not verify it, it is something to
check, said as such.

```markdown
# FAIR check — <project name>

<One paragraph: what the folder contains, which checks were done (material
found and triage choices), and whether a stranger could reuse it today. The
single biggest obstacle.>

## Results that may be affected
<only if any: what, where in the manuscript, value reported vs value in the
data or output, evidence, what to do>

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
## 9. Personal data and third-party material

## What to fix first
1. <the most blocking problem, with the concrete action>
(at most 5-6 items, ordered by how much they block reuse)

## The deposit version
<what step 3 will build, and the decisions needed from the researcher>
```

In section 8, a table: statistic, where in the manuscript, reported value,
value in the output (with the script), status. Each section links its booklet
page once. Write findings as facts and actions ("`data/questionario.xlsx` has
no open copy: a reader without Excel cannot open it"), never generic advice.
Show the report in the conversation; if wanted as a file, save it outside the
project folder.

## Step 3 — Deposit version

Read `references/deposit.md`: plan and decisions, build, dictionaries, README
and LICENSE, verification, zip and hand-over.
