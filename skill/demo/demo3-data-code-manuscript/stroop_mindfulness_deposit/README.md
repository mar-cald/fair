# Mindfulness e interferenza Stroop

Dati, codice e preprint dello studio sull'effetto di un breve training di
mindfulness sull'interferenza Stroop (Verdi & Neri, preprint 2025).

Autori: Chiara Verdi (ORCID: TODO), Marco Neri (ORCID: TODO),
Dipartimento di Psicologia Generale, Università di Padova
Contatto: chiara.verdi@example.org

## Lo studio

40 studenti dell'Università di Padova, assegnati a caso a un gruppo di
mindfulness (quattro settimane di training breve) o a un gruppo di controllo,
hanno svolto un compito Stroop colore-parola (96 prove, metà congruenti,
PsychoPy) e compilato la Mindful Attention Awareness Scale (MAAS). Le sessioni
si sono svolte in laboratorio nel marzo 2025. TODO: reclutamento, consenso.

## Contenuto

```
README.md                    questo file
LICENSE                      licenze (vedi sotto)
dataset_description.json     metadati Psych-DS, con la descrizione di ogni colonna
stroop_mindfulness.Rproj     progetto RStudio: imposta la cartella di lavoro
data/
  raw/psychopy/              un file per partecipante, esportato da PsychoPy (40 file)
  study-stroopmindfulness_description-trials_data.csv        una riga per prova, dopo le esclusioni (38 partecipanti); prodotto da scripts/01_preprocessing.R
  study-stroopmindfulness_description-participants_data.csv  una riga per partecipante: gruppo, età, sesso, punteggio MAAS (40)
dictionaries/
  study-stroopmindfulness_description-trials_dictionary.csv        le colonne del file delle prove
  study-stroopmindfulness_description-participants_dictionary.csv  le colonne del file dei partecipanti
  raw-psychopy_dictionary.csv                               le colonne dei file PsychoPy
scripts/
  01_preprocessing.R         unisce i file PsychoPy, esclude prove e partecipanti, scrive il file delle prove
  02_analysis.R              interferenza per gruppo, t-test, d di Cohen, correlazione con la MAAS, figura
output/figures/fig1_interference.png   interferenza per gruppo (prodotta da 02_analysis.R)
docs/preprint.pdf            il preprint (versione degli autori, non sottoposta a revisione)
```

## Come leggere i dati

I file di dati sono testo separato da virgole (UTF-8), con una riga di
intestazione. Ogni colonna è descritta nei file di `dictionaries/` e, in forma
leggibile dalle macchine, in `dataset_description.json`.

- Nei file PsychoPy i tempi di reazione (`key_resp.rt`) sono in secondi; nel
  file delle prove (`rt_ms`) in millisecondi.
- I codici dei partecipanti (`p01`–`p40`) sono gli stessi in tutti i file.
- Esclusioni applicate da `01_preprocessing.R`: prove con tempo di reazione
  sotto 150 ms o sopra 2500 ms; partecipanti con accuratezza sotto l'80% (p13,
  p28). Il file dei partecipanti li contiene tutti e 40.

## Come riprodurre i risultati

Provato con R 4.4.2. Pacchetti (versioni usate): tidyverse 2.0.0, here 1.0.1.

```r
install.packages(c("tidyverse", "here"))
```

Aprire `stroop_mindfulness.Rproj` in RStudio (o impostare questa cartella come
cartella di lavoro), poi:

```r
source("scripts/01_preprocessing.R")   # file PsychoPy -> file delle prove
source("scripts/02_analysis.R")        # statistiche nella console, output/figures/fig1_interference.png
```

Per registrare le versioni esatte dei pacchetti: `renv::init()` e poi
`renv::snapshot()` creano il file `renv.lock`.

## Licenza

- Dati (`data/`, `dictionaries/`, `dataset_description.json`): CC0 1.0 Universal (CC0-1.0)
- Codice (`scripts/`): GNU General Public License v3.0 (GPL-3.0)
- Preprint, figure e questo README (`docs/`, `output/`): Creative Commons Attribution 4.0 International (CC BY 4.0)
- La MAAS è uno strumento pubblicato e non è inclusa: Brown, K. W., & Ryan, R. M. (2003). The benefits of being present: Mindfulness and its role in psychological well-being. *Journal of Personality and Social Psychology, 84*(4), 822–848.

Testi completi in `LICENSE`.

## Come citare

TODO: Verdi, C., & Neri, M. (2025). Mindfulness e interferenza Stroop: dati e
codice (Versione 1.0) [Data set]. Zenodo. https://doi.org/TODO

## Materiali collegati

Preprint: TODO (DOI su PsyArXiv, se pubblicato). Preregistrazione: TODO.
