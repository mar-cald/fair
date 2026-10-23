---
name: fair-check
description: 'Checks whether a research project folder is FAIR and ready to deposit on Zenodo, PsychArchives or another repository, following the Unipd "Hands-on Open Science" booklet, then builds a clean deposit version. It adapts to the material: data only (data consistency, names, formats, README, data dictionary, license, personal data), plus code (does it run, which packages), plus a manuscript or preprint (do the reported numbers come out of the code). The deposit version has fixed folder names, Psych-DS file names and dataset_description.json, CSV dictionaries, a complete README, licenses (CC0 data, GPL-3.0 code, CC BY 4.0 preprint) and a zip to upload. Use it whenever someone asks to check, review, clean up or make FAIR a research folder, dataset or OSF/GitHub/Zenodo deposit, or asks if their data, code or preprint are ready to share, even without saying "FAIR"; also for Italian requests like "controlla la mia cartella" or "prepara la cartella per Zenodo".'
---

# FAIR check and deposit version of a research project

The question behind every check is the one the booklet starts from: *can a
person who does not know the authors, and cannot write to them, find these
data, open them, understand them and reuse them?* Every finding in the report
should say what that person would run into, and how to fix it.

The rules come from the booklet *Hands-on Open Science* (Università di Padova,
https://mar-cald.github.io/fair/). Read `references/fair-rules.md` before writing
the report: it has the naming rules, the README sections, the data dictionary
columns, the licenses, the fixed folder layout of the deposit, the Psych-DS
rules and the manuscript checks, with the page to link for each topic.

## How the work is organised

0. **Inventory**: find out what the folder contains, and so which checks apply.
1. **Check** (read-only): data, structure, README, dictionary, license; then code
   and manuscript if present.
2. **Report**: one structured report, with a short list of what to fix first.
3. **Deposit version**: a new folder next to the original, with the fixed
   layout, the documentation and the licenses, verified and zipped.

The researcher's folder is never modified. Researchers often run this on the
only copy of their project; an unexpected change there can damage the work
they are about to deposit. Everything the skill writes goes into the deposit
version, which is a separate folder.

Write the report and talk to the researcher in the language they use (often
Italian). Keep file names, column names and code in their original form.

## Step 0 — Inventory

If the researcher has not said which folder to check, ask. If they attached a
zip, extract it to a temporary directory and work on that. Then run the scanner:

```bash
python3 <skill-dir>/scripts/fair_scan.py <project-folder> --out <tmp>/fair_scan.json
```

Write the output to a temporary directory, not into the project. The JSON has
these sections:

- **`materials_present`**: whether the folder has data, code, a manuscript.
- **`inventory`, `root_entries`, `naming`, `formats`, `structure`**: what is in
  the folder, how files are named and in which formats.
- **`readme`, `licenses`**.
- **`data`**: one entry per CSV/TSV, with per-column type, range,
  missing-value codes, detected issues, the participant ID column, and
  `within_participant_inconsistencies`.
- **`cross_file_participants`**: IDs present in only one file, ID columns
  with different names, IDs written differently (`sub-01` vs `1`), and
  participant-level values (e.g. age) that disagree between files.
- **`dictionaries`**: which data files have a dictionary, and which columns
  are missing from it.
- **`code`**: packages, absolute paths, `setwd`, files referenced but missing.
- **`manuscripts`**: candidate manuscript or preprint files.
- **`psychds`**: whether the folder already follows the minimum Psych-DS rules.

`materials_present` decides the checks:

| The folder has | Checks |
|:--|:--|
| data | 1a data, 1b structure and formats, 1c README, 1d dictionary, 1e license, 1h personal data |
| data + code | the above, plus 1f the code runs, 1g packages |
| data + code + manuscript | all of the above, plus 1i manuscript and reported numbers |

A manuscript without code still gets the 1i checks that do not need the code
(data availability statement, N and exclusions against the data, what can be
deposited). Code without data is checked for what it can be: it runs, or it
fails on missing data. Say at the start of the report which material was
found and so which checks were done; do not mark absent material as a
problem unless it is needed (a data-only deposit is complete without code).

The scanner applies fixed rules (patterns in names, counts, ranges). Its
findings are a starting point: verify what looks surprising, and drop false
positives. For example, "possible numeric missing-value codes: 999" is a real
problem in an age column and not in a column of trial numbers.

## Step 1 — Check

### 1a. Data

The scanner reports types, ranges and repeated-value problems; it cannot tell
whether a value makes sense. Use the column names, the dictionary and the
README to judge, and look for:

- values outside a plausible range (negative reaction times, age 250, a Likert
  item scored 8 on a 1–7 scale, a questionnaire total above its maximum);
- the same variable coded differently in different files (`F`/`M` in one,
  `1`/`2` in another). The scanner compares values only between columns with
  the same meaning and coding, so check by hand whether the codes agree
  participant by participant;
- the number of participants (`n_participants`) against what the README or
  the manuscript says;
- proprietary files (`.xlsx`, `.sav`) with no open copy. If R is available,
  read them (`readxl::read_excel`, `haven::read_sav`) to check them like the
  CSVs, and to see whether they contain the same data as the CSV next to them.

When you need to see actual values, look at summaries (`head` of a few rows,
counts of unique values), not at whole files. Data files can be large, and
they can contain personal data that should not be printed into the
conversation. If the scanner flags `possible_personal_data`, do not print
those columns' values; report the column name and why it was flagged.

### 1b. Structure, names, formats

From `naming`, `formats` and `structure`, against sections 1–3 of the rules.
Note also what would not belong in a deposit (section 9 of the rules): old
scripts, empty folders, system files, duplicates.

### 1c. README

Read it in full. The scanner tells you which of the booklet's sections appear
(`readme.sections`) and which files are never mentioned
(`readme.files_not_mentioned`), but only reading it tells you whether a
stranger would understand the study: what a row of each data file is, when
and how data were collected, in which order the scripts run.

### 1d. Data dictionary

From `dictionaries.coverage`: data files without a dictionary, columns not
described, names that do not match, values outside `allowed_values`, codes not
in `coding`. A dictionary in `.docx` or `.pdf` counts as present but not
machine-readable.

### 1e. License

Decide which license covers each component (data, code, manuscript, own
materials, third-party materials), using the LICENSE file(s), the README and
any metadata file (`CITATION.cff`, `DESCRIPTION`). Judge each against section 6
of the rules. Typical problems: no license; one license for everything; a
Creative Commons license on code; a software license (MIT, GPL) on data;
CC BY-NC or CC BY-ND on data; a LICENSE that names a license without its text;
third-party instruments or the publisher's PDF in the folder.

### 1f. Does the code run? (if there is code)

Find the run order: the README first, then numbered file names. Then:

```bash
python3 <skill-dir>/scripts/run_code.py <project-folder> [scripts in order] --timeout 600 --logs <tmp>/logs
```

The script copies the project to a temporary directory and runs everything
there from the project root, so outputs, caches and modified files never reach
the researcher's folder. It reports, per script: success or error, the last
lines of the error, missing packages, the files it created or modified; with
`--logs`, it saves what each script printed.

Before running, tell the researcher you are about to run their code in a copy,
and how many scripts there are. If the scanner shows heavy analyses (Bayesian
models, `brms`, `stan`, simulations, bootstraps), say that they may hit the
10-minute timeout per script and ask whether to run them with a longer one.

If scripts fail because packages are missing, **do not install them on your
own**: installing changes the researcher's R or Python setup. List the missing
packages and ask. The fact that packages were missing is itself a finding.

When a script fails, the scripts after it often fail only because they read
the files it should have produced. Report the first failure as the cause, and
the later ones as consequences.

If the first failure is a portability problem (a `setwd()`, an absolute path,
a path relative to the script's folder), the run has not yet told you whether
the analysis itself works. Find out in a copy: run with `--keep`, which leaves
the temporary copy and prints its path; in that copy, and only there, fix the
line; then run `run_code.py <copy> --logs <tmp>/logs`. Report the two results
separately: "fails as deposited because of X; once X is fixed, it runs" (or
"it then fails at Y"). This second run is often where the substantive problems
show up: look at what the scripts produce (the cleaned data, the model output)
and check whether the problems found in 1a survive the cleaning and reach the
analysis. Delete the copy when done.

Also report scripts that **modify** files in `data/raw/`, and outputs the README
promises that no script creates. If no interpreter is available (no R, a
MATLAB or SPSS project), say so and limit the check to packages, paths, files.

### 1g. Packages (if there is code)

From `code.all_packages`, build the list of packages the project needs and
compare it with what is declared (`renv.lock`, `requirements.txt`, README). If R
is available, get the installed versions
(`Rscript -e 'cat(sapply(c("pkg1","pkg2"), function(p) as.character(packageVersion(p))))'`)
for the README.

### 1h. Personal data and third-party material

From `possible_personal_data` and the materials folder, against section 8 of
the rules: identifying columns, published instruments, copyrighted stimuli,
the publisher's PDF of the article.

### 1i. Manuscript and reported numbers (if there is a manuscript)

Get the text: for `.docx`, `.odt`, `.md`, `.qmd`, `.Rmd`, `.tex`, `.html`,

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py text <manuscript> --out <tmp>/manuscript.txt
```

For a PDF the script uses `pdftotext` if installed; otherwise read the PDF
with your file-reading tool and save its text to `<tmp>/manuscript.txt`.

Then check, against section 11 of the rules:

- the **Data availability** statement: does it point to a repository and a DOI,
  or say "on request"?
- **participants and exclusions**: does the N in the manuscript match
  `n_participants`, and do the exclusions described (participants, trials,
  cut-offs) match what the scripts do?
- **which version** of the manuscript it is: preprint, accepted manuscript or
  the publisher's typeset PDF (journal header, page numbers, copyright line).

For the numbers, you need the code's output (`--logs` from 1f, and any tables
the scripts write). If the code only runs after a portability fix, use the
logs of the fixed copy. Then:

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py check <tmp>/manuscript.txt <tmp>/logs [<copy>/output]
```

It lists every statistic in the text (M, SD, t, F, r, b, p, N, CI ...) with
the sentence it is in, and whether a value that rounds to it appears in the
output. Go through the result with judgement:

- a statistic **not found** may be computed by hand, in another program, or
  from a version of the data that is not in the folder: say which;
- a match can be a **coincidence**, especially for small integers and
  p-values; look at the output line it matched;
- a value **found with the opposite sign** usually means a different
  reference level or contrast;
- when the output has a value close to, but not the same as, the reported one
  (t = 2.45 reported, 2.61 in the output), it is a discrepancy to report.

Focus on the main results (abstract, results section, tables); not every
number in the text needs a line in the report.

## Step 2 — Report

Use this structure. Each area that applies gets one status: ✅ fine, ⚠️ present
but needs work, ❌ missing or blocking. Under each area, list the concrete
findings: the file, the column, the line, what a reuser would run into. Areas
that are fine need a single line. Leave out the rows and sections of material
the folder does not have.

```markdown
# FAIR check — <project name>

<One paragraph: what the folder contains (N data files, N scripts, a
manuscript?), which checks were therefore done, and an overall judgement:
could a stranger reuse it today? What is the single biggest obstacle?>

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ✅/⚠️/❌ | ... |
| Folder structure and names | ... | ... |
| Formats | ... | ... |
| README | ... | ... |
| Data dictionary | ... | ... |
| License | ... | ... |
| Code runs | ... | ... |            (if code)
| Declared packages | ... | ... |      (if code)
| Manuscript and reported numbers | ... | ... |   (if manuscript)
| Personal data and third-party material | ... | ... |

## 1. Data files and consistency
## 2. Folder structure and names
## 3. Formats
## 4. README
## 5. Data dictionary
## 6. License
## 7. Code                       (if code)
## 8. Manuscript and reported numbers   (if manuscript)
## 9. Personal data and third-party material

## What to fix first
1. <the most blocking problem, with the concrete action>
2. ...
(at most 5-6 items, ordered by how much they block reuse)

## The deposit version
<what step 3 will build, and the decisions needed from the researcher>
```

In section 8, put the numbers in a table: statistic, where in the manuscript,
reported value, value in the output (with the script), status.

Each section links the relevant booklet page (from `references/fair-rules.md`)
once. Write findings as facts and actions: "`data/questionario.xlsx` has no
CSV copy: a reader without Excel cannot open it." Avoid generic advice that
does not name a file.

Show the report in the conversation. If the researcher wants it as a file,
save it outside the project folder, so it does not end up in the deposit.

## Step 3 — The deposit version

A new folder, `<project>_deposit`, next to the original (or where the researcher
says), with the fixed layout of section 9 of the rules, the documentation, the
licenses and the Psych-DS metadata, verified and zipped. The original folder
stays as it is.

### 3a. The plan, and the researcher's decisions

Write a plan: for every file of the project, where it goes in the deposit and
under which name, or why it stays out. Psych-DS names for the data files
(section 10 of the rules), scripts in `scripts/` numbered in run order, the
original exports in `data/raw/`, the preprint in `docs/`.

Show the plan as a table, together with the decisions only the researcher can
take, and wait for the answers:

- files to leave out (old scripts, duplicates, third-party material, the
  publisher's PDF);
- **personal data**: which columns to remove from the deposit's copy of the
  data, or whether the data need restricted access instead;
- **data corrections** found in step 1 (wrong values, inconsistent codes,
  duplicates): they are decisions about the researcher's data. If there is
  code, the place for them is the cleaning script, so that the change is
  visible and reproducible; in a data-only project, the deposit's CSV can be
  corrected and each change listed in the README;
- **licenses**: the defaults are CC0 1.0 for data, GPL-3.0 for code, CC BY 4.0
  for the preprint, figures and own materials (section 6 of the rules). Use
  them unless the researcher wants otherwise or an exception applies;
- what you cannot know: authors and ORCID, collection dates, DOIs. These stay
  `TODO` if not given.

If the researcher says to go ahead without answering some of these, use the
defaults, apply no data corrections, and list the open points at the end.

### 3b. Build

Write the plan as JSON (format in the script's header) and run:

```bash
python3 <skill-dir>/scripts/build_deposit.py build <project-folder> <tmp>/plan.json <project>_deposit
```

It copies only the listed files under their new names and rewrites the paths
inside the scripts to point to the new locations, including `here("data",
"x.csv")` and `file.path(...)` calls. With a `"data"` entry in the plan, it also
removes columns from the deposit's copy of a data file (personal data) and
converts it to comma-separated UTF-8 with decimal points, adjusting
`read.csv2()` and `sep = ";"` in the scripts that read it. Check its output:
`unresolved_paths` lists path-like strings it could not map (absolute paths,
files it cannot find). Fix those by hand in the deposit's scripts.
Also fix there the other portability problems found in 1f (`setwd()`,
absolute output paths, `rm(list = ls())`), and apply the data corrections the
researcher agreed to.

### 3c. Dictionaries

For each data file in the deposit:

```bash
python3 <skill-dir>/scripts/draft_dictionary.py <deposit>/data/<name>_data.csv --out <deposit>/dictionaries/<name>_dictionary.csv
```

Files with the same columns, such as one PsychoPy file per participant (the
scanner reports them as one `file_set`), get one dictionary: pass them all,
e.g. `draft_dictionary.py <deposit>/data/raw/psychopy/*.csv --out
<deposit>/dictionaries/raw-psychopy_dictionary.csv`. Raw exports in `data/raw/`
get a dictionary too when they are the data the scripts start from.

It writes the booklet's nine columns. `variable_name`, `type`,
`allowed_values`, `missing_values` and the list of codes come from the data;
`label`, `unit`, `source` and the meaning of each code are `TODO`. If the
project had a dictionary, start from it instead: carry over what it says, add
the missing rows and columns, and fix the names that do not match.

Then fill the `TODO`s you can support with evidence: a label from the README
or the manuscript, a unit from the code or the column name (`rt_ms`), the
meaning of codes from a `factor(..., labels = ...)`, a `recode()` or a filter in
the scripts, the range of a published questionnaire. When the evidence is
indirect, write the value and add "to check" in `notes`. Leave `TODO` where
nothing supports a value. An invented label is worse than a missing one: it
looks documented, so nobody checks it.

Then the Psych-DS version of the same dictionaries:

```bash
python3 <skill-dir>/scripts/make_psychds.py <deposit> --name "<title>" --description "<what the data are>" --meta <tmp>/meta.json
```

`meta.json` holds what is known about the dataset: `author` (Person, with ORCID
URL as `identifier`), `license`
(`https://creativecommons.org/publicdomain/zero/1.0/`), `keywords`,
`temporalCoverage`, `measurementTechnique`. The script writes
`dataset_description.json` with one `PropertyValue` per column and reports
columns without a dictionary entry.

### 3d. README and LICENSE

**README.md** with the eight sections of the booklet (template in section 4 of
the rules), written for the deposit's layout and file names. Include:

- what a row is in each data file, and how the files link (IDs);
- **How to reproduce** (if code): software and version, the packages with
  versions and an `install.packages()` line, the order of the scripts and what
  each produces, and to open the `.Rproj` first if there is one;
- **Changes from the original data**, if any;
- the **License** section saying what applies to what (template in section 6
  of the rules);
- `TODO` for what only the authors know.

Write it in the language of the existing README; with no README, in English.
If the project uses R packages, suggest `renv` (`renv::init()`, then
`renv::snapshot()`) to record exact versions: propose it, do not run it.

**LICENSE**: a short header with what applies to what, then the full official
texts of the licenses used, from `<skill-dir>/assets/licenses/`:

```bash
python3 <skill-dir>/scripts/build_deposit.py license <deposit> \
  --part "Data (data/, dictionaries/, dataset_description.json)=CC0-1.0" \
  --part "Code (scripts/)=GPL-3.0" \
  --part "Preprint, figures and this README (docs/, output/)=CC-BY-4.0" \
  --holder "<authors>"
```

Include only the parts that exist: a data-only deposit has CC0 for the data
and CC BY 4.0 for the README. Never write a license text from memory: a
paraphrased license is not the license. For a license not in `assets/`,
download its official text (ask first) and add it by hand.

### 3e. Verify

- If there is code, run it **in the deposit itself**, so that the figures and
  tables it produces end up in `output/`:
  `run_code.py <deposit> --in-place --logs <tmp>/logs_deposit`. Every script
  should run. If a manuscript was checked, run `manuscript_numbers.py check`
  again on the new logs: the results should be the same as in 1i.
- Run `fair_scan.py` on the deposit and check that `psychds.valid_minimum` is
  true, there are no naming problems, every data file has a complete dictionary,
  and nothing personal is left.
- Delete from the deposit anything the run created that does not belong
  (`.Rhistory`, caches, `Rplots.pdf`).

### 3f. Zip and hand over

```bash
python3 <skill-dir>/scripts/build_deposit.py zip <deposit>
```

writes `<deposit>.zip`, the single file to upload. Then tell the researcher:

- where the deposit folder and the zip are;
- what changed with respect to the original (renamed files, moved folders,
  rewritten paths, removed columns);
- what is still `TODO` (authors, ORCID, dates, DOIs, labels without evidence)
  and the open decisions;
- to check the folder with the Psych-DS validator
  (https://psych-ds.github.io/validator/, load the deposit's root folder);
- that once the DOI exists it goes into the README, `dataset_description.json`
  and the article's Data availability statement.
