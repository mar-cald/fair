library(tidyverse)
library(lme4)
library(emmeans)

trials <- read.csv("data/study-flankersleep_task-flanker_data.csv")
quest  <- read.csv("data/study-flankersleep_task-psqi_data.csv")
quest$psqi_tot[quest$psqi_tot == 99] <- NA   # 99 = missing (outside the 0-21 range of the PSQI)
quest$subj <- as.numeric(gsub("S", "", quest$id))

d <- trials %>%
  filter(rt < 3000, acc == 1) %>%
  left_join(quest, by = "subj")

m <- lmer(rt ~ cond * psqi_tot + (1 | subj), data = d)
print(summary(m))
print(emmeans(m, ~ cond))

p <- ggplot(d, aes(psqi_tot, rt, colour = cond)) + geom_smooth(method = "lm")
ggsave("output/figures/figura1.png", p, width = 6, height = 4)
