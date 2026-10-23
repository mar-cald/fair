# fair-check — una skill per controllare se un progetto è FAIR

`fair-check` è una skill per Claude: un insieme di istruzioni e script che
Claude segue quando gli si chiede di controllare la cartella di un progetto di
ricerca prima di depositarla. Applica le regole di questa dispensa
(<https://mar-cald.github.io/fair/>).

## Cosa controlla

1. **Dati**: per ogni CSV/TSV, tipo di ogni colonna, intervallo dei valori,
   valori mancanti codificati in più modi (`NA`, cella vuota, `-99`), categorie
   scritte in modi diversi (`M` / `m`), righe duplicate, virgola decimale,
   colonne che sembrano dati personali (e-mail, codice fiscale, data di nascita).
   Controlla anche i partecipanti: la stessa persona con due età o due gruppi
   diversi nello stesso file, ID presenti in un file e non nell'altro, ID
   scritti in modi diversi (`sub-01` e `1`), età che non coincidono fra il
   file dei trial e quello dei questionari.
2. **Struttura e nomi**: spazi, accenti e parole come `finale` o `def` nei nomi,
   numerazione senza zero davanti, dati grezzi separati, cartelle vuote.
3. **Formati**: file `.xlsx`, `.sav`, `.docx` senza una copia in formato aperto.
4. **README**: quali delle otto sezioni della dispensa ci sono e quali file
   non sono mai nominati.
5. **Data dictionary**: quali file di dati non ne hanno uno, quali colonne
   mancano, nomi che non coincidono, valori fuori da `allowed_values`, codici
   non descritti in `coding`.
6. **Licenza**: quale licenza copre dati, codice e materiali, e se è adatta
   (CC0 o CC BY per i dati, GPL-3.0 o MIT per il codice, CC BY per i materiali).
7. **Codice**: lo esegue in una copia temporanea della cartella e riporta
   quali script girano, quali si fermano e perché (`setwd()`, percorsi
   assoluti, file mancanti, pacchetti non installati). Se si fermano per un
   `setwd()` o un percorso assoluto, li riesegue in una seconda copia senza
   quella riga, per vedere se l'analisi in sé funziona e se gli errori nei
   dati arrivano fino al modello.
8. **Pacchetti**: elenco dei pacchetti usati, confrontato con quelli
   dichiarati (`renv.lock`, `requirements.txt`, README).

Il risultato è un rapporto con lo stato di ogni punto e un elenco ordinato di
cose da sistemare. Durante il controllo la cartella non viene modificata.
Dopo il rapporto, e solo con il consenso di chi la usa, Claude può scrivere
la bozza dei data dictionary, le sezioni mancanti del README (software,
pacchetti, ordine degli script) e il file `LICENSE`.

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

## Cosa resta fuori, per ora

- Verificare che i numeri riportati nel manoscritto si ottengano dal codice.
- Convertire dati e dictionary nella struttura Psych-DS.

## File

| File | Contenuto |
|:--|:--|
| `fair-check/SKILL.md` | Le istruzioni che Claude segue: ordine dei controlli, formato del rapporto, cosa può correggere |
| `fair-check/references/fair-rules.md` | Le regole della dispensa (nomi, formati, README, dictionary, licenze, codice, privacy), con il link alla pagina del sito |
| `fair-check/scripts/fair_scan.py` | Scansione in sola lettura della cartella; produce un rapporto JSON |
| `fair-check/scripts/run_code.py` | Esegue gli script in una copia temporanea e riporta errori e pacchetti mancanti |
| `fair-check/scripts/draft_dictionary.py` | Scrive la bozza di `<dataset>_dictionary.csv` con le nove colonne della dispensa |
| `fair-check.skill` | La skill impacchettata, da caricare su claude.ai |

Gli script usano solo Python 3 senza pacchetti aggiuntivi.

Dopo aver modificato la skill, `fair-check.skill` va rigenerato
(`cd skill && zip -r fair-check.skill fair-check -x '*/__pycache__/*'`).
