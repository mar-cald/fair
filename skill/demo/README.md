# Tre esempi di fair-check

Tre progetti inventati, con i problemi tipici delle cartelle reali, su cui è
stata eseguita la skill. I dati sono fittizi.

| Esempio | Cosa contiene | Controlli eseguiti |
|:--|:--|:--|
| `demo1-data/` | solo dati: un questionario online esportato da Qualtrics | dati, struttura, formati, README, data dictionary, licenza, dati personali |
| `demo2-data-code/` | dati e script R: compito Flanker e questionario sul sonno | i precedenti, più: il codice gira? quali pacchetti servono? |
| `demo3-data-code-manuscript/` | dati, script R e preprint: Stroop e mindfulness | tutti, più: i numeri del preprint escono dal codice? |

In ogni cartella:

- `<progetto>/`: la cartella così come la consegnerebbe chi ha fatto lo studio;
- `fair-check-report.md`: il rapporto della skill;
- `<progetto>_deposit/`: la versione da depositare costruita dalla skill;
- `<progetto>_deposit.zip`: lo stesso, in un unico file da caricare su Zenodo.

## Com'è fatta la versione da depositare

Sempre le stesse cartelle, create solo se hanno un contenuto:

```
<progetto>_deposit/
├── README.md                 le otto sezioni della dispensa
├── LICENSE                   cosa vale per cosa, poi i testi completi
├── dataset_description.json  metadati Psych-DS, con il data dictionary
├── data/                     file di dati, nomi chiave-valore_..._data.csv
│   └── raw/                  export originali
├── dictionaries/             un <nome>_dictionary.csv per ogni file di dati
├── scripts/                  codice, numerato nell'ordine di esecuzione
├── output/figures/           prodotti dagli script
└── docs/                     preprint
```

Licenze: CC0 1.0 per i dati, GPL-3.0 per il codice, CC BY 4.0 per preprint,
figure e README.

## Le decisioni prese al posto dei ricercatori

La skill, prima di costruire la versione da depositare, chiede alcune decisioni
che spettano a chi ha fatto lo studio. Per questi esempi sono state prese così:

**demo1**:
- tolte le colonne `IPAddress`, `LocationLatitude`, `LocationLongitude`,
  `RecipientEmail`;
- depositato l'export completo in CSV, senza l'Excel originale (che contiene
  quelle colonne);
- corretti l'età scritta in lettere, `donna` → `Donna`, i valori fuori scala e la
  risposta duplicata;
- rinominate le colonne `Età` e `Duration (in seconds)`;
- il MAQ-10 è considerato un questionario degli autori.

**demo2**:
- le correzioni ai dati (blocco duplicato, `Incongruent`, età del partecipante
  7, PSQI 99) sono state messe negli script, così si vedono e si riproducono;
- tolta la data di nascita;
- lasciati fuori il PSQI (strumento di terzi) e lo script vecchio;
- l'età del partecipante 9 resta un punto aperto.

**demo3**:
- il preprint è incluso così com'è, anche se riporta un t-test che non
  coincide con il codice: correggerlo è compito degli autori;
- le soglie di esclusione restano quelle del codice (150–2500 ms), segnalate
  come punto aperto.

Autori, ORCID, date e DOI restano `TODO` dove non erano nella cartella.
