# fair-check — una skill per controllare e preparare un progetto FAIR

`fair-check` è una skill per Claude: un insieme di istruzioni e script che
Claude segue quando gli si chiede di controllare la cartella di un progetto di
ricerca prima di depositarla. Applica le regole di questa dispensa
(<https://mar-cald.github.io/fair/>) e poi costruisce una versione della
cartella pronta da caricare su Zenodo o su un altro repository.

## Cosa controlla

La skill guarda prima che cosa c'è nella cartella e fa i controlli che hanno
senso per quel materiale.

| Nella cartella | Controlli |
|:--|:--|
| solo dati | dati, struttura e nomi, formati, README, data dictionary, licenza, dati personali |
| dati e codice | i precedenti, più: il codice gira? quali pacchetti servono? |
| dati, codice e manoscritto o preprint | tutti, più: i numeri riportati escono dal codice? |

1. **Dati**:
   - per ogni CSV/TSV: tipo di ogni colonna, intervallo dei valori, valori
     mancanti codificati in più modi (`NA`, cella vuota, `-99`), categorie
     scritte in modi diversi (`M` / `m`), righe duplicate, virgola decimale;
   - colonne che sembrano dati personali (e-mail, indirizzo IP, coordinate,
     codice fiscale, data di nascita);
   - i partecipanti: la stessa persona con due età diverse, ID presenti in un
     file e non nell'altro, ID scritti in modi diversi (`sub-01` e `1`).

   I file con le stesse colonne (per esempio un file PsychoPy per
   partecipante) sono trattati come un unico insieme.
2. **Struttura e nomi**: spazi, accenti e parole come `finale` nei nomi,
   numerazione senza zero davanti, file e cartelle che non servono.
3. **Formati**: `.xlsx`, `.sav`, `.docx` senza una copia in formato aperto.
4. **README**: quali delle otto sezioni della dispensa ci sono, quali file non
   sono nominati.
5. **Data dictionary**: quali file non ne hanno uno, quali colonne mancano,
   valori fuori da `allowed_values`, codici non descritti.
6. **Licenza**: quale copre dati, codice, manoscritto e materiali, e se è adatta.
7. **Codice**:
   - lo esegue in una copia temporanea e riporta quali script girano e
     perché gli altri si fermano;
   - se si fermano per un `setwd()` o un percorso assoluto, li riesegue in una
     seconda copia senza quella riga, per vedere se l'analisi funziona e se gli
     errori nei dati arrivano fino al modello.
8. **Manoscritto**:
   - trova le statistiche riportate (M, SD, t, F, r, p, CI…) e le cerca
     nell'output del codice: quali coincidono, quali no, quali nessuno script
     le produce;
   - controlla anche la Data availability, il numero di partecipanti e le
     esclusioni.

## La versione da depositare

Dopo il rapporto, e dopo aver chiesto le decisioni che spettano al
ricercatore (colonne personali da togliere, correzioni ai dati, licenze), la
skill costruisce `<progetto>_deposit/` accanto alla cartella originale, che non
viene mai modificata:

```
<progetto>_deposit/
├── README.md                 le otto sezioni della dispensa
├── LICENSE                   cosa vale per cosa, poi i testi completi
├── dataset_description.json  metadati Psych-DS, con il data dictionary
├── data/                     file di dati con nomi Psych-DS (..._data.csv)
│   └── raw/                  export originali
├── dictionaries/             un <nome>_dictionary.csv per ogni file di dati
├── scripts/                  codice, numerato nell'ordine di esecuzione
├── output/                   figure e tabelle prodotte dagli script
├── materials/                materiali propri
└── docs/                     preprint, preregistrazione
```

- **Dati:** i file sono rinominati secondo Psych-DS.
- **Script:** i percorsi al loro interno sono aggiornati, poi il codice viene
  rieseguito nella cartella nuova per verificare che giri.
- **Licenze predefinite:** CC0 1.0 per i dati, GPL-3.0 per il codice, CC BY 4.0
  per preprint, figure e materiali. I testi completi sono inclusi nella skill.
- **Zip:** alla fine la skill crea `<progetto>_deposit.zip`, il file unico da
  caricare.

Il controllo definitivo di Psych-DS si fa con il validator ufficiale
(<https://psych-ds.github.io/validator/>).

## Esempi

In `demo/` ci sono tre progetti inventati (solo dati; dati e codice; dati,
codice e preprint). Per ognuno ci sono la cartella originale, il rapporto
della skill e la versione da depositare. Vedi `demo/README.md`.

## Come installarla

**Claude Code** (terminale o app desktop, scheda Code): copiare la cartella
`fair-check/` in `~/.claude/skills/`:

```bash
cp -r skill/fair-check ~/.claude/skills/
```

Poi, aperta la cartella del progetto, basta chiedere per esempio
*"controlla se questa cartella è pronta da depositare"*, oppure scrivere
`/fair-check`. In questa modalità Claude può eseguire il codice R e Python con
i programmi installati sul computer.

**Claude nel browser o nell'app** (claude.ai): la skill si carica dalle
impostazioni, nella sezione delle skill, usando il file `fair-check.skill`
(è un archivio zip). Serve che sia attiva l'esecuzione di codice. La cartella
del progetto si allega come zip alla conversazione. In questo ambiente R di
solito non è installato: il controllo del codice R si limita a pacchetti,
percorsi e file citati, senza eseguirlo.

## File

| File | Contenuto |
|:--|:--|
| `fair-check/SKILL.md` | Le istruzioni che Claude segue: controlli, rapporto, versione da depositare |
| `fair-check/references/fair-rules.md` | Le regole della dispensa, con il link alla pagina del sito |
| `fair-check/assets/licenses/` | I testi ufficiali di CC0 1.0, GPL-3.0 e CC BY 4.0 |
| `fair-check/scripts/fair_scan.py` | Scansione in sola lettura della cartella; rapporto JSON |
| `fair-check/scripts/run_code.py` | Esegue gli script in una copia temporanea e ne salva l'output |
| `fair-check/scripts/manuscript_numbers.py` | Estrae il testo del manoscritto e confronta i numeri con l'output del codice |
| `fair-check/scripts/draft_dictionary.py` | Bozza di `<dataset>_dictionary.csv` con le nove colonne della dispensa |
| `fair-check/scripts/build_deposit.py` | Costruisce la versione da depositare, scrive il LICENSE, crea lo zip |
| `fair-check/scripts/make_psychds.py` | Scrive `dataset_description.json` dai data dictionary |
| `fair-check.skill` | La skill impacchettata, da caricare su claude.ai |

Gli script usano solo Python 3 senza pacchetti aggiuntivi.

Dopo aver modificato la skill, `fair-check.skill` va rigenerato
(`cd skill && zip -r fair-check.skill fair-check -x '*/__pycache__/*' '*.DS_Store'`).
