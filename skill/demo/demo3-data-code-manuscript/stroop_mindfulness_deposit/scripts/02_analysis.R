library(tidyverse)
library(here)

trials <- read_csv(here("data", "study-stroopmindfulness_level-trial_data.csv"), show_col_types = FALSE)
ppt <- read_csv(here("data", "study-stroopmindfulness_level-participant_data.csv"), show_col_types = FALSE)

interference <- trials %>%
  filter(correct == 1) %>%
  group_by(participant, congruent) %>%
  summarise(rt = mean(rt_ms), .groups = "drop") %>%
  pivot_wider(names_from = congruent, values_from = rt) %>%
  mutate(interference = `TRUE` - `FALSE`) %>%
  mutate(interference = -interference) %>%
  left_join(ppt, by = "participant")

interference %>%
  group_by(group) %>%
  summarise(n = n(), M = mean(interference), SD = sd(interference)) %>%
  print()

print(t.test(interference ~ group, data = interference, var.equal = TRUE))
# Cohen's d with pooled SD
g <- split(interference$interference, interference$group)
sp <- sqrt(((length(g[[1]]) - 1) * var(g[[1]]) + (length(g[[2]]) - 1) * var(g[[2]])) /
           (length(g[[1]]) + length(g[[2]]) - 2))
cat("Cohen's d:", round((mean(g[[1]]) - mean(g[[2]])) / sp, 3), "\n")
print(cor.test(~ interference + maas_score, data = interference))

p <- ggplot(interference, aes(group, interference)) + geom_boxplot()
ggsave(here("output", "figures", "fig1_interference.png"), p, width = 5, height = 4)
