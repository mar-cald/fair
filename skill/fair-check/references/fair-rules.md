# FAIR rules used by this skill

These rules come from the booklet *Hands-on Open Science* (Università di Padova,
https://mar-cald.github.io/fair/). Each section gives the page to cite in the
report, so the researcher can read the full explanation.

## Contents

1. File names — `struttura-1.html#regole-generali`
2. Formats — `struttura-1.html#in-che-formato-salvarli`
3. Folder structure — `struttura-1.html#struttura`
4. README — `struttura-1.html#readme`
5. Data dictionary — `struttura-1.html#data-dictionary`
6. Licenses — `licenze.html`
7. Code and reproducibility — `esempio.html`, `risorse.html`
8. Privacy and rights — `risorse.html#checklist-prima-di-depositare`
9. The deposit version: fixed folder layout — `struttura-1.html#struttura`, `zenodo.html`
10. Psych-DS — `struttura-2.html`
11. Manuscript or preprint — `risorse.html#checklist-prima-di-depositare`

Base URL for all links: `https://mar-cald.github.io/fair/`

---

## 1. File names

- No spaces, accented letters or special characters in file names or in
  variable (column) names. They break scripts, links and transfers between
  operating systems. Allowed: letters, digits, `_`, `-`, `.`.
- Numbered files use leading zeros (`01_`, `02_`), otherwise `10_` sorts before
  `2_`. Scripts are numbered in the order they run.
- The name says what the file contains. `Dati definitivi (2).xlsx` and
  `analisi finale.R` say nothing about the content.
- Versions go in `_v1`, `_v2`, or better in git. Words like `final`,
  `definitivo`, `nuovo`, `old`, `copy`, `(1)` in names point to manual versioning.
- One case convention (`snake_case` or `camelCase`), used consistently.

## 2. Formats

- Proprietary formats (`.xlsx`, `.xls`, `.sav`, `.dta`, `.sas7bdat`, `.mat`)
  open only with the program that created them. Open text formats (`.csv`,
  `.tsv`, `.txt`, `.json`) open with any tool and can be read by eye.
- `.rds` / `.RData` are R-only binary formats: same problem for anyone not using R.
- Documents: `.docx` → `.md`, `.txt` or `.pdf`. A codebook in `.docx` should
  become `<dataset>_dictionary.csv`.
- The original export of an instrument (E-Prime, Qualtrics, a `.sav`) can stay
  in `data/raw/` as read-only. Next to it goes the open-format version. So a
  proprietary file is a problem only when there is **no** open version beside it.

## 3. Folder structure

Reference layout (not mandatory in every detail; what matters is that raw data,
processed data, code and outputs are separated and the root is readable):

```
project/
├── README.md                       what is in here and how to use it
├── LICENSE                         under which conditions
├── data/
│   ├── raw/                        raw data: READ-ONLY, never modified
│   └── processed/
│       ├── gonogo_data.csv         clean data, produced by the scripts
│       └── gonogo_dictionary.csv   one row per column of gonogo_data.csv
├── scripts/
│   ├── 01_cleaning.R
│   └── 02_analysis.R
├── materials/                      stimuli, questionnaires, protocols
├── output/
│   ├── figures/
│   └── tables/
└── docs/                           preregistration, preprint, ...
```

Optional but useful: `CITATION.cff` (how to cite), `renv.lock` (exact R
package versions), an `.Rproj` file (sets the working directory in RStudio).

## 4. README

In the project root, in Markdown or `.txt`. It answers the questions a person
has **before** they can use anything else in the folder.

| Section | Answers |
|:--|:--|
| Title and authors (with ORCID) | Whose work is this, who to write to |
| What it is about | What study, when the data were collected |
| File contents | What is in the folder, file by file |
| How to read the data | What is needed to access the data |
| How to reproduce | In which order the scripts run, with which software, what they produce |
| License | Under which conditions it can be reused, what applies to what |
| How to cite | Citation for the project, DOI |
| Related materials | DOI of the article, preregistration, code |

Provenance belongs in the README too: how and when data were collected and
processed (e.g. "collected in the lab between March and July 2025").

Example of a complete README (from `esempio.html`):

```
# Stroop and trait anxiety

Stroop interference as a function of trait anxiety.
100 adults; colour-word Stroop task (PsychoPy) and a STAI-Y questionnaire,
collected in the lab in March 2026.

## Contents
- data/stroop_data.csv — one trial per row
- data/stroop_dictionary.csv — its columns
- data/raw/ — original exports, read-only
- scripts/01_preprocessing.R — cleans and merges the data
- scripts/02_analysis.R — models and figures
- renv.lock — exact R package versions

## How to reproduce
Open stroop-anxiety.Rproj in RStudio (R >= 4.3), then:
  renv::restore()   # installs the exact package versions (renv.lock)
  source("scripts/01_preprocessing.R")
  source("scripts/02_analysis.R")

## License
Data CC0-1.0, code GPL-3.0, materials CC BY 4.0 (see LICENSE).
STAI-Y is a third-party instrument: not included, cite it.

## How to cite
See CITATION.cff. Dataset: https://doi.org/10.5281/zenodo.XXXXXXX

## Links
Article: https://doi.org/10.xxxx/xxxxx
Preregistration: https://doi.org/10.17605/OSF.IO/XXXXX
```

## 5. Data dictionary

The README describes the project; the data dictionary describes **every
column** of every data file. One row per variable, in a separate file named
`<dataset>_dictionary.csv`, next to the data file it describes.

| Column | Content | Example |
|:--|:--|:--|
| `variable_name` | Exact column name, character by character | `rt` |
| `label` | What it measures | Reaction time |
| `type` | integer, numeric, string, categorical, date, boolean | numeric |
| `unit` | Unit of measurement, empty if none | milliseconds |
| `allowed_values` | Range or list of possible values | 200-2000 |
| `coding` | Meaning of each code, for categorical variables | 1 = Psychology; 2 = Economics |
| `missing_values` | How missing values are represented | empty cell, or NA |
| `source` | Where the value comes from: instrument, questionnaire, computation | PsychoPy |
| `notes` | Decisions, anomalies, warnings | ... |

What makes a dictionary insufficient: columns of the data that are not in it;
names that do not match the header exactly; categorical variables without
`coding`; numeric variables without `unit` when they have one; no statement on
how missing values are coded.

## 6. Licenses

Data, code and texts are different legal objects and need different licenses.
Applying one license to the whole project is the most common mistake.

The deposit version built by the skill uses the **defaults** in bold below,
unless the authors choose otherwise or one of the exceptions applies.

| Component | Recommended | Notes |
|:--|:--|:--|
| Data (and dictionaries, `dataset_description.json`) | **CC0 1.0** (default) or CC BY 4.0 | On facts and measurements the attribution requirement of CC BY has no legal effect; CC0 is required by Dryad and recommended by many repositories. ERC/Horizon Europe ask for CC BY or CC0. |
| Code | **GPL-3.0** (default) or MIT | Apache-2.0 for structured software or when companies are involved; AGPL-3.0 for web applications (e.g. an online experiment platform). GPL is mandatory if the project includes GPL code. |
| Manuscript / preprint | **CC BY 4.0** | Only the authors' version (preprint, or accepted manuscript where the journal allows it). The publisher's typeset PDF can almost never be redistributed: leave it out and link its DOI. If the preprint is already on a server (PsyArXiv, bioRxiv) under a license, keep that license. |
| Texts and own materials, README, figures | **CC BY 4.0** | Questionnaires, stimuli, protocols written by the authors; figures produced by the scripts. |
| Third-party materials | none: not redistributed | Published tests (e.g. STAI-Y), copyrighted stimuli: cite them, do not deposit them. |

Licenses to flag:

- **CC BY-NC** ("non-commercial"): "commercial" is not precisely defined; it
  blocks legitimate uses (a paid course, a publisher, a company funding
  research) and is not "open". Flag it and explain, do not call it wrong.
- **CC BY-ND** (no derivatives): makes reuse of data practically impossible.
- **Creative Commons on code**: CC licenses are not designed for software.
- **Software licenses (MIT, GPL) on data**: not designed for data.
- **CC0 on data is not appropriate** when the dataset contains third-party
  material, when the funder/journal/repository requires a different license, or
  when the EU *sui generis* database right applies.
- **No license at all**: all rights reserved, nobody can legally reuse anything.
- PsychArchives' *scientific use only* license: legitimate, but it excludes
  uses outside academic research and teaching (e.g. third-mission activities).

How a license is applied, in practice:

1. The license field in the repository (Zenodo, PsychArchives) at deposit time.
2. A `LICENSE` file in the project root with the full text of the license(s).
3. A section in the README that says, in words, what applies to what:

```markdown
## License

- Data (`data/`, `dictionaries/`, `dataset_description.json`): CC0 1.0 Universal (CC0-1.0)
- Code (`scripts/`): GNU General Public License v3.0 (GPL-3.0)
- Preprint, figures and own materials (`docs/`, `output/`, `materials/`): CC BY 4.0
- Third-party materials: not redistributed, subject to the
  conditions of their respective owners
```

The full official texts of the three default licenses are bundled with the
skill in `assets/licenses/` (`CC0-1.0.txt`, `GPL-3.0.txt`, `CC-BY-4.0.txt`,
downloaded from creativecommons.org and gnu.org). For any other license, the
official text must be downloaded (ask first):

- CC BY-SA 4.0: https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt
- MIT: short, written with year and copyright holder (see https://choosealicense.com/licenses/mit/)
- Apache-2.0: https://www.apache.org/licenses/LICENSE-2.0.txt

## 7. Code and reproducibility

From the checklist "before depositing":

- The code runs **on another computer**, starting from a clean folder.
- It is clear which scripts produced which results and in which order they run.
- Dependencies are declared: package list and versions (`renv.lock` for R,
  `requirements.txt` or `environment.yml` for Python), plus the R/Python version.
  FAIR4RS (Barker et al., 2022) asks for: identifier and version, declared
  dependencies, license, instructions to run it.

Things that stop code from running on another computer:

- `setwd("C:/Users/...")` or any absolute path: works only on the author's machine.
  Use paths relative to the project root (an `.Rproj` file, or `here::here()`).
- Reading files that are not in the folder.
- Packages loaded but not declared anywhere.
- `install.packages()` inside analysis scripts: installs every time, and
  without version control.
- `rm(list = ls())` at the top: does not restart R, gives a false sense of a
  clean session.

## 8. Privacy and rights

From the checklist "before depositing":

- No full birth dates, addresses, or combinations of variables that identify a
  person. Names, e-mails, phone numbers, tax codes (codice fiscale), IP
  addresses, GPS coordinates must not be in shared data.
- Pseudonymised data (codes replacing names, key kept elsewhere) are still
  personal data; only anonymised data (irreversible) are not.
- Everything deposited can be redistributed: check tests, questionnaires and
  stimuli owned by third parties.
- Sensitive data: deposit with restricted access (metadata and DOI public, files
  only to approved people), not open.

## 9. The deposit version: fixed folder layout

The deposit version always uses the same folder names, so that every project
deposited this way looks the same to a reader. Only the folders that have
content are created.

```
<project>_deposit/
├── README.md                 the eight sections of the booklet
├── LICENSE                   what applies to what, then the full texts
├── dataset_description.json  Psych-DS metadata and data dictionary
├── data/                     data files, named key-value_..._data.csv
│   └── raw/                  original exports (.xlsx, .sav, E-Prime ...), read-only
├── dictionaries/             one <data file name>_dictionary.csv per data file
├── scripts/                  analysis code, numbered in the order it runs
├── output/
│   ├── figures/              produced by the scripts
│   └── tables/
├── materials/                own stimuli, questionnaires, protocols
└── docs/                     preprint or accepted manuscript, preregistration
```

The dictionaries are in their own folder, not next to the data as the
booklet's general layout shows: Psych-DS checks every file inside `data/`
(except `data/raw/`), and a `_dictionary.csv` there would be reported as a
badly named data file.

What stays out of the deposit:

- system and editor files: `.DS_Store`, `.Rhistory`, `.RData`, `.Rproj.user/`,
  `__pycache__/`, `.ipynb_checkpoints/`, `renv/library/`, `.git/`;
- scripts that are not part of the analysis (old tests, files that read data
  that are not there), unless the authors want them, described in the README;
- copies of the same data in several formats beyond the original export in
  `data/raw/` and its open version in `data/`;
- empty folders;
- third-party material that cannot be redistributed (published tests,
  copyrighted stimuli, the publisher's PDF of the article);
- personal data (see section 8): columns to remove, or files to deposit with
  restricted access instead.

The `.Rproj` file can stay: it sets the working directory in RStudio, and the
scripts are written to run from the project root.

Zenodo does not keep folders when files are uploaded one by one: a whole
project folder is uploaded as a single `.zip`, whose contents Zenodo shows in
the preview. Before uploading, open the zip and check that it contains only the
project's files.

## 10. Psych-DS

Minimum rules (from `struttura-2.html`):

1. A `data/` folder in the root, with the data files in CSV.
2. A `dataset_description.json` file in the root, with exactly this name,
   next to `data/` and not inside it.
3. Data files named with key-value pairs and the suffix `_data.csv`:
   `study-stroop_subject-01_data.csv`. A hyphen joins a key to its value, an
   underscore separates the pairs; keys are lowercase; values contain only
   letters and digits.

Psych-DS defines nine official keys: `study`, `site`, `subject`, `session`,
`task`, `condition`, `trial`, `stimulus`, `description`. Use only these.
Names used in the deposit: `study-<study name>` always first, then, when there
is more than one file, `task-<task>` for task data or `description-<what it
is>` otherwise, e.g. `study-flankersleep_task-flanker_data.csv`,
`study-stroopmindfulness_description-participants_data.csv`. One file per
participant adds `subject-<id>`.

`dataset_description.json` uses the schema.org vocabulary. Required:
`name`, `description`, `variableMeasured`; usually also `@context`
(`https://schema.org/`) and `@type` (`Dataset`). `variableMeasured` must list
**exactly** the column names of all the data files. Each entry can be a plain
name or a `PropertyValue` object, which turns the JSON into a data dictionary:

```json
"variableMeasured": [
  {
    "@type": "PropertyValue",
    "name": "rt_ms",
    "description": "Reaction time from stimulus onset to response",
    "unitText": "milliseconds",
    "minValue": 200,
    "maxValue": 3000
  },
  {
    "@type": "PropertyValue",
    "name": "condition",
    "description": "Congruency between word and ink colour",
    "value": "congruent | incongruent"
  }
]
```

Useful optional fields: `author` (Person with `name`, `identifier` = ORCID
URL, `affiliation`), `license` (URL), `keywords`, `datePublished`,
`temporalCoverage`, `spatialCoverage`, `measurementTechnique`, `citation`.

The authoritative check is the web validator,
https://psych-ds.github.io/validator/ (load the root folder of the deposit).
`data/raw/` is ignored by the validator.

## 11. Manuscript or preprint

- The DOI of the deposit goes in the article's **Data availability** section.
  "Data available on request" is not FAIR: most requests go unanswered.
- The numbers in the results (descriptives, test statistics, effect sizes,
  the number of participants and of exclusions) should be produced by the
  deposited code. A number that no script prints cannot be checked by a reader.
- The exclusions described in the methods (participants, trials, cut-offs)
  should match what the scripts do.
- What can be deposited: the preprint or the accepted manuscript (check the
  journal's policy, e.g. on Sherpa Romeo), under CC BY 4.0, in `docs/`. The
  publisher's typeset PDF usually cannot.
