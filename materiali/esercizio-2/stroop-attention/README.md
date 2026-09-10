# Effetto Stroop e training attentivo — dataset in formato Psych-DS

Dataset **didattico e fittizio** per il seminario "Hands-on Open Science"
(Università di Padova, 23 settembre 2026). Serve come esempio minimo ma
completo di dataset conforme a [Psych-DS](https://psychds-docs.readthedocs.io/).

## Struttura

```
stroop-attention/
├── dataset_description.json          metadati (obbligatorio, questo nome esatto)
├── README.md
├── LICENSE
├── data/                             (obbligatoria)
│   ├── study-stroop_subject-01_data.csv
│   ├── study-stroop_subject-02_data.csv
│   └── raw/                          export originali, ignorati dal validator
│       └── subject-01_eprime_export.txt
└── analysis/
    └── 01_stroop_effect.R
```

## I dati

Una riga = una prova. Due partecipanti, 12 prove ciascuno, compito Stroop
cromatico con condizioni congruente e incongruente.

Il significato delle colonne è dichiarato nel campo `variableMeasured` di
`dataset_description.json`: in Psych-DS il data dictionary vive nei metadati,
non in un file a parte.

## Validazione

Trascinate la cartella `stroop-attention/` (non la sottocartella `data/`) sul
validator: <https://psych-ds.github.io/validator/>. La validazione avviene nel
browser: i file non vengono caricati da nessuna parte.

## Licenza

Dati e metadati CC0 1.0; codice in `analysis/` con licenza MIT. Vedi `LICENSE`.
