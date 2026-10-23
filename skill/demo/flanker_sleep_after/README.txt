Flanker and sleep quality
=========================

Data from the flanker experiment (2025). Participants did the flanker task
and filled out the PSQI questionnaire.

Authors: TODO (names and ORCID)
Contact: giulia.bianchi@example.org


About the study
---------------
TODO: research question, where and when the data were collected (months,
lab or online), how participants were recruited.

24 participants completed the Flanker task (48 trials in 2 blocks of 24).
The sleep questionnaire contains 24 participants as well, but participant 19
has no questionnaire and S25 has no Flanker data, so 23 participants have
both.


Contents
--------
data/raw/flanker_export.xlsx         original E-Prime export, read-only
data/flanker_trials.csv              one row per trial; produced by scripts/01_import.R
data/flanker_trials_dictionary.csv   description of each column of flanker_trials.csv
data/questionario_sonno.csv          one row per participant (sleep questionnaire)
data/questionario_sonno_dictionary.csv  description of each column of questionario_sonno.csv
scripts/01_import.R                  reads the Excel export, writes data/flanker_trials.csv
scripts/02_models.R                  mixed model of reaction times by condition and PSQI;
                                     writes output/figures/figura1.png
output/figures/                      figures produced by the scripts
flanker_sleep.Rproj                  RStudio project (sets the working directory)
Analisi vecchie/prova.R              TODO: old test script, not part of the analysis
                                     (it reads a file that is not here): remove or describe
materials/PSQI_italiano.pdf          TODO: third-party questionnaire, do not redistribute


How to read the data
--------------------
All data files are plain text (CSV) and open with any spreadsheet program,
R or Python. Each data file has a dictionary next to it (<name>_dictionary.csv)
describing every column: meaning, type, unit, allowed values, coding and how
missing values are written.

- data/flanker_trials.csv is comma-separated.
- data/questionario_sonno.csv is semicolon-separated with a decimal comma
  (Excel with Italian settings): in R, read it with read.csv2().
- Participant codes differ between the two files: subj 1 in the trials is S01
  in the questionnaire. 02_models.R matches them by removing the "S".
- In flanker_trials.csv, rt = 9999 marks TODO (timeouts?) and an empty cell a
  missing response; trials with rt >= 3000 are excluded from the analysis.


How to reproduce
----------------
Software: R 4.4.2 (tested); RStudio is optional.

Packages (versions used when this was tested):
  readxl 1.4.3, janitor 2.2.1, dplyr 1.2.0, tidyverse 2.0.0,
  lme4 1.1.36, emmeans 1.10.7, ggplot2 4.0.2

Install them with:
  install.packages(c("readxl", "janitor", "dplyr", "tidyverse", "lme4", "emmeans"))

Open flanker_sleep.Rproj (or set the working directory to this folder), then:
  source("scripts/01_import.R")   # data/raw/flanker_export.xlsx -> data/flanker_trials.csv
  source("scripts/02_models.R")   # model output in the console, output/figures/figura1.png

01_import.R regenerates data/flanker_trials.csv identically from the Excel
export, so it can be skipped if you start from the CSV.


License
-------
TODO: choose the licenses (see LICENSE). Recommended:
- Data (data/): CC0 1.0 Universal (CC0-1.0)
- Code (scripts/): MIT (the current LICENSE file)
- Third-party materials (PSQI questionnaire): not redistributed; cite
  Buysse et al. (1989) and the Italian validation used.


How to cite
-----------
TODO: author(s) (year). Title (Version 1.0) [Data set]. Repository.
https://doi.org/TODO


Related materials
-----------------
Article: TODO (DOI)
Preregistration: TODO (DOI or link)
