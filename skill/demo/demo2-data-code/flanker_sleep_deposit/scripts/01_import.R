# Import the E-Prime export and save a clean CSV
library(readxl)
library(janitor)
library(dplyr)

raw <- read_excel("data/raw/flanker_export.xlsx") %>% clean_names()

trials <- raw %>%
  rename(subj = subject, cond = condition, rt = rt, acc = acc) %>%
  select(subj, age, block, trial, cond, rt, acc) %>%
  # Corrections to the export (see README, "Changes from the original data")
  distinct() %>%                                # block 2 of participant 12 was exported twice
  mutate(cond = tolower(cond),                  # 6 trials were written "Incongruent"
         age = if_else(subj == 7, 22, age))     # participant 7: age typed as 2 in block 2

write.csv(trials, "data/study-flankersleep_task-flanker_data.csv", row.names = FALSE)
