library(readr)
library(dplyr)
d <- read_csv("data/raw_trials.csv")
g <- read_csv("output/groups.csv")
ids <- read_csv("output/ids_model.csv")
d$age <- as.numeric(Sys.Date() - as.Date(d$birth)) / 365.25
d |> group_by(id) |> summarise(acc = mean(acc)) |> kable()
write_csv(d |> filter(id %in% ids$id), "output/clean.csv")
