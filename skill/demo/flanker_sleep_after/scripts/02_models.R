library(tidyverse)
library(lme4)
library(emmeans)

trials <- read.csv("data/flanker_trials.csv")
quest  <- read.csv2("data/questionario_sonno.csv")
quest$subj <- as.numeric(gsub("S", "", quest$id))

d <- trials %>%
  filter(rt < 3000, acc == 1) %>%
  left_join(quest, by = "subj")

m <- lmer(rt ~ cond * psqi_tot + (1 | subj), data = d)
print(summary(m))
print(emmeans(m, ~ cond))

p <- ggplot(d, aes(psqi_tot, rt, colour = cond)) + geom_smooth(method = "lm")
ggsave("output/figures/figura1.png", p, width = 6, height = 4)
