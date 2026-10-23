# Merge the PsychoPy files, exclude fast/slow trials and low-accuracy participants
library(tidyverse)
library(here)

files <- list.files(here("data", "raw", "psychopy"), pattern = "\\.csv$", full.names = TRUE)
raw <- map_dfr(files, read_csv, show_col_types = FALSE)

trials <- raw %>%
  transmute(participant,
            trial = trials.thisN + 1,
            congruent = congruent == 1,
            correct = key_resp.corr,
            rt_ms = key_resp.rt * 1000) %>%
  filter(rt_ms >= 150, rt_ms <= 2500)

acc <- trials %>% group_by(participant) %>% summarise(acc = mean(correct))
keep <- acc %>% filter(acc >= .80) %>% pull(participant)
cat("Participants excluded for accuracy < 80%:", setdiff(acc$participant, keep), "\n")

trials %>%
  filter(participant %in% keep) %>%
  write_csv(here("data", "stroop_clean.csv"))
