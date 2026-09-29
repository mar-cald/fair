// FAIR in pratica — booklet operativo tratto dal sito "Hands-on Open Science".
// Compilare dalla cartella booklet/ con:
//   quarto typst compile booklet.typ fair-in-pratica.pdf --font-path fonts

// ---------------------------------------------------------------------------
// Colori (gli stessi del sito, vedi custom.scss)
// ---------------------------------------------------------------------------
#let acc   = rgb("#8f1f27")   // rosso Unipd
#let ink   = rgb("#1a1714")
#let muted = rgb("#5a534b")
#let rule  = rgb("#c8c1b6")
#let tint  = rgb("#f7f0ec")   // fondo dei riquadri
#let grey  = rgb("#f3f1ee")   // fondo del codice
#let ok    = rgb("#2d6a3e")
#let okbg  = rgb("#eef5ef")
#let nobg  = rgb("#fbeeee")

#set document(
  title: "FAIR in pratica",
  author: "Margherita Calderan",
  keywords: ("FAIR", "open data", "Zenodo", "licenze", "DMP"),
)

#set page(
  paper: "a4",
  margin: (x: 19mm, top: 21mm, bottom: 19mm),
  header: context {
    if counter(page).get().first() > 1 [
      #set text(size: 7.5pt, fill: muted, tracking: 0.04em)
      #upper[FAIR in pratica] #h(1fr) #upper[Manuale operativo]
      #v(-4pt)
      #line(length: 100%, stroke: 0.4pt + rule)
    ]
  },
  footer: context {
    if counter(page).get().first() > 1 [
      #set text(size: 7.5pt, fill: muted)
      #h(1fr) #counter(page).display() #h(1fr)
    ]
  },
)

#set text(font: "Libre Franklin", size: 9.6pt, fill: ink, lang: "it")
#set par(leading: 0.62em, spacing: 0.95em)
#set list(indent: 2pt, body-indent: 6pt, spacing: 0.55em, marker: text(fill: acc)[▪])
#set enum(indent: 2pt, body-indent: 6pt, spacing: 0.55em)
#set strong(delta: 250)

#show link: set text(fill: acc)
#show raw: set text(font: "DejaVu Sans Mono", size: 7.9pt)
#show raw.where(block: false): box.with(fill: grey, inset: (x: 2.5pt), outset: (y: 2.5pt), radius: 2pt)
#show raw.where(block: true): block.with(fill: grey, inset: 9pt, radius: 3pt, width: 100%)

// Titolo di sezione: numero + titolo, filetto rosso
#let sec-n = counter("sec")
#show heading.where(level: 1): it => {
  sec-n.step()
  v(2pt)
  block(below: 12pt)[
    #set text(size: 20pt, weight: 700, fill: ink)
    #context text(fill: acc)[#sec-n.get().first()] #h(6pt) #it.body
    #v(-9pt)
    #line(length: 100%, stroke: 1.4pt + acc)
  ]
}
#show heading.where(level: 2): it => block(above: 15pt, below: 7pt)[
  #set text(size: 12pt, weight: 700, fill: acc)
  #it.body
]
#show heading.where(level: 3): it => block(above: 10pt, below: 5pt)[
  #set text(size: 10pt, weight: 700)
  #it.body
]

// Tabelle: righe sottili, intestazione in grassetto
#set table(
  stroke: (x, y) => (
    top: if y == 0 { 0pt } else { 0.4pt + rule },
    bottom: 0.8pt + if y == 0 { acc } else { rule },
  ),
  inset: (x: 5pt, y: 5pt),
)
#show table.cell.where(y: 0): set text(weight: 700, size: 8.6pt, fill: acc)
#show table: set text(size: 8.9pt)

// ---------------------------------------------------------------------------
// Componenti
// ---------------------------------------------------------------------------
#let lead(body) = block(below: 12pt, text(size: 11.5pt, fill: ink, weight: 500, body))

#let callout(title: none, fill: tint, color: acc, body) = block(
  fill: fill, stroke: (left: 3pt + color), inset: (x: 11pt, y: 9pt),
  radius: (right: 3pt), width: 100%, breakable: false,
)[
  #if title != none { text(weight: 700, fill: color, size: 9.8pt, title); v(-3pt) }
  #body
]

#let panel(title, color, bg, body) = block(
  fill: bg, inset: 9pt, radius: 3pt, width: 100%, height: auto, stroke: 0.5pt + color.lighten(55%),
)[
  #text(weight: 700, fill: color, size: 9pt, upper(title))
  #v(-2pt)
  #body
]
#let yes(title: "Sì", body) = panel(title, ok, okbg, body)
#let no(title: "No", body) = panel(title, acc, nobg, body)

#let num(n) = box(
  circle(radius: 8pt, fill: acc, stroke: none,
    align(center + horizon, text(fill: white, weight: 700, size: 8.5pt, str(n)))),
  baseline: 3.5pt,
)
#let num-top(n) = move(dy: -3.5pt, num(n))

// Passi numerati: numero tondo a sinistra, titolo + testo a destra
#let steps(gutter: 7pt, ..items) = {
  let rows = ()
  for (i, it) in items.pos().enumerate() {
    rows.push(num-top(i + 1))
    rows.push([#text(weight: 700, it.at(0)) #h(3pt) #it.at(1)])
  }
  grid(columns: (20pt, 1fr), row-gutter: gutter, column-gutter: 4pt, ..rows)
}

#let tag(body, color: acc) = box(
  fill: color, inset: (x: 5pt, y: 2.5pt), radius: 2pt,
  text(fill: white, weight: 700, size: 7.5pt, tracking: 0.04em, upper(body)),
)

#let minibox(title, body) = block(
  stroke: 0.6pt + rule, inset: 9pt, radius: 3pt, width: 100%, breakable: false,
)[
  #text(size: 7.5pt, weight: 700, fill: muted, tracking: 0.05em, upper(title))
  #v(-3pt)
  #set text(size: 8.8pt)
  #body
]

// ===========================================================================
// COPERTINA
// ===========================================================================
#page(margin: 0pt, header: none, footer: none)[
  #block(fill: acc, width: 100%, inset: (x: 19mm, top: 19mm, bottom: 11mm))[
    #set text(fill: white)
    #show link: set text(fill: white)
    #show link: underline.with(stroke: 0.4pt + white.transparentize(40%), offset: 2pt)
    #text(size: 8.5pt, weight: 600, tracking: 0.12em)[HANDS-ON OPEN SCIENCE]
    #h(7pt) #box(line(length: 9pt, angle: 90deg, stroke: 0.6pt + white.transparentize(45%)), baseline: 1pt) #h(7pt)
    #text(size: 8.5pt, weight: 400, fill: white.transparentize(15%), tracking: 0.02em)[Dipartimento di Psicologia Generale, Università di Padova]
    #v(16pt)
    #text(size: 44pt, weight: 800, tracking: -0.01em)[FAIR in pratica]
    #v(4pt)
    #text(size: 14pt, weight: 400)[Manuale operativo per chi deve condividere dati, codice e materiali, e non sa da dove cominciare.]
    #v(16pt)
    #line(length: 26pt, stroke: 1.5pt + white)
    #v(2pt)
    #text(size: 14pt, weight: 600)[Margherita Calderan]
    #v(18pt)
    #line(length: 100%, stroke: 0.5pt + white.transparentize(55%))
    #v(6pt)
    #grid(columns: (1fr, 1.15fr), column-gutter: 18pt, align: top,
      [
        #text(size: 7.5pt, weight: 700, fill: white.transparentize(30%), tracking: 0.08em)[UN'INIZIATIVA DELLA]
        #v(-3pt)
        #text(size: 11pt, weight: 700)[Sottocommissione Open Science]
        #v(-5pt)
        #set text(size: 9pt)
        della Commissione Terza Missione \
        Dipartimento di Psicologia Generale \
        Università di Padova
      ],
      [
        #set text(size: 7.8pt, fill: white.transparentize(15%))
        #set par(leading: 0.5em)
        #grid(columns: (auto, 1fr), column-gutter: 9pt, row-gutter: 5.5pt, align: top,
          text(weight: 700)[Origine], [Dispensa del seminario _Hands-on Open Science: alternative a OSF e strumenti per la gestione FAIR dei dati_ (23 settembre 2026)],
          text(weight: 700)[Online], link("https://mar-cald.github.io/fair/")[mar-cald.github.io/fair],
          text(weight: 700)[Licenza], [Testi CC BY 4.0],
          text(weight: 700)[Aggiornato], [Settembre 2026],
        )
      ],
    )
  ]
  #block(inset: (x: 19mm, top: 13mm))[
    #text(size: 14pt, weight: 700)[Il minimo indispensabile, in sei mosse]
    #v(8pt)
    #set text(size: 11pt)
    #steps(gutter: 10pt,
      ([Dati in CSV, non (solo) in Excel.], [Un formato che si apre con qualunque programma, oggi e fra vent'anni.]),
      ([Un README e un data dictionary.], [Cosa c'è nella cartella, e cosa significa ogni colonna.]),
      ([Una licenza per ciascuna cosa.], [Dati CC0, codice MIT o GPL-3.0, materiali CC BY 4.0.]),
      ([Deposito su Zenodo.], [Un archivio vero, con un DOI permanente. Non Drive, non il sito del lab, non GitHub.]),
      ([Il DOI nell'articolo.], [Nella sezione _Data availability_, al posto di "disponibili su richiesta".]),
      ([Se avete un grant ERC o Horizon Europe: il DMP.], [Da consegnare entro la fine del sesto mese di progetto.]),
    )
    #v(20pt)
    #text(size: 8pt, weight: 700, fill: muted, tracking: 0.08em)[IN QUESTO MANUALE]
    #v(-2pt)
    #line(length: 100%, stroke: 0.5pt + rule)
    #v(2pt)
    #set text(size: 9.5pt)
    #grid(columns: (1fr, 1fr), column-gutter: 16pt, row-gutter: 7pt,
      [#text(fill: acc, weight: 700)[1] #h(4pt) Perché non è più facoltativo],
      [#text(fill: acc, weight: 700)[5] #h(4pt) Licenze: le tre che servono],
      [#text(fill: acc, weight: 700)[2] #h(4pt) FAIR, cosa fare davvero],
      [#text(fill: acc, weight: 700)[6] #h(4pt) Depositare su Zenodo, passo per passo],
      [#text(fill: acc, weight: 700)[3] #h(4pt) Il Data Management Plan],
      [#text(fill: acc, weight: 700)[7] #h(4pt) Dati sensibili],
      [#text(fill: acc, weight: 700)[4] #h(4pt) Preparare la cartella],
      [#text(fill: acc, weight: 700)[8] #h(4pt) Checklist finale e link],
    )
  ]
]

// ===========================================================================
// 1. PERCHÉ
// ===========================================================================
= Perché non è più facoltativo

#lead[Condividere i dati in modo FAIR non è più una buona pratica per volenterosi: è una condizione scritta nei bandi che finanziano la vostra ricerca.]

#grid(columns: (1fr, 1fr), column-gutter: 12pt,
  callout(title: [ERC e Horizon Europe])[
    - *DMP obbligatorio*, da consegnare entro la *fine del mese 6* del progetto (→ sezione 3).
    - *Accesso aperto ai dati*: _"as open as possible, as closed as necessary"_.
    - Deposito in un *repository affidabile*, con metadati aperti e conformi ai principi FAIR.
    - Licenza dei dati: *CC BY o CC0*. Nient'altro. Una licenza "non commerciale" non è ammessa.
    #v(2pt)
    #text(size: 8pt, fill: muted)[Fonte: #link("https://erc.europa.eu/manage-your-project/open-science")[erc.europa.eu › Open Science]]
  ],
  callout(title: [PRIN 2026 (MUR)])[
    Dalle linee guida di valutazione, §5.2 _Open Science_:

    #pad(left: 6pt)[_"La gestione dei dati di ricerca deve essere responsabile e conforme ai principi FAIR."_]

    - Accesso aperto ai dati, stesso principio _"as open as possible, as closed as necessary"_.
    - Depositare la pubblicazione _"insieme ai dati necessari per validare i risultati"_.
    #v(2pt)
    #text(size: 8pt, fill: muted)[Fonte: #link("https://www.mur.gov.it/sites/default/files/2026-04/D.D.%202298%20All.%203%20Linee%20Guida%20di%20valutazione.pdf")[MUR, D.D. 2298, All. 3]]
  ],
)

#v(4pt)
In Italia la linea è la stessa anche fuori dai singoli bandi: il #link("https://www.mur.gov.it/sites/default/files/2022-06/Piano_Nazionale_per_la_Scienza_Aperta.pdf")[Piano Nazionale per la Scienza Aperta 2021-2027] del MUR indica la gestione FAIR come _"standard di riferimento"_ per la ricerca finanziata con fondi pubblici.

== Aperto non vuol dire FAIR

FAIR significa *Findable, Accessible, Interoperable, Reusable*: trovabile, accessibile, leggibile da altri programmi, riusabile. Il criterio pratico è uno solo:

#callout(fill: white, color: ink)[
  #text(size: 11pt, weight: 600)[Una persona che non vi conosce, e che non può scrivervi, riesce a trovare i vostri dati, aprirli, capirli e sapere se può riusarli?]
]

#v(2pt)
#table(columns: (1.05fr, 1.5fr),
  [Quello che si sente dire], [Perché non basta],
  [_"Dati disponibili su richiesta all'autore."_], [Non è condivisione. Gli studi che lo hanno verificato trovano che la maggior parte delle richieste resta senza risposta. Per ERC e Horizon Europe non basta.],
  [_"Li ho messi su Drive / sul sito del lab / su GitHub."_], [Nessun DOI, nessuna garanzia di conservazione: un link che si rompe al primo cambio di account o di sito.],
  [_"Ho caricato l'Excel su OSF."_], [Aperto sì, FAIR no: senza descrizione delle colonne e senza licenza, nessuno può usarlo (né legalmente, né in pratica).],
  [_"FAIR vuol dire tutto pubblico."_], [No. Dati sensibili possono essere FAIR con *accesso ristretto*: la scheda è pubblica, i file si ottengono su richiesta (→ sezione 7).],
)

#v(6pt)
#callout(title: [E OSF?], fill: grey, color: muted)[
  Il Center for Open Science ha annunciato la dismissione di OSF _Projects_: dal *16 novembre 2026* non si creano nuovi progetti, dal *19 febbraio 2027* tutti i progetti diventano di *sola lettura*, e in futuro i progetti privati saranno rimossi. OSF _Registrations_ (preregistrazioni) e PsyArXiv restano attivi. Per i dati, la strada è un repository come Zenodo.
]

// ===========================================================================
// 2. FAIR IN PRATICA
// ===========================================================================
#pagebreak()
= FAIR, cosa fare davvero

#lead[Metà del lavoro FAIR la fa il repository, automaticamente. L'altra metà è vostra, e nessuno la fa al posto vostro.]

#table(columns: (auto, 1fr, 1.25fr),
  [], [Lo fa il repository], [Lo fate voi],
  [#text(size: 17pt, weight: 800, fill: acc)[F] \ #text(size: 7.5pt, weight: 700)[FINDABLE]],
  [Assegna un *DOI* permanente e rende i metadati visibili ai motori di ricerca e ai cataloghi.],
  [Compilate metadati *ricchi*: titolo che dice cosa c'è, autori con *ORCID*, descrizione, parole chiave (per es. "Stroop", "cognitive control").],

  [#text(size: 17pt, weight: 800, fill: acc)[A] \ #text(size: 7.5pt, weight: 700)[ACCESSIBLE]],
  [Dal DOI si scaricano i file con un browser, senza account né abbonamenti. Il DOI funziona per sempre, anche se il deposito viene ritirato.],
  [Scegliete il *livello di accesso*: aperto, oppure ristretto con una procedura di richiesta pubblica.],

  [#text(size: 17pt, weight: 800, fill: acc)[I] \ #text(size: 7.5pt, weight: 700)[INTEROPERABLE]],
  [—],
  [Salvate in *formati aperti* (CSV, TXT, JSON), usate nomi di colonna espliciti e sempre gli stessi, collegate dati, codice, articolo e preregistrazione tramite i loro DOI.],

  [#text(size: 17pt, weight: 800, fill: acc)[R] \ #text(size: 7.5pt, weight: 700)[REUSABLE]],
  [—],
  [Scrivete un *README* e un *data dictionary*, dichiarate una *licenza*, dite come e quando sono stati raccolti i dati.],
)

#v(4pt)
Le ultime due righe della colonna di destra sono quelle che mancano quasi sempre, e sono le sezioni 4 e 5 di questo manuale.

== Quanto siete FAIR? Il test in sette domande

Prendete l'ultimo lavoro che avete pubblicato. Ogni "no" è una cosa da sistemare nel prossimo.

#let check(body) = grid(columns: (14pt, 1fr), column-gutter: 4pt,
  box(width: 9pt, height: 9pt, stroke: 0.9pt + acc, radius: 1.5pt, baseline: 1pt), body)
#block(inset: (left: 2pt))[
  #set par(spacing: 0.75em)
  #check[Esiste un DOI per i dati, non solo per l'articolo?]
  #check[Una persona esterna può scaricare dati, materiali e script, senza scrivervi?]
  #check[I file sono in formati aperti (CSV, TXT), non solo `.xlsx` o `.sav`?]
  #check[Ogni colonna di ogni file è spiegata da qualche parte: significato, unità, codifica?]
  #check[C'è una licenza esplicita? E distinta per dati, codice e materiali?]
  #check[Si capisce quale script produce quali risultati, e in che ordine si eseguono?]
  #check[Dati, codice, preregistrazione e articolo si citano a vicenda?]
]

#v(8pt)
#callout(title: [Da ricordare])[
  *Una licenza mancante equivale a "tutti i diritti riservati".* Dati pubblici ma senza licenza, legalmente, non si possono riusare.
  #v(2pt)
  *Un file che si apre solo con un programma a pagamento è già un ostacolo.* CSV sempre, eventualmente accanto all'originale.
]

// ===========================================================================
// 3. DMP
// ===========================================================================
#pagebreak()
= Il Data Management Plan

#lead[Il DMP è un documento di poche pagine che dice, all'inizio del progetto, cosa farete dei dati. Non è un esercizio burocratico: è la lista delle decisioni che altrimenti prenderete di fretta il giorno prima di pubblicare.]

#grid(columns: (1.1fr, 1fr), column-gutter: 14pt,
  [
    == Cosa ci si scrive

    Le risposte a sei domande, niente di più:

    #steps(
      ([Quali dati?], [Tipo, formato, volume approssimativo. Riusate dati esistenti?]),
      ([Come li documentate?], [README, data dictionary, standard (per es. BIDS per il neuroimaging).]),
      ([Dove li conservate?], [Durante il progetto (server di ateneo) e dopo (Zenodo o altro repository).]),
      ([Chi può accedervi, e con che licenza?], [Aperti, ristretti o chiusi, e perché. Licenza CC0 o CC BY.]),
      ([Etica e privacy?], [Consenso informato, pseudonimizzazione, anonimizzazione, GDPR.]),
      ([Chi se ne occupa, e con che costi?], [Persone responsabili e risorse (tempo, spazio, eventuali costi di deposito).]),
    )
  ],
  [
    == Quando

    #callout(title: [ERC e Horizon Europe])[
      Il DMP si consegna come deliverable *entro la fine del mese 6* di progetto e si aggiorna quando le cose cambiano. Gli scostamenti dal piano vanno motivati, non nascosti.
    ]
    #v(4pt)
    #callout(title: [Tutti gli altri], fill: grey, color: muted)[
      Anche quando non è richiesto, scriverlo prima di raccogliere i dati costa un'ora e risparmia giorni. Molte scelte (per es. cosa scrivere nel consenso informato) non si possono più correggere dopo.
    ]

    == Da dove partire

    - #link("https://biblio.unipd.it/biblioteca-digitale/per-chi-pubblica/documenti-e-materiali/unipd_dmp-guidelines_18-09-2024_v4-3.pdf")[*Template Horizon Europe annotato da Unipd*]: spiegazioni ed esempi per ogni domanda. Il punto di partenza consigliato.
    - #link("https://argos.openaire.eu/")[Argos] (OpenAIRE), #link("https://dmponline.dcc.ac.uk/")[DMPonline]: compilazione guidata online.
    - #link("https://dmponline.rivm.nl/template_export/5992485.pdf")[Template ufficiale Horizon Europe].
  ],
)

== Il calendario di un progetto FAIR

#let phase(when, what) = [
  #text(size: 7.5pt, weight: 700, fill: acc, tracking: 0.05em, upper(when))
  #v(-3pt)
  #set text(size: 8.7pt)
  #what
]
#grid(columns: (1fr, 1fr, 1fr, 1fr), column-gutter: 6pt, fill: tint, inset: (x: 8pt, y: 7pt),
  phase[Inizio][DMP. Nel consenso informato prevedete la condivisione dei dati anonimizzati. Preregistrazione.],
  phase[Durante][Cartella ordinata (sezione 4), README e data dictionary aggiornati man mano, non alla fine.],
  phase[Invio dell'articolo][Bozza su Zenodo, link privato per i revisori (sezione 6). DOI già riservato nel manoscritto.],
  phase[Pubblicazione][_Publish_ su Zenodo. DOI nella sezione _Data availability_. Collegamento fra deposito e articolo.],
)

// ===========================================================================
// 4. PREPARARE LA CARTELLA
// ===========================================================================
#pagebreak()
= Preparare la cartella

== CSV o Excel? CSV.

#grid(columns: (1fr, 1fr), column-gutter: 14pt,
  [
    Un file *`.xlsx`* è un formato di Excel: per leggerlo serve un programma che lo capisca, e dentro può nascondere fogli multipli, formule, celle unite, colori.

    Un file *`.csv`* è una tabella in *testo semplice*: ogni riga del file è una riga della tabella, con le colonne separate da virgole (o punti e virgola). Si apre con qualunque programma (Excel, R, SPSS, Python, il Blocco note) e si leggerà anche fra trent'anni.

    Lo stesso vale per `.sav` (SPSS), `.mat` (MATLAB), `.docx`: tenete l'originale, se volete, ma depositate *anche* la versione aperta.
  ],
  [
    #callout(title: [Come si fa])[
      *Excel:* File → Salva con nome → _CSV UTF-8 (delimitato da virgole)_. *Un foglio = un file CSV.*

      *SPSS:* File → Esporta → CSV.

      *R:*
      #v(-4pt)
      ```r
      write.csv(dati, "dati.csv",
                row.names = FALSE)
      ```
    ]
    #v(3pt)
    #callout(title: [Tre trappole], fill: nobg)[
      - *Colori ed evidenziature spariscono.* Se un'informazione sta nel colore di una cella, mettetela in una colonna.
      - *Excel in italiano* salva con `;` come separatore e la virgola decimale. Va bene, ma scrivetelo nel README.
      - *Niente celle unite, niente righe di intestazione multiple*: una riga di nomi, poi solo dati.
    ]
  ],
)

== Nomi dei file

#grid(columns: (1fr, 1fr), column-gutter: 10pt,
  no[
    ```
    Dati definitivi (2).xlsx
    analisi finale NUOVA.R
    questionarioEtà.csv
    ```
  ],
  yes[
    ```
    gonogo_data.csv
    02_analysis_gonogo.R
    demographics.csv
    ```
  ],
)
- *Niente spazi, accenti o caratteri speciali*, né nei nomi dei file né nei nomi delle colonne: rompono script e link.
- *Numeri con lo zero davanti* (`01_`, `02_`): altrimenti `10_` viene prima di `2_`.
- *Il nome dice cosa contiene.* "definitivo", "finale", "nuovo" non dicono niente.

== La struttura

#grid(columns: (1.35fr, 1fr), column-gutter: 14pt,
  [
    ```
    progetto/
    ├── README.md            cosa c'è e come si usa
    ├── LICENSE              a quali condizioni
    ├── data/
    │   ├── raw/             grezzi: SOLA LETTURA
    │   ├── gonogo_data.csv
    │   └── gonogo_dictionary.csv
    ├── scripts/
    │   ├── 01_cleaning.R
    │   └── 02_analysis.R
    ├── materials/           stimoli, questionari propri
    ├── output/              figure e tabelle
    └── docs/                preregistrazione, preprint
    ```
  ],
  [
    #set text(size: 9pt)
    *Grezzi separati e intoccabili.* L'export originale dello strumento (PsychoPy, E-Prime, Qualtrics) sta in `data/raw/` e non si modifica mai: i dati puliti li producono gli script.

    #v(3pt)
    *Script numerati* nell'ordine in cui vanno eseguiti.

    #v(3pt)
    *Test commerciali o di terzi* (per es. WISC, STAI): non si depositano, si citano.

    #v(3pt)
    Per dati comportamentali ripetitivi esiste uno standard, #link("https://psychds-docs.readthedocs.io/")[Psych-DS]; per il neuroimaging #link("https://bids.neuroimaging.io/")[BIDS]. Utili, ma *dopo* README e data dictionary.
  ],
)

// ===========================================================================
// 4 (segue). README E DATA DICTIONARY
// ===========================================================================
#pagebreak()
== Il README

Un file di testo nella cartella principale (`README.md` o `README.txt`) che risponde alle domande che chiunque si fa *prima* di aprire qualsiasi altro file. Scritto in inglese, se il deposito è pubblico. Un esempio completo, da copiare e adattare:

#grid(columns: (1.3fr, 1fr), column-gutter: 14pt,
  [
    ```
    # Stroop and trait anxiety

    Stroop interference as a function of trait
    anxiety. 100 adults; colour-word Stroop task
    (PsychoPy) and STAI-Y questionnaire, collected
    in the lab in March 2026.
    Authors: N. Surname (ORCID 0000-0000-...)

    ## Contents
    - data/stroop_data.csv: one trial per row
    - data/stroop_dictionary.csv: its columns
    - data/raw/: original exports, read-only
    - scripts/01_preprocessing.R: cleans data
    - scripts/02_analysis.R: models and figures

    ## How to reproduce
    R >= 4.3. Run the scripts in numeric order.

    ## License
    Data CC0-1.0, code MIT, materials CC BY 4.0.
    STAI-Y is a third-party instrument: not
    included, cite it.

    ## How to cite / Links
    Dataset: https://doi.org/10.5281/zenodo.XXXXXXX
    Article: https://doi.org/10.xxxx/xxxxx
    Preregistration: https://doi.org/...
    ```
  ],
  [
    #table(columns: (auto, 1fr),
      [Sezione], [Risponde a],
      [Titolo, autori], [Di chi è, a chi scrivo],
      [Descrizione], [Che studio è, quando e come sono stati raccolti i dati],
      [Contenuto], [Cosa c'è, file per file],
      [Riproduzione], [In che ordine girano gli script, con che software],
      [Licenza], [Cosa posso farne, e cosa vale per cosa],
      [Citazione e link], [DOI del dataset, dell'articolo, della preregistrazione],
    )
    #v(4pt)
    #callout(title: [Regola pratica])[
      Se un collega del vostro gruppo, che non ha lavorato allo studio, non riesce a rifare le analisi con il solo README, il README non basta.
    ]
  ],
)

== Il data dictionary

Il README descrive il progetto; il *data dictionary* (o _codebook_) descrive *ogni singola colonna* dei dati. È anch'esso un CSV, con una riga per variabile, accanto al file che descrive (`stroop_data.csv` → `stroop_dictionary.csv`).

#table(columns: (auto, 1.6fr, auto, auto, 1fr, auto),
  [variable_name], [label], [type], [unit], [allowed_values], [missing],
  [`participant`], [participant code], [string], [], [p01–p100], [],
  [`block`], [block number], [integer], [], [1–4], [],
  [`congruent`], [congruent trial (word = colour)], [boolean], [], [TRUE / FALSE], [],
  [`rt_ms`], [reaction time], [integer], [ms], [200–2000], [empty cell],
  [`group`], [experimental group], [categorical], [], [1 = control; 2 = training], [NA],
)
#v(2pt)
#text(size: 8.8pt, fill: muted)[Colonne utili da aggiungere quando servono: `source` (strumento o questionario da cui viene il dato) e `notes` (decisioni prese, anomalie). Il nome in `variable_name` deve essere *identico*, carattere per carattere, a quello nel file di dati.]

// ===========================================================================
// 5. LICENZE
// ===========================================================================
#pagebreak()
= Licenze: le tre che servono

#lead[Una licenza d'uso è la frase che dice agli altri cosa possono fare con il vostro lavoro. Se non c'è, valgono tutti i diritti riservati: nessuno può riusare legalmente nulla, anche se il file è pubblico e scaricabile.]

Dati, codice e testi sono oggetti diversi per la legge e hanno licenze diverse. L'errore più comune è metterne una sola per tutto. Ecco cosa scegliere:

#let lic(what, name, alt, why) = (
  [#text(weight: 700, size: 10pt, what)],
  [#text(weight: 800, size: 12pt, fill: acc, name)],
  [#why #if alt != none [#v(-2pt) #text(size: 8.5pt, fill: muted)[#alt]]],
)
#table(columns: (auto, auto, 1fr), inset: (x: 6pt, y: 7pt),
  [Cosa], [Licenza], [In pratica],
  ..lic([Dati], [CC0 1.0], [Alternativa: CC BY 4.0, se volete l'obbligo formale di attribuzione.],
    [Chiunque può riusarli, senza condizioni. È la scelta raccomandata dalla maggior parte dei repository (Dryad la impone).]),
  ..lic([Codice], [MIT], [Alternativa: GPL-3.0, se volete che anche le versioni modificate restino aperte (obbligatoria se riusate codice già GPL).],
    [Chiunque può usare e modificare il codice, mantenendo l'avviso di copyright. Nessuna garanzia da parte vostra.]),
  ..lic([Materiali propri], [CC BY 4.0], none,
    [Stimoli, questionari costruiti da voi, protocolli, figure, testi: riuso libero, citando la fonte.]),
  ..lic([Materiali di terzi], [nessuna], none,
    [Test commerciali, questionari altrui, immagini di cui non avete i diritti: *non si depositano, si citano*.]),
)

#v(4pt)
#grid(columns: (1fr, 1fr), column-gutter: 12pt,
  callout(title: [Ma con CC0 nessuno mi cita?])[
    La citazione è una norma scientifica, non un obbligo di legge: vi citeranno comunque, se il dataset ha un DOI e il README dice come farlo. E sui dati (fatti, misure) l'obbligo di attribuzione di CC BY è comunque giuridicamente debole.
  ],
  callout(title: [Evitate "NC", non commerciale], fill: nobg)[
    CC BY-NC sembra prudente ma blocca usi legittimi (un corso a pagamento, un editore, una fondazione) e *non è ammessa da Horizon Europe e ERC* per i dati, che richiedono CC BY o CC0.
  ],
)

== Come si applica, in pratica

#steps(
  ([Nel repository.], [Al momento del deposito si compila il campo _License_ (su Zenodo è obbligatorio e si possono indicarne più d'una).]),
  ([Un file `LICENSE`.], [Nella cartella principale, con il testo delle licenze scelte (si copia da #link("https://choosealicense.com/")[choosealicense.com] e #link("https://creativecommons.org/")[creativecommons.org]).]),
  ([Una sezione nel README], [che dica a parole cosa vale per cosa. Da incollare e adattare:]),
)
#v(2pt)
```
## License
- Data (data/): CC0 1.0 Universal (CC0-1.0)
- Code (scripts/): MIT
- Own materials (materials/): CC BY 4.0
- Third-party instruments: not redistributed; see their original sources

If you use this material, please cite:
Surname, N. (2026). Title of the dataset (Version 1.0) [Data set]. Zenodo.
https://doi.org/10.5281/zenodo.XXXXXXX
```

// ===========================================================================
// 6. ZENODO
// ===========================================================================
#pagebreak()
= Depositare su Zenodo

#lead[#link("https://zenodo.org/")[Zenodo] è la scelta predefinita: gestito dal CERN con fondi europei, gratuito, fino a *50 GB* e 100 file per deposito, DOI immediato, versioni, accesso aperto, ristretto o sotto embargo.]

#v(-6pt)
#text(size: 9pt)[*Alternative da conoscere:* #link("https://researchdata.cab.unipd.it/")[Research Data Unipd], il repository di ateneo, con il supporto dei bibliotecari; #link("https://openneuro.org/")[OpenNeuro] per il neuroimaging (in formato BIDS). Per un repository disciplinare: #link("https://www.re3data.org/")[re3data.org].]

== Passo per passo

#text(size: 9pt, fill: muted)[*Prima di cominciare*: cartella pronta (sezione 4). Se volete conservarne la struttura, caricatela come un unico `.zip`: aprite lo zip e controllate che non contenga file nascosti (`.DS_Store`, `__MACOSX`, `.Rhistory`) né file con dati personali.]
#v(4pt)

#steps(
  ([Accedete.], [Su zenodo.org, _Log in_ con il vostro *ORCID* (così il deposito è già associato a voi). Poi _New upload_.]),
  ([Caricate i file.], [Trascinate lo zip o i singoli file.]),
  ([DOI.], [Alla domanda _"Do you already have a DOI?"_ rispondete *No*. Con _Get a DOI now!_ il DOI viene riservato subito: potete scriverlo nel manoscritto prima di pubblicare.]),
  ([_Resource type_.], [*Dataset* se il contributo principale sono i dati (anche se ci sono gli script di analisi). *Software* se il codice è un prodotto a sé: in quel caso fate due depositi e collegateli (passo 7).]),
  ([Descrizione.], [Titolo che dice cosa c'è; _Creators_ con ORCID e affiliazione; _Description_ (riusate l'inizio del README); _Keywords_. Più è descritto, più è trovabile.]),
  ([Licenza e copyright.], [_License_ è impostata di default su *CC BY 4.0*: per i dati cambiatela in *CC0*, e aggiungete MIT per il codice. _Copyright_: "© 2026 Nome Cognome" (o l'ente, se i diritti sono suoi).]),
  ([Collegamenti e finanziamenti.], [_Related works_: il DOI dell'articolo (_is supplement to_), della preregistrazione, del codice. _Funding_: il vostro grant (i progetti ERC e Horizon Europe si cercano per numero o acronimo; per un PRIN indicate MUR e codice del progetto).]),
  ([Accesso.], [*Public* per i dati aperti. *Restricted* per i file sensibili: scheda e DOI pubblici, file solo a chi approvate voi (sezione 7). *Embargo* se i file devono aprirsi solo a una data precisa.]),
  ([Pubblicate.], [_Save draft_, _Preview_, poi *Publish*. Da quel momento il DOI è attivo e i file non si possono più cambiare liberamente (vedi sotto).]),
)

#v(6pt)
#grid(columns: (1fr, 1fr), column-gutter: 12pt,
  callout(title: [Bozza per i revisori della rivista])[
    Salvate la bozza, poi _Share_ → _Links_ → permesso *Can preview draft* (non _Can view_, che funziona solo sui record pubblicati). Il link si apre senza account.

    #text(size: 8.8pt)[*Revisione in doppio cieco?* L'anteprima mostra gli autori: sostituiteli con "anonymous" e togliete i vostri nomi da README, script e percorsi (`/Users/nome/...`). Rimetteteli prima di pubblicare.]
  ],
  callout(title: [Correzioni e nuove versioni])[
    - *Entro 30 giorni* dalla pubblicazione: potete sostituire i file da soli, stesso DOI.
    - *Dopo*: si pubblica una *nuova versione* (_New version_), che ha un DOI proprio. Un _concept DOI_ rimanda sempre all'ultima versione.
    - *Metadati* (titolo, autori, descrizione, licenza): si correggono sempre, con _Edit_.
  ],
)

#v(6pt)
#grid(columns: (1fr, 1fr), column-gutter: 12pt,
  minibox[Il codice sta su GitHub?][
    *GitHub non è un archivio*: si cancella in un attimo e non ha DOI. Ma Zenodo lo archivia da solo: Profilo → _GitHub_ → collegate l'account → _Sync_ → attivate il repository (deve essere pubblico). Ogni *release* creata su GitHub (per es. `v1.0.0`) viene archiviata con un DOI.
  ],
  minibox[Un'alternativa: PsychArchives][
    #link("https://www.psycharchives.org/")[PsychArchives] (ZPID) è il repository disciplinare della psicologia: gratuito, ma con 1 GB per oggetto e un controllo formale dello staff prima della pubblicazione. Offre una licenza "solo uso scientifico". Dettagli nella #link("https://mar-cald.github.io/fair/psycharchives.html")[dispensa online].
  ],
)

// ===========================================================================
// 7. DATI SENSIBILI
// ===========================================================================
#pagebreak()
= Dati sensibili

#lead[_"As open as possible, as closed as necessary."_ Dati che non si possono rendere pubblici non esonerano dal FAIR: cambiano solo il modo di condividerli.]

#grid(columns: (1fr, 1fr), column-gutter: 12pt,
  no(title: "Non è anonimo")[
    - Sostituire i nomi con codici, tenendo altrove la chiave di collegamento: è *pseudonimizzazione*, e per il GDPR sono ancora dati personali.
    - Date di nascita complete, codici postali, combinazioni rare (età + professione + paese) che identificano una persona.
  ],
  yes(title: "Le strade praticabili")[
    + *Accesso ristretto*: metadati e DOI pubblici, file su richiesta approvata (su Zenodo: _Restricted_, con le condizioni scritte nella scheda).
    + *Dataset derivato*: dati aggregati o statistiche sufficienti a riprodurre le analisi.
    + *Dati sintetici* che imitano la struttura di quelli reali, per far girare il codice.
  ],
)
#v(4pt)
#callout(title: [Per i prossimi studi])[
  Nel *consenso informato* prevedete esplicitamente la condivisione dei dati anonimizzati in un archivio pubblico. Se il consenso non lo dice, dopo non si può fare.
]

// ===========================================================================
// 8. CHECKLIST
// ===========================================================================
= Checklist finale e link

#grid(columns: (1fr, 1fr), column-gutter: 16pt,
  [
    === Contenuto
    #set par(spacing: 0.6em)
    #check[README chiaro nella cartella principale]
    #check[Data dictionary per tutte le colonne di tutti i file]
    #check[Dati in CSV (anche se tenete l'originale)]
    #check[Il codice gira su un altro computer, da una cartella pulita]
    === Diritti e riservatezza
    #check[Licenza nel repository, nel file `LICENSE` e nel README]
    #check[Niente materiali di terzi che non potete ridistribuire]
    #check[Nessuna informazione che identifica una persona]
    #check[I coautori sono d'accordo con il deposito]
    === Collegamenti
    #check[Tutti gli autori con ORCID]
    #check[Deposito collegato ad articolo, preregistrazione, codice]
    #check[DOI del deposito nella _Data availability_ dell'articolo]
  ],
  [
    === Data availability statement, da copiare
    #block(fill: grey, inset: 9pt, radius: 3pt, width: 100%)[
      #set text(size: 8.8pt)
      Data, analysis code, and materials are openly available on Zenodo at https://doi.org/10.5281/zenodo.XXXXXXX (data: CC0 1.0; code: MIT; materials: CC BY 4.0).
    ]
    #text(size: 8.5pt, fill: muted)[Se i dati sono ad accesso ristretto: _"Data are available on Zenodo under restricted access at [DOI]; access is granted upon request for scientific purposes."_]

    === Link utili
    #set text(size: 8.8pt)
    #set par(spacing: 0.55em)
    #link("https://zenodo.org/")[*Zenodo*] · #link("https://researchdata.cab.unipd.it/")[Research Data Unipd] · #link("https://www.re3data.org/")[re3data.org]

    #link("https://biblio.unipd.it/biblioteca-digitale/per-chi-pubblica/documenti-e-materiali/unipd_dmp-guidelines_18-09-2024_v4-3.pdf")[*DMP: template annotato Unipd*] · #link("https://argos.openaire.eu/")[Argos] · #link("https://dmponline.dcc.ac.uk/")[DMPonline]

    #link("https://chooser-beta.creativecommons.org/")[*Scegliere una licenza CC*] · #link("https://choosealicense.com/")[choosealicense.com] (codice)

    #link("https://erc.europa.eu/manage-your-project/open-science")[ERC: Open Science] · #link("https://www.openaire.eu/how-to-comply-with-horizon-europe-mandate-for-rdm")[OpenAIRE: Horizon Europe]

    #link("https://psychds-docs.readthedocs.io/")[Psych-DS] · #link("https://bids.neuroimaging.io/")[BIDS] · #link("https://www.cos.io/osf-changes")[OSF: cosa cambia]

    #link("https://www.fairsfair.eu/fair-aware")[FAIR-Aware]: autovalutazione in 10 minuti

    #link("https://doi.org/10.1038/sdata.2016.18")[Wilkinson et al. (2016)]: i principi FAIR originali
  ],
)

#v(1fr)
#line(length: 100%, stroke: 0.5pt + rule)
#text(size: 8.5pt, fill: muted)[
  *Tutto il resto*, con esempi scaricabili (un progetto modello completo, Psych-DS, PsychArchives, confronto fra repository, glossario): #link("https://mar-cald.github.io/fair/")[*mar-cald.github.io/fair*]. \
  Booklet tratto dalla dispensa di Margherita Calderan, Dipartimento di Psicologia Generale, Università di Padova. Testi CC BY 4.0.
]
