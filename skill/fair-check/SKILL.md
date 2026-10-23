---
name: fair-check
description: Checks whether a research project folder (data, code, README, license) is FAIR and ready to be deposited on Zenodo, PsychArchives or another repository, following the rules of the Unipd "Hands-on Open Science" booklet. It inspects the data for inconsistencies, the folder structure and file names, the README, the data dictionary, the license choice, and whether the analysis code runs and which packages it needs. It then offers to draft the missing data dictionaries and README sections. Use this skill whenever someone asks to check, review, audit or "make FAIR" a research repository, project folder, dataset or OSF/GitHub/Zenodo deposit, or asks whether their data and code are ready to share or publish, even if they don't say "FAIR". Also use it for requests in Italian such as "controlla la mia cartella", "è pronta da depositare?" or "verifica se i miei dati sono FAIR".
---

# FAIR check of a research project folder

The question behind every check is the one the booklet starts from: *can a
person who does not know the authors, and cannot write to them, find these
data, open them, understand them and reuse them?* Every finding in the report
should say what that person would run into, and how to fix it.

The rules come from the booklet *Hands-on Open Science* (Università di Padova,
https://mar-cald.github.io/fair/). Read `references/fair-rules.md` before writing
the report: it has the naming rules, the README sections, the data dictionary
columns, the license recommendations and the page to link for each topic.

## How the work is organised

1. **Check** (read-only): scan the folder, look at the data, read the README and
   the license, run the code in a temporary copy.
2. **Report**: one structured report, with a short list of what to fix first.
3. **Fix** (only what the researcher agrees to): draft data dictionaries,
   README sections, LICENSE file.

Nothing in the researcher's folder is created, renamed or modified during
steps 1 and 2. Researchers often run this on the only copy of their project;
an unexpected change there can damage the work they are about to deposit.

Write the report and talk to the researcher in the language they use (often
Italian). Keep file names, column names and code in their original form.

## Step 1 — Check

### 1a. Find the folder

If the researcher has not said which folder to check, ask. If they attached a
zip, extract it to a temporary directory and work on that.

### 1b. Run the scanner

```bash
python3 <skill-dir>/scripts/fair_scan.py <project-folder> --out <tmp>/fair_scan.json
```

Write the output to a temporary directory, not into the project. The JSON has
these sections: `inventory`, `root_entries`, `naming`, `formats`, `structure`,
`readme`, `licenses`, `data` (one entry per CSV/TSV, with per-column type,
range, missing-value codes and detected issues), `dictionaries` (which data
files have a dictionary and which columns are missing from it), `code`
(packages, absolute paths, `setwd`, missing referenced files),
`cross_file_type_inconsistencies` and `cross_file_participants`.

Two checks concern participants. For each data file the scanner looks for
the participant ID column and lists in `within_participant_inconsistencies`
the columns that should have one value per person (age, sex, group, or any
column that is constant for almost everyone) but have more than one for
some participants. In `cross_file_participants` it compares files that share
participants: IDs present in only one file, ID columns with different names,
IDs written differently (`sub-01` vs `1`), and participant-level columns
(e.g. age) whose values disagree between files.

The scanner applies fixed rules (patterns in names, counts, ranges). Its
findings are a starting point: read them, verify what looks surprising, and
drop false positives. For example, a column flagged as "possible numeric
missing-value codes: 999" is a real problem in an age column and not a
problem in a column of trial numbers.

### 1c. Look at the data with judgement

The scanner reports types and ranges; it cannot tell whether a value makes
sense. Use the column names, the dictionary and the README to judge, and look
for:

- values outside a plausible range (negative reaction times, age 250, a Likert
  item scored 8 on a 1–7 scale, accuracy above 1 or 100);
- the same variable coded differently in different files (`F`/`M` in one,
  `1`/`2` in another). The scanner compares values only between columns with
  the same meaning and coding, so check by hand whether the codes agree
  participant by participant (is everyone with `gender = F` coded the same
  `sex`?);
- the number of participants: if the README says N = 100, how many unique IDs
  are in the data (`n_participants`)?
- proprietary files (`.xlsx`, `.sav`) with no open copy beside them. If R is
  available, you can read them (`readxl::read_excel`, `haven::read_sav`) to
  check them like the CSVs, but do not convert them yet: conversion belongs
  to step 3.

When you need to see actual values, look at summaries (`head` of a few
rows, counts of unique values), not at whole files. Data files can be large,
and they can contain personal data that should not be printed into the
conversation. If the scanner flags `possible_personal_data`, do not print
those columns' values; report the column name and why it was flagged.

### 1d. README and license

Read the README in full. The scanner tells you which of the booklet's
sections appear (`readme.sections`) and which files are never mentioned
(`readme.files_not_mentioned`), but only reading it tells you whether the
description would let a stranger understand the study: whether it says what
a row of each data file is, when and how data were collected, and in which
order the scripts run.

For the license, decide which license covers each component (data, code, own
materials, third-party materials), using the LICENSE file(s), the README
license section and any metadata file (`CITATION.cff`, `DESCRIPTION`).
Then judge each against the table in `references/fair-rules.md` section 6.
The typical problems are: no license; one license for everything; a
Creative Commons license on code; MIT/GPL on data; CC BY-NC or CC BY-ND on
data; a LICENSE file that names a license without its full text; third-party
instruments (published tests, copyrighted stimuli) included in the folder.

### 1e. Does the code run?

Find the run order: the README first, then numbered file names. Then run:

```bash
python3 <skill-dir>/scripts/run_code.py <project-folder> [scripts in order] --timeout 600
```

The script copies the project to a temporary directory and runs everything
there from the project root, so outputs, caches and modified files never reach
the researcher's folder. It reports, per script: success or error, the last
lines of the error, missing packages, and the files it created or modified.

Before running, tell the researcher that you are about to run their code in a
copy, and how many scripts there are. If the scanner shows heavy analyses
(Bayesian models, `brms`, `stan`, simulations, bootstraps) mention that they may
hit the 10-minute timeout per script and ask whether to run them anyway or
with a longer timeout.

If scripts fail because packages are missing, **do not install them on your
own**: installing changes the researcher's R or Python setup. List the
missing packages and ask. With permission, install them
(`Rscript -e 'install.packages(c(...))'`, `pip install ...`) and run again. The
fact that packages were missing is itself a finding: the project does not
declare its dependencies.

When a script fails, the scripts after it often fail only because they read
the files it should have produced. Report the first failure as the cause,
and the later ones as consequences, not as separate problems.

If the first failure is a portability problem — a `setwd()`, an absolute
path, a file read from a path relative to the script's folder — the run has
not yet told you whether the analysis itself works. Find out in a copy:

```bash
python3 <skill-dir>/scripts/run_code.py <project-folder> --keep
```

`--keep` leaves the temporary copy and prints its path (`copy`). In that copy,
and only there, remove the `setwd()` line or turn the absolute path into
one relative to the project root, then run the scripts again from the copy
with `run_code.py <copy>`. Report the two results separately: "fails as
deposited because of X; once X is fixed, it runs" (or "it then fails at Y").
This second run is often where the substantive problems show up: look at
what the scripts produce (the cleaned data, the model output) and check
whether the problems found in step 1c — impossible values, missing-value
codes, duplicates — survive the cleaning and reach the analysis. Delete the
copy when done.

Things to report from the run:

- which scripts run from a clean copy and which fail, with the reason in
  plain words (a missing file, an absolute path, a missing package, an error
  in the code);
- scripts that work only from their own folder (`note` in the output);
- scripts that **modify** files in `data/raw/` (raw data must stay
  read-only);
- outputs that the README says are produced but that no script creates.

If no interpreter is available (no R on the machine, a MATLAB or SPSS project),
say so and limit the code check to the static part: packages, paths, files.

### 1f. Packages

From the scanner (`code.all_packages`, per-file `packages`) build the list of
packages the project needs, and compare it with what the project declares
(`renv.lock`, `requirements.txt`, README). If R is available, get the installed
version of each package
(`Rscript -e 'cat(sapply(c("pkg1","pkg2"), function(p) as.character(packageVersion(p))))'`)
to write them into the README later.

## Step 2 — Report

Use this structure. Each area gets one status: ✅ fine, ⚠️ present but needs
work, ❌ missing or blocking. Under each area, list the concrete findings: the
file, the column, the line, what a reuser would run into. Do not pad areas
that are fine; a single line is enough for those.

```markdown
# FAIR check — <project name>

<One paragraph: what the folder contains (N data files, N scripts, ...),
and an overall judgement: could a stranger reuse it today? What is the
single biggest obstacle?>

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
| Personal data | ... | ... |

## 1. Data files and consistency
## 2. Folder structure and names
## 3. Formats
## 4. README
## 5. Data dictionary
## 6. License
## 7. Code
## 8. Personal data and third-party material

## What to fix first
1. <the most blocking problem, with the concrete action>
2. ...
(at most 5-6 items, ordered by how much they block reuse)

## What I can do now
<the fixes from step 3 that apply to this project, as a short list>
```

Each section links the relevant booklet page (from `references/fair-rules.md`)
once, so the researcher can read the reasoning there.

Write findings as facts and actions: "`data/questionario.xlsx` has no CSV
copy: a reader without Excel cannot open it. Save it as
`data/questionnaire.csv` and keep the .xlsx in `data/raw/`." Avoid generic
advice that does not name a file.

Show the report in the conversation. If the researcher wants it as a file,
save it **outside** the project folder unless they ask otherwise, so it does
not end up in the deposit.

## Step 3 — Fix, with permission

After the report, offer the fixes that apply and wait for the researcher to
choose. Write new files only after a yes; never overwrite an existing file
without showing what changes. Never rename files or columns on your own:
scripts refer to them by name, and renaming breaks the code. If the
researcher wants renames, update every reference in the scripts and run the
code again to check it still works.

### Data dictionary

For each data file without a dictionary:

```bash
python3 <skill-dir>/scripts/draft_dictionary.py <data.csv>
```

It writes `<stem>_dictionary.csv` next to the data file, with the booklet's
nine columns. `variable_name`, `type`, `allowed_values`, `missing_values` and
the list of codes come from the data; `label`, `unit`, `source` and the
meaning of each code are `TODO`.

Then fill the `TODO`s you can support with evidence: a label from a README
description, a unit from the code (`rt * 1000`, a column named `rt_ms`), the
meaning of codes from a `factor(..., labels = ...)` or `recode()` in the scripts.
When the evidence is indirect, write the value and add "to check" in `notes`.
Leave `TODO` where nothing supports a value. An invented label is worse than a
missing one: it looks documented, so nobody checks it.

For an existing but incomplete dictionary, add the missing rows and columns
instead of creating a new file.

### README

If there is no README, create `README.md` with the eight sections of the
booklet (template in `references/fair-rules.md` section 4), filling what you
know from the folder and leaving `TODO` for what only the authors know
(authors, ORCID, collection dates, DOIs).

If the README exists, add only the missing sections. In every case, the
"How to reproduce" section should contain what the code check established:

- software and version (`R 4.4.1`, `Python 3.12`);
- the packages to install, with versions, ready to copy
  (`install.packages(c("tidyverse", "lme4"))`);
- the order in which the scripts run and what each one produces;
- if there is an `.Rproj`, to open it first (it sets the working directory).

Write it in the language of the existing README; with no README, in English,
the language reusers are most likely to share. Then suggest `renv` for exact
versions (`renv::init()` then `renv::snapshot()`): running it changes the
project (it creates `renv/` and `renv.lock`), so propose it, do not run it.

### License

The license is the authors' decision: propose, do not choose. Recommend
following the booklet (data CC0-1.0, code GPL-3.0 or MIT, own materials CC BY
4.0) and explain any problem found in step 1. Once they decide:

- add the "License" section to the README with what applies to what
  (template in `references/fair-rules.md` section 6);
- write the `LICENSE` file with the **full official text**. For MIT, write it
  with the year and the copyright holders. For the others, download the text
  from the official URL listed in `references/fair-rules.md` (ask before
  downloading). Do not write long license texts from memory: a
  paraphrased license is not the license. With several licenses, use one
  file per license (`LICENSE_DATA`, `LICENSE_CODE`) or one file with
  clearly separated sections.

### Other fixes

- Open-format copies of proprietary data files (`.xlsx` → `.csv`, `.sav` →
  `.csv` plus a dictionary built from its value labels), keeping the original
  in `data/raw/`.
- Fixing absolute paths and `setwd()` in scripts, replacing them with paths
  relative to the project root (or `here::here()`), then running the code
  again to confirm.

After any fix that touches code, run `run_code.py` again and report the
result.
