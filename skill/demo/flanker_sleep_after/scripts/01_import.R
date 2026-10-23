# Import the E-Prime export and save a clean CSV
library(readxl)
library(janitor)
library(dplyr)

raw <- read_excel("data/raw/flanker_export.xlsx") %>% clean_names()

trials <- raw %>%
  rename(subj = subject, cond = condition, rt = rt, acc = acc) %>%
  select(subj, age, block, trial, cond, rt, acc)

write.csv(trials, "data/flanker_trials.csv", row.names = FALSE)
