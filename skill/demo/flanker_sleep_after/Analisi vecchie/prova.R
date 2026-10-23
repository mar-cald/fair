d <- read.csv("dati_finali.csv")
t.test(rt ~ cond, data = d)
