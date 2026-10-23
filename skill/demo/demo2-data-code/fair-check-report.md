# FAIR check — flanker_sleep

The folder contains **data and code** from a Flanker experiment with a sleep
questionnaire (PSQI):
- 2 data files: 1176 trials from 24 participants, and 24 questionnaires;
- the original Excel export and an incomplete data dictionary;
- 2 analysis scripts and an old test script;
- an RStudio project, the PSQI questionnaire as a PDF, a 33-word README and
  an MIT license.

There is no manuscript. The checks done are: data, structure, formats, README,
dictionary, license, code, packages, personal data.

**A stranger could open the files but could not reuse them correctly.** Four data
problems reach the model without anyone noticing:
- a condition label written with a capital letter becomes a third
  experimental condition;
- a missing PSQI score coded 99 is analysed as a real score;
- one participant is silently dropped;
- a block of trials is counted twice.

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ❌ | `Incongruent`/`incongruent`, PSQI = 99, a duplicated block, an age typo, IDs that differ between files |
| Folder structure and names | ⚠️ | Good layout (raw data apart, `.Rproj`, numbered scripts); `Analisi vecchie/` and an empty `output/` |
| Formats | ✅ | The Excel export is in `data/raw/`, and its CSV version is in `data/` |
| README | ❌ | 33 words: no file list, no reproduction steps, no license, no citation |
| Data dictionary | ❌ | None for the questionnaire; the trials one has 3 of 9 columns and misses `age` and `cond` |
| License | ❌ | One MIT license for everything: a software license on data; the PSQI is third-party |
| Code runs | ⚠️ | `01_import.R` runs and reproduces the CSV exactly; `02_models.R` stops at its last line (absolute path) and runs once that is fixed |
| Declared packages | ❌ | 6 packages used, none declared |
| Personal data and third-party material | ❌ | Full birth dates (`data_nascita`); the PSQI PDF |

## 1. Data files and consistency

**`data/flanker_trials.csv`** (one row per trial)
- **`cond`:** 6 trials of participants 4 and 15 are written `Incongruent` instead
  of `incongruent`.
- **`rt`:**
  - 29 trials are 9999, which looks like a timeout code;
  - 27 cells are empty.

  `02_models.R` removes both with `filter(rt < 3000)`, but nothing says what
  9999 means or why 3000 ms is the cutoff.
- **Duplicated block:** 24 exact duplicate rows, which are block 2 of
  participant 12 pasted twice.
- **`age`:** participant 7 is 22 in block 1 and 2 in block 2.

**`data/questionario_sonno.csv`** (one row per participant; semicolon-separated,
decimal comma)
- **`psqi_tot`:** S21 has 99, outside the 0–21 range of the PSQI global score.
- **`data_nascita`:** see section 9.

**Across the two files**
- **The same participants are written differently:** `1, 2, …` vs `S01, S02, …`,
  under different column names (`subj` vs `id`). `02_models.R` reconciles them
  with `gsub("S", "", …)`.
- **Participants in only one file:** participant 19 has no questionnaire, and
  S25 has no trials.
- **Age disagrees between the files** for participants 7 and 9 (30 in the trials,
  33 in the questionnaire).

## 2. Folder structure and names → [rules](https://mar-cald.github.io/fair/struttura-1.html#struttura)
- **`Analisi vecchie/prova.R`:**
  - the folder name has a space and "vecchie";
  - the script reads a file that does not exist;
  - it is not part of the analysis.
- **`output/figures/` is empty:** the figure is saved to the author's Desktop.

## 3. Formats → [rules](https://mar-cald.github.io/fair/struttura-1.html#in-che-formato-salvarli)
- **`data/raw/flanker_export.xlsx`** is the original export, kept read-only in
  `data/raw/`. `01_import.R` turns it into `data/flanker_trials.csv`.

## 4. README → [rules](https://mar-cald.github.io/fair/struttura-1.html#readme)

`README.txt` has a title, two sentences and a contact. It is missing:
- the authors and ORCID;
- the collection dates;
- the file list;
- what a row is in each file;
- the run order and the packages;
- the license, the citation and related materials.

## 5. Data dictionary → [rules](https://mar-cald.github.io/fair/struttura-1.html#data-dictionary)
- **`flanker_trials_dictionary.csv`:**
  - it has 3 of 9 columns;
  - it lists `condition`, but the data column is `cond`;
  - there is no row for `age`;
  - the unit of `rt`, the meaning of 9999 and the coding of `acc` are not
    given.
- **The questionnaire** has no dictionary.

## 6. License → [rules](https://mar-cald.github.io/fair/licenze.html)
- **One license for everything:** the MIT license is the only one, so it also
  covers the data. Recommended: CC0 1.0 for the data, GPL-3.0 for the code.
- **`materials/PSQI_italiano.pdf`** is a published third-party instrument.
  Leave it out and cite it.

## 7. Code

Everything ran in a temporary copy, with R 4.4.2.

| Script | As deposited | Notes |
|:--|:--|:--|
| `scripts/01_import.R` | ✅ runs | Regenerates `data/flanker_trials.csv` from the Excel export, identical to the one in the folder |
| `scripts/02_models.R` | ❌ fails on the last line | `ggsave("C:/Users/giulia/Desktop/figura1.png")` |
| `Analisi vecchie/prova.R` | ❌ fails | Reads `dati_finali.csv`, which is not in the folder |

**With the save path changed to `output/figures/`** (in a second copy only),
`02_models.R` runs. The output shows that the data problems reach the model:
- **`cond` has three levels.** The 6 `Incongruent` trials become the reference
  level, and `emmeans` returns "nonEst" for one condition.
- **S21's 99 enters the model as a PSQI score.**
- **The model has 23 participants:** participant 19 is dropped without a
  message.
- **Participant 12's block 2 counts twice.**

**Packages used, none declared:** readxl 1.4.3, janitor 2.2.1, dplyr 1.2.0,
tidyverse 2.0.0, lme4 1.1.36, emmeans 1.10.7.

## 9. Personal data and third-party material → [checklist](https://mar-cald.github.io/fair/risorse.html#checklist-prima-di-depositare)
- **`data_nascita`** holds full birth dates. Age is already in `eta`, so the
  column should be removed.
- **The PSQI PDF:** third-party instrument (section 6).

## What to fix first
1. **Remove `data_nascita`** and leave the PSQI PDF out of the deposit.
2. **Fix in the scripts the data problems that change the results:**
   - `Incongruent` → `incongruent`;
   - PSQI 99 → missing;
   - remove the duplicated block;
   - correct participant 7's age;
   - decide which age is right for participant 9.
3. **Save the figure inside the project.**
4. **Write the two dictionaries**, including what 9999, the empty `rt` cells and
   `acc` mean.
5. **Write the README** with the reproduction steps and package versions.
6. **Use separate licenses:** CC0 for the data, GPL-3.0 for the code.

## The deposit version

What goes where in `flanker_sleep_deposit/`:

| From | To |
|:--|:--|
| `data/raw/flanker_export.xlsx` | `data/raw/flanker_export.xlsx` |
| `data/flanker_trials.csv` | `data/study-flankersleep_task-flanker_data.csv` (regenerated by `01_import.R`) |
| `data/questionario_sonno.csv` | `data/study-flankersleep_task-psqi_data.csv` (comma-separated, without `data_nascita`) |
| `data/flanker_trials_dictionary.csv` | completed, in `dictionaries/` |
| `scripts/01_import.R`, `scripts/02_models.R` | `scripts/` (paths updated) |
| `flanker_sleep.Rproj` | root |
| `README.txt`, `LICENSE` | replaced by `README.md` and a new `LICENSE` |
| `Analisi vecchie/prova.R` | left out: not part of the analysis |
| `materials/PSQI_italiano.pdf` | left out: third-party instrument |

Decisions needed from you:
- **Data corrections in point 2:** apply them? In the scripts, so that the change
  is visible and reproducible.
- **Participant 9's age:** which one is right?
- **Licenses:** CC0 for data, GPL-3.0 for code, CC BY 4.0 for the README and
  figures?
- **Authors, ORCID, collection dates, DOIs.**
