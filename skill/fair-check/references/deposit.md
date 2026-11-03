# The deposit version (step 3)

A new folder, `<project>_deposit`, next to the original (or where the
researcher says), with the fixed layout of section 9 of the rules, standard
file names, documentation and licenses, verified and zipped. The original
stays as it is.

What the Psych-DS answer of the triage changes:

| | Psych-DS: no (default) | Psych-DS: yes |
|:--|:--|:--|
| Folders | section 9 layout | section 9 layout |
| Data file names | `study-x_task-y_data.<own extension>` | `study-x_task-y_data.csv` |
| Open formats (.tsv, .txt, .json) | kept as they are | converted to comma-separated UTF-8 CSV |
| `dataset_description.json` | not created | created (3c) |
| Psych-DS validator | not mentioned as a goal | must pass |

Without Psych-DS, leave out `dataset_description.json` from the section 9
layout. In both cases a proprietary file with no open copy (Excel, SPSS, Stata,
E-Prime `.edat`) gets one: that is FAIR, not Psych-DS.

## 3a. Plan and decisions

For every file of the project: where it goes and under which name, or why it
stays out. Data files with key-value names (section 10 of the rules), scripts
in `scripts/` numbered in run order, original exports in `data/raw/`,
experiment files in `materials/`, the preprint in `docs/`. For each program's
files, follow the "Deposit" paragraph of `software-exports.md`.

**Splitting long scripts** (if chosen): the plan shows where each script is
cut (line numbers, at the end of a phase) and which file passes results to the
next piece. The pieces keep the original lines as they are; the only additions
are a line at the end of a piece that saves what the next one needs
(`write.csv()` of the processed data in `data/`, `saveRDS()` of a model in
`output/`) and a line at the start of the next that reads it, plus the
`library()` calls each piece needs. No restyling, no renaming of objects.

If models were not re-estimated, ask whether the saved fits go into `output/`
(a reader can check results without hours of computing, but they can be large).

Show the plan as a table with the decisions only the researcher can take, and
wait:

- files to leave out (old scripts, duplicates, third-party material, the
  publisher's PDF);
- **personal data**: columns to remove from the deposit's copy, or restricted
  access instead;
- **data corrections** found in step 1: decisions about their data. With code,
  they go in the cleaning script (visible, reproducible); in a data-only
  project, in the deposit's copy, each listed in the README;
- **licenses**: defaults CC0 1.0 data, GPL-3.0 code, CC BY 4.0 preprint,
  figures and own materials (section 6), unless they want otherwise or an
  exception applies;
- what you cannot know: authors, ORCID, dates, DOIs (`TODO` if not given).

If they say to go ahead without answering, use the defaults, apply no data
corrections, and list the open points at the end.

## 3b. Build

Write the plan as JSON (format in the script's header) and run:

```bash
python3 <skill-dir>/scripts/build_deposit.py build <project-folder> <tmp>/plan.json <project>_deposit
```

It copies the listed files under their new names and rewrites the paths inside
the scripts (`here("data", "x.csv")`, `file.path(...)` included). Optional plan
sections:

- **`"data"`**: `drop` removes columns (personal data); `normalise` (default
  true) converts to comma-separated UTF-8 with decimal points and adjusts the
  scripts that read the file. **Set `"normalise": false` for every open file
  when Psych-DS is not chosen**, and for raw exports the scripts read as they
  are; `drop` still works and keeps separator and encoding.
  `remove_export_rows`: leave false for files the scripts read.
- **`"csv_copies"`**: an open CSV from JSON, an E-Prime log, a TSV or UTF-16
  export, an Excel sheet or an SPSS file, without export rows and listed
  columns. Without Psych-DS, use it only for files with no open copy.

Check the output: `unresolved_paths` (absolute paths, missing files) and
`check_by_hand` (reading lines it could not adjust, scripts reading a file
whose export rows were removed): fix them in the deposit's scripts. Fix there
also the portability problems of 1f (`setwd()`, absolute paths,
`rm(list = ls())`), add agreed seeds, apply agreed data corrections. Each fix
is the smallest possible and in the style of the surrounding code; new code
written from scratch is in the language chosen in the triage, in the style of
the researcher's scripts (or their style skill, if they have one).

## 3c. Dictionaries

For each data file (`<name>` is the file name without `_data.<ext>`):

```bash
python3 <skill-dir>/scripts/draft_dictionary.py <deposit>/data/<name>_data.<ext> --out <deposit>/dictionaries/<name>_dictionary.csv
```

Files with the same columns (a `file_set`, e.g. one PsychoPy file per
participant) get one dictionary: pass them all. Raw exports in `data/raw/` get
one too when the scripts start from them. It reads the scanner's formats
(`--sheet` for Excel) and writes the booklet's nine columns: from the data
(name, type, allowed and missing values, codes); from the file (Qualtrics
question text, SPSS labels); from `scripts/software.py` (columns experiment
software writes, marked "to check"); everything else `TODO`. If the project had
a dictionary, start from it: carry it over, add missing rows, fix names.

Fill the `TODO`s you can support with evidence (README, manuscript, units in
code or names like `rt_ms`, codes from `factor(..., labels = )` or `recode()`,
published questionnaire ranges); indirect evidence gets "to check" in `notes`.
Leave `TODO` where nothing supports a value: an invented label looks
documented, so nobody checks it.

**Only with Psych-DS:**

```bash
python3 <skill-dir>/scripts/make_psychds.py <deposit> --name "<title>" --description "<what the data are>" --meta <tmp>/meta.json
```

`meta.json`: `author` (Person, ORCID URL as `identifier`), `license`
(`https://creativecommons.org/publicdomain/zero/1.0/`), `keywords`,
`temporalCoverage`, `measurementTechnique`. It writes
`dataset_description.json` and reports columns without a dictionary entry.

## 3d. README and LICENSE

**README.md** with the booklet's eight sections (section 4 of the rules), for
the deposit's layout and names: what a row is in each file and how files link;
**How to reproduce** (software and version, packages with versions and an
`install.packages()` line, script order and outputs, open the `.Rproj` first);
**Changes from the original data**; **License** (what applies to what);
`TODO` for what only the authors know. In the language of the existing README,
English if none. Suggest `renv` (`renv::init()`, `renv::snapshot()`), do not
run it.

**LICENSE**: header plus the official texts from `<skill-dir>/assets/licenses/`:

```bash
python3 <skill-dir>/scripts/build_deposit.py license <deposit> \
  --part "Data (data/, dictionaries/)=CC0-1.0" \
  --part "Code (scripts/)=GPL-3.0" \
  --part "Preprint, figures and this README (docs/, output/)=CC-BY-4.0" \
  --holder "<authors>"
```

Only the parts that exist (add `dataset_description.json` to the data part with
Psych-DS). Never write a license from memory; for one not in `assets/`,
download its official text (ask first).

## 3e. Verify

- With code: `run_code.py <deposit> --in-place --logs <tmp>/logs_deposit`, so
  figures and tables land in `output/`. Every script should run. If the
  manuscript was checked, rerun `manuscript_numbers.py check` on the new logs:
  same results as 1i. Differences in scripts without seeds show what a reader
  would get: report their size. If scripts were split, the numbers must equal
  the original script's in 1f.
- If models were not re-estimated: run with `--keep` instead of `--in-place`,
  load the saved fits in the copy as in 1f; the deposit's scripts stay as they
  are. Say that `output/` was not regenerated.
- `fair_scan.py` on the deposit: no naming problems, a complete dictionary for
  every data file, nothing personal left; with Psych-DS, `psychds.valid_minimum`
  true.
- Delete what the run created that does not belong (`.Rhistory`, caches,
  `Rplots.pdf`).

## 3f. Zip and hand over

```bash
python3 <skill-dir>/scripts/build_deposit.py zip <deposit>
```

Then tell the researcher:

- where the folder and the zip are, and how to upload: on **Zenodo** the zip is
  the single file (Zenodo shows its contents); on **PsychArchives** or another
  repository, follow its upload form, and say which metadata fields the README
  already answers (title, authors, description, license, keywords);
- every change from the original (renamed files, moved folders, rewritten
  paths, removed columns, split scripts, lines added or fixed), so they can
  check each one;
- what is still `TODO`, the dictionary entries "to check", the open decisions;
- with Psych-DS, to check with the validator (https://psych-ds.github.io/validator/,
  load the root folder);
- once the DOI exists: into the README, `dataset_description.json` (if any) and
  the article's Data availability statement.
