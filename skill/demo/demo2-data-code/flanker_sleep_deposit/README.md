# Flanker and sleep quality

Data and analysis code of a study relating the Flanker effect to sleep quality
(PSQI).

Authors: TODO (names and ORCID)
Contact: giulia.bianchi@example.org

## About the study

24 participants completed a Flanker task (48 trials in two blocks of 24,
E-Prime) and the Pittsburgh Sleep Quality Index (PSQI), in 2025.
TODO: research question, where and when the data were collected, recruitment.

Participant 19 completed the Flanker task but not the questionnaire; S25
completed the questionnaire but not the task. The model in
`scripts/02_models.R` uses the 22 participants with both a Flanker session and
a valid PSQI score (S21's PSQI is missing).

## Contents

```
README.md                      this file
LICENSE                        licenses (see below)
dataset_description.json       Psych-DS metadata, with the description of every column
flanker_sleep.Rproj            RStudio project: sets the working directory
data/
  raw/flanker_export.xlsx      original E-Prime export (read-only)
  study-flankersleep_task-flanker_data.csv   one row per trial; produced by scripts/01_import.R
  study-flankersleep_task-psqi_data.csv      one row per participant: sex, age, PSQI, hours of sleep
dictionaries/
  study-flankersleep_task-flanker_dictionary.csv   one row per column of the Flanker file
  study-flankersleep_task-psqi_dictionary.csv      one row per column of the PSQI file
scripts/
  01_import.R                  reads the export, applies the corrections below, writes the Flanker file
  02_models.R                  mixed model of reaction times by condition and PSQI; writes the figure
output/figures/figura1.png     reaction time by PSQI and condition (produced by 02_models.R)
```

## How to read the data

The data files are comma-separated text (UTF-8) with a header row. `NA` is a
missing value. Every column is described in `dictionaries/` and, in
machine-readable form, in `dataset_description.json`.

- In the Flanker file, `rt = 9999` marks a trial without a response (to check)
  and `NA` a missing value; the analysis excludes trials with `rt >= 3000`.
- Participants are coded `1, 2, …` in the Flanker file (`subj`) and
  `S01, S02, …` in the PSQI file (`id`): `02_models.R` matches them by removing
  the "S".
- `psqi_tot = 99` (participant S21) is a missing value.

## How to reproduce

Tested with R 4.4.2. Packages (versions used):
readxl 1.4.3, janitor 2.2.1, dplyr 1.2.0, tidyverse 2.0.0, lme4 1.1.36,
emmeans 1.10.7.

```r
install.packages(c("readxl", "janitor", "dplyr", "tidyverse", "lme4", "emmeans"))
```

Open `flanker_sleep.Rproj` in RStudio (or set the working directory to this
folder), then:

```r
source("scripts/01_import.R")   # data/raw/flanker_export.xlsx -> Flanker data file
source("scripts/02_models.R")   # model in the console, output/figures/figura1.png
```

To record the exact package versions, `renv::init()` and `renv::snapshot()`
create a `renv.lock` file.

## Changes from the original data

Applied by `scripts/01_import.R` when it reads the export:

- block 2 of participant 12, exported twice, is kept once (24 rows removed);
- 6 trials with condition "Incongruent" are written "incongruent";
- participant 7's age, typed as 2 in block 2, is set to 22 as in block 1.

Applied by `scripts/02_models.R`: `psqi_tot = 99` is treated as missing.

Applied before deposit to the PSQI file: the column with the full date of
birth (`data_nascita`) was removed, and the file was converted from
semicolon-separated with decimal comma to comma-separated.

Still open: participant 9's age is 30 in the Flanker file and 33 in the PSQI file.

## License

- Data (`data/`, `dictionaries/`, `dataset_description.json`): CC0 1.0 Universal (CC0-1.0)
- Code (`scripts/`): GNU General Public License v3.0 (GPL-3.0)
- This README and the figures (`output/`): Creative Commons Attribution 4.0 International (CC BY 4.0)
- The PSQI questionnaire is a third-party instrument and is not included: Buysse, D. J., Reynolds, C. F., Monk, T. H., Berman, S. R., & Kupfer, D. J. (1989). The Pittsburgh Sleep Quality Index. *Psychiatry Research, 28*(2), 193–213. TODO: Italian version used.

Full texts in `LICENSE`.

## How to cite

TODO: Authors (2025). Flanker and sleep quality: data and code (Version 1.0)
[Data set]. Zenodo. https://doi.org/TODO

## Related materials

Article: TODO (DOI). Preregistration: TODO.
