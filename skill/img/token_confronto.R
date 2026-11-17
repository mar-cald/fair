# Figura per le slide: token e operazioni con e senza fair-check
# Dati: prove del 17/11/2026, stessa richiesta a due assistenti (Claude), uno con la skill e uno senza.
# Cartella di prova: due prove per lato, skill prima di accorpare i comandi.
# Cartella SEB (vera): una prova per lato, skill dopo aver accorpato i comandi.

library(ggplot2)

d <- data.frame(
  cartella = rep(c("Cartella di prova\n(2 prove per lato)", "Cartella vera, SEB\n(1 prova per lato)"), each = 2),
  versione = rep(c("Senza skill", "Con fair-check"), 2),
  token = c(mean(c(78540, 80317)), mean(c(110430, 109325)), 139397, 151283),
  operazioni = c(mean(c(8, 10)), mean(c(23, 21)), 16, 15)
)
d$versione <- factor(d$versione, levels = c("Senza skill", "Con fair-check"))
d$cartella <- factor(d$cartella, levels = unique(d$cartella))
d$etichetta <- paste0(round(d$token / 1000), " mila token, ", d$operazioni, " operazioni")

colori <- c("Senza skill" = "#9a948a", "Con fair-check" = "#8f1f27")

p <- ggplot(d, aes(x = token / 1000, y = versione, fill = versione)) +
  geom_col(width = 0.62) +
  geom_text(aes(label = etichetta), hjust = -0.04, size = 6.6, colour = "#222222") +
  facet_wrap(~cartella, ncol = 1) +
  scale_fill_manual(values = colori, guide = "none") +
  scale_x_continuous(limits = c(0, 290), breaks = c(0, 50, 100, 150), expand = c(0, 0)) +
  labs(x = "migliaia di token", y = NULL) +
  theme_minimal(base_size = 22) +
  theme(panel.grid.major.y = element_blank(), panel.grid.minor = element_blank(),
        panel.grid.major.x = element_line(colour = "#e6e2da", linewidth = 0.4),
        strip.text = element_text(hjust = 0, face = "bold", size = 21, colour = "#222222"),
        axis.text.y = element_text(size = 21, colour = "#222222"),
        axis.text.x = element_text(colour = "#555555"),
        axis.title.x = element_text(colour = "#555555", size = 18),
        plot.margin = margin(6, 12, 6, 6))

ggsave("token_confronto.svg", p, width = 11, height = 5.2, bg = "transparent")
