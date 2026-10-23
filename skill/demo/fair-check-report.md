# FAIR check — flanker_sleep

The folder contains a Flanker experiment with a sleep questionnaire (PSQI): 2 data
files (1176 trials from 24 participants; 24 questionnaires), the original Excel
export, one incomplete data dictionary, 2 analysis scripts plus an old test
script, an RStudio project, the PSQI questionnaire as a PDF, a 33-word README and
an MIT license. **As it is, a stranger could open the files but could not reuse
them correctly.** The biggest obstacle is not missing documentation but four data
problems that reach the model without anyone noticing. A condition label written
with a capital letter becomes a third experimental condition. A missing PSQI
score coded 99 is analysed as a real score. One participant is silently dropped.
A block of trials is counted twice.

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ❌ | `Incongruent`/`incongruent`, PSQI = 99, a duplicated block, an age typo, IDs that differ between files |
| Folder structure and names | ⚠️ | Good layout (raw data separate, `.Rproj`, scripts numbered); `Analisi vecchie/` and empty `output/` |
| Formats | ✅ | The Excel export is in `data/raw/`, and its CSV version is in `data/` |
| README | ❌ | 33 words; no file list, no instructions to reproduce, no license, no citation |
| Data dictionary | ❌ | The questionnaire has none; the trials dictionary has 3 of 9 columns and misses `age` and `cond` |
| License | ❌ | One MIT license for everything: a software license applied to data, and the PSQI is a third-party instrument |
| Code runs | ⚠️ | `01_import.R` runs and reproduces the CSV exactly; `02_models.R` stops at the last line (absolute path), and runs once that is fixed |
| Declared packages | ❌ | 6 packages used, none declared |
| Personal data | ❌ | Full birth dates (`data_nascita`) in the questionnaire |

## 1. Data files and consistency

**`data/flanker_trials.csv`** (one row per trial: 24 participants × 48 trials)
- **`cond`:** 6 trials of participants 4 and 15 are written `Incongruent` instead of
  `incongruent`. R treats them as a third condition (see section 7 for what this does
  to the model).
- **`rt`:**
  - 29 trials have the value 9999, which looks like a timeout code (no
    response) rather than a time.
  - 27 trials have an empty cell.

  Missing values are therefore coded two ways. `02_models.R` removes both with
  `filter(rt < 3000)`, but nothing in the folder says what 9999 means or why 3000
  ms is the cutoff.
- **Duplicate rows:** 24 rows are exact duplicates. They are block 2 of
  participant 12, which appears twice, so participant 12 contributes 61 trials
  to the model against a median of 44.
- **`age`:** participant 7 is 22 in block 1 and 2 in block 2.

**`data/questionario_sonno.csv`** (one row per participant; semicolon-separated,
decimal comma, as exported by Excel with Italian settings)
- **`psqi_tot`:**
  - Participant S21 has 99. The PSQI global score goes from 0 to 21, so 99 is
    almost certainly a missing-value code.
  - The analysis script reads it as a score.
- **`data_nascita`:** see section 8.

**Across the two files**
- **The same participants are written differently:** `1, 2, …` in the trials and
  `S01, S02, …` in the questionnaire, under different column names (`subj` vs `id`).
  `02_models.R` reconciles them with `gsub("S", "", …)`, which works but is
  documented nowhere.
- **Participants in only one file:**
  - Participant 19 has trials but no questionnaire. In the analysis all their
    trials get `psqi_tot = NA` and are dropped by `lmer` without a message:
    the model has 23 participants, not 24.
  - S25 has a questionnaire but no trials.
- **Age disagrees between the two files:** for participant 7 (2 / 22 vs 22) and
  participant 9 (30 in the trials, 33 in the questionnaire).

## 2. Folder structure and names → [rules](https://mar-cald.github.io/fair/struttura-1.html#struttura)

The layout follows the booklet: the raw export is in `data/raw/`, the scripts are
numbered `01_`, `02_`, and the `.Rproj` sets the working directory.
- **`Analisi vecchie/prova.R`:**
  - The folder name has a space and a manual-versioning word.
  - The script reads `dati_finali.csv`, which does not exist, so it fails.
  - It is not part of the analysis. Remove it from the deposit, or say in the
    README what it is.
- **`output/figures/` is empty:** the figure is saved to the author's Desktop
  instead (section 7).

## 3. Formats → [rules](https://mar-cald.github.io/fair/struttura-1.html#in-che-formato-salvarli)
- **`data/raw/flanker_export.xlsx`:** it is the original export, kept read-only
  in `data/raw/` as the booklet suggests. `01_import.R` turns it into
  `data/flanker_trials.csv`. The scanner does not see the CSV as its open copy
  because the names differ; the README should state the link.

## 4. README → [rules](https://mar-cald.github.io/fair/struttura-1.html#readme)

`README.txt` has a title, two sentences on the study, and a contact e-mail. It
is missing:
- the authors and their ORCID;
- when and where the data were collected, and how participants were recruited;
- a file-by-file list;
- what a row is in each data file;
- the order of the scripts, the software and packages needed, and what each
  script produces;
- the license, how to cite, and links to the article or preregistration.

None of the 10 files in the folder is named in it.

## 5. Data dictionary → [rules](https://mar-cald.github.io/fair/struttura-1.html#data-dictionary)
- **`data/flanker_trials_dictionary.csv`:**
  - It has 3 of the 9 columns (`variable_name`, `label`, `type`); `unit`,
    `allowed_values`, `coding`, `missing_values`, `source` and `notes` are
    missing.
  - It lists `condition`, but the data column is `cond`.
  - It has no row for `age`.
  - The things a reuser most needs are absent: the unit of `rt`, what 9999
    means, and what `acc` 0 and 1 stand for.
- **`data/questionario_sonno.csv`:** there is no dictionary.

## 6. License → [rules](https://mar-cald.github.io/fair/licenze.html)
- **One license for everything:** `LICENSE` is the full MIT text. MIT is a
  software license, and it is the only license in the folder, so it ends up
  covering the data and the materials as well.
- **What the booklet recommends:**
  - for the data, CC0 1.0 (or CC BY 4.0);
  - for the code, MIT can stay, or GPL-3.0 if you want derivative code to stay
    open.
- **`materials/PSQI_italiano.pdf`** is a published third-party instrument (the
  Pittsburgh Sleep Quality Index and its Italian validation). It cannot be
  redistributed under your license. Leave it out of the deposit and cite it in
  the README.

## 7. Code

I ran everything in a temporary copy of the folder; the folder itself was not
touched. R 4.4.2.

| Script | As deposited | Notes |
|:--|:--|:--|
| `scripts/01_import.R` | ✅ runs | Regenerates `data/flanker_trials.csv` from the Excel export, **identical** to the one in the folder |
| `scripts/02_models.R` | ❌ fails on the last line | `ggsave("C:/Users/giulia/Desktop/figura1.png")`: that folder exists only on the author's computer |
| `Analisi vecchie/prova.R` | ❌ fails | Reads `dati_finali.csv`, which is not in the folder |

**Rerun with the save path changed to `output/figures/figura1.png`.** I made
this change only in a second copy. With it, `02_models.R` runs and produces the
figure. The output shows that the data problems from section 1 reach the model:

- **`cond` has three levels.** `Incongruent` (6 trials) becomes the reference
  level, so the intercept and the two condition effects are estimated against
  those 6 trials. For the same reason `emmeans` returns "nonEst" for one
  condition. The congruent–incongruent difference the study is about is not
  what the coefficient `condincongruent` reports.
- **The 99 is analysed as a PSQI score.** All of S21's trials enter the model
  with `psqi_tot = 99`.
- **The model has 23 participants, not 24.** Participant 19 is dropped (no
  questionnaire), and no message says so.
- **Participant 12's block 2 counts twice.**

## 8. Personal data and third-party material → [checklist](https://mar-cald.github.io/fair/risorse.html#checklist-prima-di-depositare)
- **`data_nascita`** in `questionario_sonno.csv` holds full birth dates. Together
  with sex and the year of the study they make participants identifiable.
  The analysis does not use it, and age is already recorded in `eta`, so it
  should be removed before sharing.
- **`materials/PSQI_italiano.pdf`:** third-party instrument (see section 6).
- **The README's contact address is personal.** That is fine if intended; an
  institutional address lasts longer.

## What to fix first
1. **Remove `data_nascita`** from `questionario_sonno.csv`, and take
   `PSQI_italiano.pdf` out of the deposit.
2. **Fix the data that change the results:**
   - `Incongruent` → `incongruent`;
   - recode PSQI 99 as missing;
   - remove the duplicated block of participant 12;
   - correct participant 7's age;
   - decide which age is right for participant 9.

   Then rerun `02_models.R` and check whether the results change.
3. **Save the figure inside the project:** `ggsave("output/figures/figura1.png", …)`.
4. **Write the two data dictionaries.** State what 9999, the empty `rt` cells and
   `acc` mean, and why trials over 3000 ms are excluded.
5. **Rewrite the README** with the file list, the steps to reproduce (with
   package versions), the licenses and the missing participant 19.
6. **Use separate licenses:** CC0 for `data/`, MIT (or GPL-3.0) for `scripts/`.

## What I can do now
- Complete `flanker_trials_dictionary.csv` (all 9 columns, `cond` instead of
  `condition`, a row for `age`) and draft `questionario_sonno_dictionary.csv`,
  with `TODO` where only you know the answer.
- Write a `README.md` with the booklet's eight sections, including:
  - the R version and packages: readxl 1.4.3, janitor 2.2.1, dplyr 1.2.0,
    tidyverse 2.0.0, lme4 1.1.36, emmeans 1.10.7;
  - the order of the scripts.
- Change the `ggsave()` path and run the code again to confirm it works.
- Once you have chosen the licenses, add the License section to the README and
  the license texts (downloaded from the official sites, after asking).

The data corrections in point 2 are decisions about your data, so I only
reported them.
