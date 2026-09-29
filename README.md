# Hands-on Open Science — dispensa del seminario

Sito Quarto con i materiali del seminario *"Hands-on Open Science: alternative a
OSF e strumenti per la gestione FAIR dei dati"* (Dipartimento di Psicologia
Generale, Università di Padova, 23 settembre 2026).

Le pagine sono file `.qmd` in questa cartella; `quarto render` genera il sito in
`docs/`, pubblicato con GitHub Pages.

| File | Contenuto |
|---|---|
| `index.qmd` | Home: dove mettere dati, codice e materiali (tre schede) e il vademecum da scaricare. Per cercare nel sito si usa la ricerca integrata di Quarto (lente in alto a destra) |
| `apertura.qmd` | Che cosa sta succedendo a OSF: le tempistiche della dismissione |
| `ma.qmd` | Esercizio di apertura: a coppie ci si scambia la cartella e si spunta una checklist (pagina collegata dall'apertura, fuori dal menu) |
| `fair.qmd` | I principi FAIR e il Data Management Plan |
| `repository.qmd` | Dove archiviare e come scegliere il repository |
| `zenodo.qmd` | Depositare su Zenodo (incluse correzioni e nuove versioni) |
| `psycharchives.qmd` | Depositare su PsychArchives (incluse correzioni e nuove versioni) |
| `confronto.qmd` | Zenodo e PsychArchives a confronto (tabella) |
| `licenze.qmd` | Licenze per dati, codice e materiali |
| `struttura-1.qmd` | README, data dictionary, formati e struttura delle cartelle |
| `struttura-2.qmd` | Psych-DS, uno standard per organizzare i dati |
| `esempio.qmd` | Un esempio completo: un progetto modello con tutte le parti |
| `risorse.qmd` | Vademecum da scaricare, checklist, link, glossario |
| `segnala.qmd` | Come segnalare un errore (email o issue GitHub); si apre dall'icona bug in navbar |
| `_quarto.yml` | Titolo del sito, voci del menu, opzioni generali |
| `custom.scss` | Grafica del sito: colori (in cima al file), tipografia (Libre Franklin) e stile della navbar |
| `booklet/` | Sorgente del vademecum in PDF (vedi sotto) |

## Ricerca del sito

La ricerca integrata di Quarto indicizza anche alcuni **sinonimi nascosti**:
in cima a ogni pagina c'è un blocco `::: {.visually-hidden}` con parole chiave
(per es. "SPSS", "leggimi", "anonimizzare") che non compaiono nel testo ma
aiutano a trovare la sezione giusta. Per aggiungere un sinonimo, mettilo in quel
blocco della pagina pertinente.

## Materiali per le esercitazioni

```
materiali/
└── struttura-2/
    └── stroop-attention/   dataset di esempio conforme a Psych-DS
```

I dataset sono **fittizi**, costruiti per l'esercitazione.

## Vademecum PDF

`booklet/vademecum.pdf` è il *Vademecum FAIR*: l'essenziale del sito in 8
pagine A4 orizzontali (perché FAIR, formati aperti, README, data dictionary,
licenze, Zenodo, checklist), con il testo a sinistra e uno schema a destra.

La sorgente è `booklet/vademecum.qmd`. Il testo è in **Markdown**, come le
pagine del sito; in cima al file c'è un blocco Typst con copertina, stili e le
funzioni usate dagli schemi, che di solito non serve toccare. Per rigenerare il
PDF, dalla cartella `booklet/`:

```
quarto render vademecum.qmd
```

Nella cartella:

- `_quarto.yml` imposta il formato Typst e la cartella dei font;
- `typst-show.typ` è volutamente vuoto: toglie l'impaginazione di default di
  Quarto, così copertina e stili li decide il blocco Typst del `.qmd`;
- `fonts/` contiene Libre Franklin, necessario per la compilazione.

Il `quarto render` del sito esclude `booklet/` (voce `"!booklet/"` in
`_quarto.yml`) e copia soltanto il PDF in `docs/` (voce `resources`), dove è
linkato nella home, in Risorse e nel footer. Dopo aver modificato
`vademecum.qmd`, quindi, si rigenera prima il PDF e poi il sito.

## Licenza

Testi CC BY 4.0; dataset di esempio CC0 1.0.
