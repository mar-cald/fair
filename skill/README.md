# fair-check — una skill per controllare e preparare un progetto FAIR

`fair-check` è una skill nel formato aperto [Agent Skills](https://agentskills.io):
istruzioni e script che un assistente AI (Claude, Codex nell'app ChatGPT e altri
strumenti che supportano il formato) segue quando gli si chiede di controllare
la cartella di un progetto di ricerca prima di depositarla. Applica le regole
di questa dispensa e costruisce una versione della cartella pronta da caricare
su Zenodo o su un altro repository.

Che cosa fa, come installarla e come usarla è spiegato nella pagina del sito
[La skill fair-check](https://mar-cald.github.io/fair/skill.html). Questo file
descrive la cartella, per chi lavora sulla skill.

## File

| File | Contenuto |
|:--|:--|
| `fair-check/SKILL.md` | Il flusso che Claude legge ogni volta: inventario, domande iniziali, rapporto, rimandi ai file di dettaglio |
| `fair-check/references/check-data.md` | Controlli su dati e documentazione (dati, nomi, formati, README, dictionary, licenza, dati personali) |
| `fair-check/references/check-code.md` | Controlli sul codice: esecuzione, modelli già stimati, seed, pacchetti |
| `fair-check/references/check-manuscript.md` | Controlli sul manoscritto e sui numeri riportati |
| `fair-check/references/deposit.md` | La versione da depositare: piano, costruzione, dictionary, README e LICENSE, verifica, zip |
| `fair-check/references/fair-rules.md` | Le regole della dispensa, con il link alla pagina del sito |
| `fair-check/references/software-exports.md` | Che cosa scrivono Qualtrics, PsychoPy, jsPsych, Gorilla, OpenSesame ed E-Prime, e dove vanno i loro file nel deposito |
| `fair-check/assets/licenses/` | I testi ufficiali di CC0 1.0, GPL-3.0 e CC BY 4.0 |
| `fair-check/scripts/fair_scan.py` | Inventario della cartella, in sola lettura; rapporto JSON |
| `fair-check/scripts/software.py` | Come riconoscere i file dei sei programmi e che cosa significano le loro colonne |
| `fair-check/scripts/run_code.py` | Esegue gli script in una copia temporanea e ne salva l'output |
| `fair-check/scripts/manuscript_numbers.py` | Estrae il testo del manoscritto e confronta i numeri con l'output del codice |
| `fair-check/scripts/draft_dictionary.py` | Bozza di `<dataset>_dictionary.csv` con le nove colonne della dispensa |
| `fair-check/scripts/build_deposit.py` | Costruisce la versione da depositare, scrive il LICENSE, crea lo zip |
| `fair-check/scripts/make_psychds.py` | Scrive `dataset_description.json` dai data dictionary (solo con Psych-DS) |
| `fair-check.skill` | La skill impacchettata (un archivio zip della cartella `fair-check`) |

Gli script usano Python 3 senza pacchetti aggiuntivi; per leggere i file
Excel serve `openpyxl`, per quelli SPSS e Stata `pyreadstat`.

## Esempi

In `demo/` ci sono tre progetti inventati (solo dati; dati e codice; dati,
codice e preprint), ognuno con la cartella originale, il rapporto della skill e
la versione da depositare. Vedi `demo/README.md`. Sono stati prodotti con
Claude e con una versione precedente della skill, che applicava sempre Psych-DS.

## Dopo una modifica

Rigenerare `fair-check.skill` e reinstallare la skill negli assistenti che la usano:

```bash
cd skill && zip -r fair-check.skill fair-check -x '*/__pycache__/*' '*.DS_Store'
```
