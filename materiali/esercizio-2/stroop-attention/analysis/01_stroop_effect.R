# 01_stroop_effect.R ---------------------------------------------------------
# Legge tutti i file _data.csv della cartella data/ e calcola il costo Stroop.
# Da eseguire con la radice del dataset come working directory.

files <- list.files("data", pattern = "_data\\.csv$", full.names = TRUE)
d <- do.call(rbind, lapply(files, read.csv, stringsAsFactors = FALSE))

stopifnot(nrow(d) > 0, all(d$condition %in% c("congruent", "incongruent")))

# Solo prove corrette, come da preregistrazione
correct <- subset(d, correct == 1)

means <- aggregate(rt_ms ~ participant_id + condition, data = correct, FUN = mean)
print(means)

cost <- with(means, tapply(rt_ms, list(participant_id, condition), identity))
cat("\nStroop cost (incongruent - congruent), in ms:\n")
print(round(cost[, "incongruent"] - cost[, "congruent"], 1))
