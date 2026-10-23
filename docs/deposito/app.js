// "Prepara il deposito": controlla una cartella di progetto e costruisce la
// versione da depositare, tutto nel browser.
//
// I controlli e la costruzione del deposito sono gli script Python della skill
// fair-check (skill/fair-check/scripts/), eseguiti con Pyodide; deposito/bridge.py
// li collega a questa pagina. Qui ci sono solo la lettura della cartella,
// l'interfaccia e la traduzione in italiano dei messaggi del controllo.

(function () {
  "use strict";

  const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/";
  const PY_FILES = ["fair_scan.py", "draft_dictionary.py", "build_deposit.py", "make_psychds.py"];
  const LICENSES = ["CC0-1.0.txt", "GPL-3.0.txt", "CC-BY-4.0.txt"];
  const SKIP_DIRS = new Set([".git", ".Rproj.user", "node_modules", "__pycache__", ".ipynb_checkpoints", ".venv", "venv", ".quarto"]);
  const SITE = "https://mar-cald.github.io/fair/";
  const DEST_LABEL = {
    "data": "data/ (dati)", "data/raw": "data/raw/ (export originali)", "scripts": "scripts/ (codice)",
    "output/figures": "output/figures/", "output/tables": "output/tables/", "materials": "materials/ (materiali propri)",
    "docs": "docs/ (preprint, documenti)", ".": "cartella principale", "exclude": "lasciare fuori",
  };
  const DICT_COLS = ["label", "type", "unit", "allowed_values", "coding", "missing_values", "source", "notes"];

  let py = null;
  let state = null; // {root, project, report, proposal, drafts}

  const $ = (sel, el) => (el || document).querySelector(sel);
  const esc = (s) => String(s == null ? "" : s)
    .replace(/\((\d+) files with the same columns\)/g, "($1 file con le stesse colonne)")
    .replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const tick = () => new Promise((r) => setTimeout(r, 30));

  function status(msg, kind) {
    const el = $("#fa-status");
    el.textContent = msg || "";
    el.className = "fa-status" + (kind ? " fa-" + kind : "");
  }

  // ------------------------------------------------------------------ Python

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = src;
      s.onload = resolve;
      s.onerror = () => reject(new Error("Impossibile scaricare " + src));
      document.head.appendChild(s);
    });
  }

  async function getPython() {
    if (py) return py;
    status("Preparo Python nel browser (circa 10 MB la prima volta, poi resta in memoria nel browser)…");
    await loadScript(PYODIDE + "pyodide.js");
    py = await window.loadPyodide({ indexURL: PYODIDE });
    py.FS.mkdirTree("/fair/licenses");
    for (const f of PY_FILES) py.FS.writeFile("/fair/" + f, await fetchText("skill/fair-check/scripts/" + f));
    py.FS.writeFile("/fair/bridge.py", await fetchText("deposito/bridge.py"));
    for (const f of LICENSES) py.FS.writeFile("/fair/licenses/" + f, await fetchText("skill/fair-check/assets/licenses/" + f));
    py.runPython("import sys; sys.path.insert(0, '/fair'); import bridge");
    return py;
  }

  async function fetchText(url) {
    const r = await fetch(url);
    if (!r.ok) throw new Error("Impossibile scaricare " + url);
    return await r.text();
  }

  function callPy(fn, ...args) {
    args.forEach((a, i) => py.globals.set("_arg" + i, a));
    const call = `bridge.${fn}(${args.map((_, i) => "_arg" + i).join(", ")})`;
    return JSON.parse(py.runPython(call));
  }

  // ---------------------------------------------------------- reading folder

  function skipPath(parts) {
    return parts.some((p, i) => (i < parts.length - 1 && SKIP_DIRS.has(p)) || p.startsWith(".") || p.startsWith("~$"))
      || parts.join("/").includes("renv/library");
  }

  async function filesFromInput(fileList) {
    const out = [];
    for (const f of fileList) {
      const parts = (f.webkitRelativePath || f.name).split("/");
      if (!skipPath(parts)) out.push({ path: parts.join("/"), file: f });
    }
    return out;
  }

  async function filesFromDrop(items) {
    const out = [];
    const readAll = (reader) => new Promise((res, rej) => {
      const all = [];
      const next = () => reader.readEntries((batch) => (batch.length ? (all.push(...batch), next()) : res(all)), rej);
      next();
    });
    async function walk(entry, prefix) {
      const path = prefix ? prefix + "/" + entry.name : entry.name;
      if (skipPath(path.split("/"))) return;
      if (entry.isFile) {
        const file = await new Promise((res, rej) => entry.file(res, rej));
        out.push({ path, file });
      } else if (entry.isDirectory) {
        for (const e of await readAll(entry.createReader())) await walk(e, path);
      }
    }
    const entries = [...items].map((i) => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
    if (entries.length !== 1 || !entries[0].isDirectory) {
      throw new Error("Trascinate una sola cartella: quella del progetto.");
    }
    await walk(entries[0], "");
    return out;
  }

  // entries: [{path: "progetto/sub/file", bytes?: Uint8Array, file?: File}]
  async function loadEntries(entries) {
    if (!entries.length) throw new Error("La cartella è vuota.");
    const project = entries[0].path.split("/")[0];
    if (entries.some((e) => e.path.split("/")[0] !== project)) throw new Error("Scegliete una sola cartella.");
    const total = entries.reduce((s, e) => s + (e.bytes ? e.bytes.length : e.file.size), 0);
    if (total > 500e6) throw new Error(`La cartella pesa ${Math.round(total / 1e6)} MB: oltre 500 MB il browser non regge. Per dataset così grandi usate la skill fair-check con Claude Code.`);
    await getPython();
    status(`Leggo ${entries.length} file (${(total / 1e6).toFixed(1)} MB)…`);
    await tick();
    py.runPython("import shutil; shutil.rmtree('/work', ignore_errors=True)");
    for (const e of entries) {
      const bytes = e.bytes || new Uint8Array(await e.file.arrayBuffer());
      const full = "/work/" + e.path;
      py.FS.mkdirTree(full.slice(0, full.lastIndexOf("/")));
      py.FS.writeFile(full, bytes);
    }
    status("Controllo la cartella…");
    await tick();
    const root = "/work/" + project;
    const res = callPy("scan_json", root);
    state = { root, project, report: res.report, proposal: res.proposal, drafts: null };
    renderReport();
    renderForm();
    status(`Cartella "${project}": ${res.report.n_files} file controllati.`, "ok");
    $("#fa-report-section").hidden = false;
    $("#fa-deposit-section").hidden = false;
    $("#fa-result-section").hidden = true;
    $("#fa-report-section").scrollIntoView({ behavior: "smooth" });
  }

  // ------------------------------------------------- messages in Italian

  const FLAG = {
    "name": "nome", "e-mail": "e-mail", "phone number": "numero di telefono", "address": "indirizzo",
    "birth date": "data di nascita", "tax / national ID": "codice fiscale", "IP address": "indirizzo IP",
    "GPS coordinates": "coordinate GPS", "institutional ID": "matricola", "crowdsourcing worker ID": "ID della piattaforma di reclutamento",
  };
  const TR = [
    [/^1 exact duplicate rows$/, "1 riga duplicata"],
    [/^1 values with leading\/trailing spaces$/, "1 valore con spazi all'inizio o alla fine"],
    [/^'(.*)' should have one value per participant but has more for 1 of (\d+) participants \((.*)\)$/,
      "'$1' dovrebbe avere un solo valore per partecipante, ma ne ha più di uno per 1 partecipante su $2 ($3)"],
    [/^missing values coded in more than one way: (.*)$/, "valori mancanti scritti in più modi: $1"],
    [/^(\d+) values with leading\/trailing spaces$/, "$1 valori con spazi all'inizio o alla fine"],
    [/^column is entirely empty$/, "colonna completamente vuota"],
    [/^possible numeric missing-value codes: (.*)$/, "possibili codici numerici per i valori mancanti: $1"],
    [/^decimal comma inside a comma-delimited file$/, "virgola decimale in un file separato da virgole"],
    [/^mostly numeric but contains text: (.*)$/, "quasi tutta numerica, ma contiene testo: $1"],
    [/^dates written in more than one format: (.*)$/, "date scritte in più formati: $1"],
    [/^same category written differently: (.*)$/, "la stessa categoria scritta in modi diversi: $1"],
    [/^constant column \(one value only\)$/, "colonna costante (un solo valore)"],
    [/^(\d+) rows with a different number of fields than the header \(first lines: (.*)\)$/, "$1 righe con un numero di campi diverso dall'intestazione (righe $2)"],
    [/^column (\d+) has no name$/, "la colonna $1 non ha nome"],
    [/^duplicated column names: (.*)$/, "nomi di colonna ripetuti: $1"],
    [/^the first row looks like data, not column names \(no header\?\)$/, "la prima riga sembra contenere dati, non i nomi delle colonne"],
    [/^(\d+) exact duplicate rows$/, "$1 righe duplicate"],
    [/^'(.*)' should have one value per participant but has more for (\d+) of (\d+) participants \((.*)\)$/,
      "'$1' dovrebbe avere un solo valore per partecipante, ma ne ha più di uno per $2 partecipanti su $3 ($4)"],
    [/^column name suggests (.*)$/, (m, x) => "il nome della colonna fa pensare a: " + (FLAG[x] || x)],
    [/^values look like e-mail addresses$/, "i valori sembrano indirizzi e-mail"],
    [/^values look like Italian tax codes \(codice fiscale\)$/, "i valori sembrano codici fiscali"],
    [/^values look like phone numbers$/, "i valori sembrano numeri di telefono"],
    [/^(.*): no label$/, "$1: manca la descrizione (label)"],
    [/^(.*): categorical-looking column without coding$/, "$1: sembra categoriale ma manca la codifica (coding)"],
    [/^(.*): values in data not described in coding: (.*)$/, "$1: valori presenti nei dati ma non descritti in coding: $2"],
    [/^(.*): data range (.*) outside allowed_values (.*)$/, "$1: i valori vanno da $2, fuori da allowed_values ($3)"],
    [/^(.*): has (\d+) missing values but missing_values is empty$/, "$1: ha $2 valori mancanti ma missing_values è vuoto"],
    [/^data '(.*)' vs dictionary '(.*)' \(differ only in case\/spacing\)$/, "nei dati '$1', nel dictionary '$2' (cambiano solo maiuscole o spazi)"],
    [/^setwd\((.*)\) — ties the script to one computer$/, "setwd($1): lega lo script a un solo computer"],
    [/^absolute path '(.*)'$/, "percorso assoluto '$1': funziona solo sul computer dell'autore"],
    [/^rm\(list = ls\(\)\) — .*$/, "rm(list = ls()): non ripulisce davvero la sessione; meglio riavviare R"],
    [/^installs packages inside the script$/, "installa pacchetti dentro lo script"],
    [/^no dataset_description.json in the root$/, "manca dataset_description.json nella cartella principale"],
    [/^files in data\/ not named key-value_..._data.csv: (.*)$/, "file in data/ che non seguono lo schema chiave-valore_..._data.csv: $1"],
    [/^no data\/ folder in the root$/, "manca la cartella data/"],
    [/^columns not in variableMeasured: (.*)$/, "colonne non elencate in variableMeasured: $1"],
    [/^(.*) \(absolute path: rewrite it relative to the project root\)$/, "$1: percorso assoluto, va riscritto a partire dalla cartella del progetto"],
    [/^(.*) \(could not map (.*)\)$/, "$1: il file $2 non è stato trovato"],
    [/^semicolon-separated -> comma-separated$/, "da separato con punto e virgola a separato con virgole"],
    [/^tab-separated -> comma-separated$/, "da separato con tabulazioni a separato con virgole"],
    [/^decimal comma -> decimal point$/, "virgola decimale sostituita dal punto"],
    [/^columns removed: (.*)$/, "colonne tolte: $1"],
  ];
  const NAMEPROB = { "spaces": "spazi", "accented/non-ASCII letters": "lettere accentate", "looks like a duplicate copy": "sembra una copia duplicata", "starts with a digit": "inizia con un numero" };

  function tr(msg) {
    for (const [re, rep] of TR) if (re.test(msg)) return msg.replace(re, rep);
    return msg;
  }
  function trName(p) {
    if (NAMEPROB[p]) return NAMEPROB[p];
    let m = p.match(/^manual versioning word \((.*)\)$/);
    if (m) return `parola che indica una versione ("${m[1]}")`;
    m = p.match(/^special characters (.*)$/);
    if (m) return "caratteri speciali " + m[1];
    return p;
  }

  // -------------------------------------------------------------- report

  const ICON = { ok: "✅", warn: "⚠️", bad: "❌", info: "ℹ️" };

  function areas(r) {
    const A = [];
    // 1. data
    const di = [];
    for (const t of r.data) {
      const name = t.file || t.file_set;
      if (t.error) { di.push(`<code>${esc(name)}</code>: ${esc(t.error)}`); continue; }
      const its = [];
      (t.header_issues || []).forEach((x) => its.push(x.replace(/^'(.*)': (.*)$/, (m, c, ps) => `colonna '${c}': ${ps.split(", ").map(trName).join(", ")}`)));
      (t.issues || []).forEach((x) => its.push(tr(x)));
      (t.columns || []).forEach((c) => (c.issues || []).forEach((x) => its.push(`<code>${esc(c.name)}</code>: ${esc(tr(x))}`)));
      (t.within_participant_inconsistencies || []).forEach((x) => its.push(tr(x)));
      Object.entries(t.issues_by_file || {}).forEach(([f, xs]) => its.push(`<code>${esc(f)}</code>: ${xs.map(tr).map(esc).join("; ")}`));
      if (its.length) di.push(`<code>${esc(name)}</code>${t.n_rows != null ? ` (${t.n_rows} righe)` : ""}<ul>${its.map((x) => `<li>${x.startsWith("<code>") ? x : esc(x)}</li>`).join("")}</ul>`);
    }
    for (const x of r.cross_file_participants || []) {
      const its = [];
      if (x.only_in_first.length) its.push(`ID solo in <code>${esc(x.files[0])}</code>: ${esc(x.only_in_first.join(", "))}`);
      if (x.only_in_second.length) its.push(`ID solo in <code>${esc(x.files[1])}</code>: ${esc(x.only_in_second.join(", "))}`);
      if (x.note_names) its.push(`la colonna degli ID ha nomi diversi: <code>${esc(x.id_columns[0])}</code> e <code>${esc(x.id_columns[1])}</code>`);
      if (x.note_format) its.push("gli ID coincidono solo togliendo prefissi e zeri iniziali: scriveteli nello stesso modo in tutti i file");
      (x.values_disagree || []).forEach((v) => its.push(`<code>${esc(v.columns[0])}</code> / <code>${esc(v.columns[1])}</code> non coincidono per ${v.n_participants} partecipanti (${esc(v.examples.join("; "))})`));
      if (its.length) di.push(`Fra <code>${esc(x.files[0])}</code> e <code>${esc(x.files[1])}</code><ul>${its.map((i) => `<li>${i}</li>`).join("")}</ul>`);
    }
    Object.entries(r.cross_file_type_inconsistencies || {}).forEach(([c, xs]) => di.push(`<code>${esc(c)}</code> ha tipi diversi nei vari file: ${esc(xs.join("; "))}`));
    const nData = r.data.length;
    A.push({ title: "Dati e coerenza", link: "struttura-1.html#data-dictionary",
      status: !nData ? "info" : di.length ? "warn" : "ok",
      line: !nData ? "Nessun file CSV o TSV da controllare." : di.length ? `${di.reduce((n, x) => n + Math.max(1, (x.match(/<li>/g) || []).length), 0)} punti da controllare: decidete voi se sono errori.` : "Nessuna incoerenza trovata.",
      items: di });

    // 2. structure and names
    const si = [];
    r.naming.problems.forEach((p) => si.push(`<code>${esc(p.path)}</code>: ${esc(p.problems.map(trName).join(", "))}`));
    r.naming.numbering.forEach((n) => si.push(`in <code>${esc(n.folder)}</code> i numeri non hanno lo zero davanti (${esc(n.files.join(", "))}): meglio 01_, 02_…`));
    (r.structure.empty_dirs || []).forEach((d) => si.push(`cartella vuota: <code>${esc(d)}</code>`));
    A.push({ title: "Struttura e nomi", link: "struttura-1.html#regole-generali", status: si.length ? "warn" : "ok",
      line: si.length ? "Nomi da sistemare: nella versione da depositare i nomi vengono puliti." : "Nomi e cartelle in ordine.", items: si });

    // 3. formats
    const fi = [];
    let fmtBad = false;
    r.formats.proprietary_data.forEach((p) => {
      if (!p.open_copy_exists) fmtBad = true;
      fi.push(`<code>${esc(p.file)}</code> (${esc(p.format)}): ${p.open_copy_exists ? "c'è anche una versione CSV" : "nessuna copia in formato aperto"}`);
    });
    r.formats.proprietary_docs.forEach((p) => fi.push(`<code>${esc(p.file)}</code> (${esc(p.format)}): meglio PDF, Markdown o testo`));
    A.push({ title: "Formati", link: "struttura-1.html#in-che-formato-salvarli", status: fmtBad ? "bad" : fi.length ? "warn" : "ok",
      line: fmtBad ? "Ci sono dati solo in formato proprietario." : fi.length ? "Alcuni file sono in formati proprietari." : "Tutti i dati sono in formati aperti.", items: fi });

    // 4. README
    const SEC = { authors_orcid: "autori e ORCID", description: "di cosa si tratta", contents: "contenuto dei file", how_to_read: "come leggere i dati",
      how_to_reproduce: "come riprodurre", license: "licenza", citation: "come citare", related_materials: "materiali collegati", provenance: "quando e come sono stati raccolti i dati" };
    const ri = [];
    let rst = "bad", rline = "Manca il README.";
    if (r.readme) {
      const missing = Object.entries(SEC).filter(([k]) => !r.readme.sections[k]).map(([, v]) => v);
      if (missing.length) ri.push("sezioni mancanti: " + missing.join(", "));
      if (r.readme.files_not_mentioned.length) ri.push(`${r.readme.files_not_mentioned.length} file non sono nominati nel README`);
      rst = missing.length ? "warn" : "ok";
      rline = `<code>${esc(r.readme.file)}</code>, ${r.readme.n_words || 0} parole.`;
    }
    A.push({ title: "README", link: "struttura-1.html#readme", status: rst, line: rline, items: ri.map(esc) });

    // 5. dictionary
    const dIt = [];
    let dBad = false;
    r.dictionaries.coverage.forEach((c) => {
      if (!c.dictionary) { dBad = true; dIt.push(`<code>${esc(c.data)}</code>: nessun data dictionary`); return; }
      const its = [];
      if ((c.data_columns_not_in_dictionary || []).length) its.push("colonne non descritte: " + c.data_columns_not_in_dictionary.join(", "));
      (c.name_mismatches || []).forEach((x) => its.push(tr(x)));
      (c.entry_problems || []).forEach((x) => its.push(tr(x)));
      if (its.length) dIt.push(`<code>${esc(c.data)}</code> → <code>${esc(c.dictionary)}</code><ul>${its.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`);
    });
    r.dictionaries.dictionary_files.forEach((d) => { if (d.columns_missing && d.columns_missing.length) dIt.push(`<code>${esc(d.file)}</code>: mancano le colonne ${esc(d.columns_missing.join(", "))}`); });
    r.dictionaries.non_csv_dictionaries.forEach((d) => dIt.push(`<code>${esc(d)}</code>: dictionary non in CSV, non leggibile dai programmi`));
    A.push({ title: "Data dictionary", link: "struttura-1.html#data-dictionary", status: !nData ? "info" : dBad ? "bad" : dIt.length ? "warn" : "ok",
      line: !nData ? "Nessun file di dati." : dBad ? "Alcuni file di dati non hanno un data dictionary." : dIt.length ? "Data dictionary incompleti." : "Ogni file di dati ha un data dictionary completo.", items: dIt });

    // 6. license
    const li = [];
    const found = new Set();
    r.licenses.files.forEach((f) => {
      f.detected.forEach((x) => found.add(x));
      li.push(`<code>${esc(f.file)}</code>: ${f.detected.length ? esc(f.detected.join(", ")) : "licenza non riconosciuta"}${f.looks_like_full_text ? "" : " (senza il testo completo)"}`);
    });
    (r.licenses.readme_detected || []).forEach((x) => found.add(x));
    let lst = found.size ? "ok" : "bad";
    if ([...found].some((x) => /NC|ND/.test(x))) { lst = "warn"; li.push("licenza NC o ND: limita usi legittimi dei dati (vedi la pagina Licenze)"); }
    if (r.materials_present.code && r.materials_present.data && found.size === 1) { lst = "warn"; li.push("una sola licenza per dati e codice: servono licenze diverse"); }
    if (r.licenses.files.some((f) => !f.looks_like_full_text)) lst = lst === "ok" ? "warn" : lst;
    A.push({ title: "Licenza", link: "licenze.html", status: lst,
      line: found.size ? "Trovate: " + [...found].join(", ") + "." : "Nessuna licenza: senza licenza nessuno può riusare legalmente i materiali.", items: li });

    // 7. code
    if (r.materials_present.code) {
      const ci = [];
      r.code.files.forEach((c) => {
        const its = (c.issues || []).map(tr);
        if (c.referenced_files_not_found) its.push("legge file che non sono nella cartella: " + c.referenced_files_not_found.join(", "));
        if (its.length) ci.push(`<code>${esc(c.file)}</code><ul>${its.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>`);
      });
      if (r.code.all_packages.length) ci.push("pacchetti usati: " + esc(r.code.all_packages.join(", ")) + (r.code.environment["renv.lock"] ? "" : " (non dichiarati in un renv.lock o requirements.txt)"));
      A.push({ title: "Codice (letto, non eseguito)", link: "esempio.html", status: ci.length > 1 || r.code.files.some((c) => (c.issues || []).length || c.referenced_files_not_found) ? "warn" : "info",
        line: `${r.code.files.length} script. La pagina li legge ma non li esegue: dopo il download, eseguiteli sul vostro computer dalla cartella del deposito.`, items: ci });
    }

    // 8. personal data
    const pi = [];
    r.data.forEach((t) => (t.possible_personal_data || []).forEach((p) => pi.push(typeof p === "string"
      ? `<code>${esc(t.file_set)}</code>: colonna <code>${esc(p)}</code>`
      : `<code>${esc(t.file)}</code>, colonna <code>${esc(p.column)}</code>: ${esc(p.flags.map(tr).join("; "))}`)));
    A.push({ title: "Dati personali", link: "risorse.html#checklist-prima-di-depositare", status: pi.length ? "bad" : nData ? "ok" : "info",
      line: pi.length ? "Colonne che sembrano identificare le persone: vanno tolte dal deposito." : "Nessuna colonna riconosciuta come dato personale. Il controllo guarda nomi e formati delle colonne: verificate comunque.", items: pi });

    // 9. manuscript
    if (r.manuscripts.length) {
      A.push({ title: "Manoscritto", link: "risorse.html#checklist-prima-di-depositare", status: "info",
        line: "Trovato: " + r.manuscripts.map((m) => m.file).join(", ") + ". Il confronto fra i numeri del testo e l'output del codice non è disponibile in questa pagina (lo fa la skill fair-check con Claude). Depositate il preprint o l'accepted manuscript, non il PDF dell'editore.", items: [] });
    }
    return A;
  }

  function renderReport() {
    const A = areas(state.report);
    const r = state.report;
    const mats = ["dati", r.materials_present.code && "codice", r.materials_present.manuscript && "manoscritto"].filter(Boolean);
    let h = `<p>La cartella contiene: ${mats.join(", ")}. ${r.n_files} file, ${r.total_size_mb} MB.</p>`;
    h += `<table class="fa-summary"><thead><tr><th>Area</th><th></th><th>In una riga</th></tr></thead><tbody>`;
    A.forEach((a, i) => { h += `<tr><td><a href="#fa-area-${i}">${esc(a.title)}</a></td><td class="fa-icon">${ICON[a.status]}</td><td>${a.line}</td></tr>`; });
    h += `</tbody></table>`;
    A.forEach((a, i) => {
      h += `<details class="fa-area" id="fa-area-${i}"${a.items.length && a.status !== "ok" ? " open" : ""}><summary>${ICON[a.status]} ${esc(a.title)}</summary>`;
      h += `<p>${a.line} <a href="${a.link}" target="_blank">Le regole</a></p>`;
      if (a.items.length) h += `<ul>${a.items.map((x) => `<li>${x}</li>`).join("")}</ul>`;
      h += `</details>`;
    });
    $("#fa-report").innerHTML = h;
  }

  // ---------------------------------------------------------------- form

  function personalCols(path) {
    const t = state.report.data.find((d) => d.file === path);
    return t ? (t.possible_personal_data || []).map((p) => p.column) : [];
  }
  function setPersonal(folder) {
    const t = state.report.data.find((d) => d.file_set && d.file_set.split("/*")[0] === folder);
    return t ? t.possible_personal_data || [] : [];
  }

  function rowsForForm() {
    // one row per file, except file sets (one row per folder)
    const out = [], seen = new Set();
    state.proposal.files.forEach((f, i) => {
      if (f.set) {
        if (seen.has(f.set)) return;
        seen.add(f.set);
        const n = state.proposal.sets[f.set].length;
        out.push({ id: "set:" + f.set, label: `${f.set}/ (${n} file con le stesse colonne)`, set: f.set, dest: f.dest,
          name: f.name.includes("/") ? f.name.split("/").slice(0, -1).join("/") : "", reason: "un file per partecipante: restano insieme in data/raw/", kind: "set" });
      } else {
        out.push({ id: "f:" + i, label: f.path, dest: f.dest, name: f.name, reason: f.reason, kind: f.kind, path: f.path });
      }
    });
    return out;
  }

  function renderForm() {
    const p = state.proposal;
    ["#fa-title", "#fa-description", "#fa-provenance", "#fa-authors", "#fa-contact", "#fa-dates", "#fa-keywords",
      "#fa-article", "#fa-prereg", "#fa-holder"].forEach((id) => { $(id).value = ""; });
    $("#fa-study").value = p.study;
    state.personal = {};
    const rows = rowsForForm();
    state.rows = rows;
    let h = `<table class="fa-files"><thead><tr><th>File del progetto</th><th>Dove va</th><th>Nome nel deposito</th></tr></thead><tbody>`;
    rows.forEach((r, i) => {
      const opts = (r.kind === "set" ? ["data/raw", "exclude"] : p.destinations)
        .map((d) => `<option value="${d}"${d === r.dest ? " selected" : ""}>${esc(DEST_LABEL[d])}</option>`).join("");
      h += `<tr class="${r.dest === "exclude" ? "fa-excluded" : ""}" data-row="${i}">
        <td><code>${esc(r.label)}</code>${r.reason ? `<div class="fa-reason">${esc(r.reason)}</div>` : ""}</td>
        <td><select data-dest="${i}" aria-label="Destinazione di ${esc(r.label)}">${opts}</select></td>
        <td>${r.kind === "set" ? `<span class="fa-muted">data/raw/${esc(r.name)}/</span>` : `<input type="text" data-name="${i}" value="${esc(r.name)}" aria-label="Nome nel deposito di ${esc(r.label)}">`}</td></tr>`;
    });
    h += `</tbody></table>`;
    $("#fa-files").innerHTML = h;
    $("#fa-files").querySelectorAll("select[data-dest]").forEach((s) => s.addEventListener("change", (e) => {
      const i = +e.target.dataset.dest;
      rows[i].dest = e.target.value;
      e.target.closest("tr").classList.toggle("fa-excluded", rows[i].dest === "exclude");
      if (rows[i].dest === "data" && !/_data\.csv$/.test(rows[i].name) && /\.(csv|tsv)$/i.test(rows[i].label)) {
        rows[i].name = `study-${$("#fa-study").value}_description-${rows[i].label.split("/").pop().replace(/\.[^.]+$/, "").replace(/[^A-Za-z0-9]/g, "").toLowerCase()}_data.csv`;
        $(`input[data-name="${i}"]`).value = rows[i].name;
      }
      renderPersonal();
      renderDictionaries();
    }));
    $("#fa-files").querySelectorAll("input[data-name]").forEach((inp) => inp.addEventListener("change", (e) => { rows[+e.target.dataset.name].name = e.target.value.trim(); }));
    renderPersonal();
    state.drafts = null;
    renderDictionaries();
    renderLicenses();
  }

  function keptData() {
    // data files and sets kept in the deposit, with the paths to describe
    return state.rows.filter((r) => r.dest !== "exclude" && ((r.dest === "data" && /\.(csv|tsv)$/i.test(r.label)) || (r.kind === "set" && r.dest === "data/raw")
      || (r.dest === "data/raw" && /\.(csv|tsv)$/i.test(r.label))));
  }

  function renderPersonal() {
    const items = [];
    keptData().forEach((r) => {
      const cols = r.kind === "set" ? setPersonal(r.set) : personalCols(r.path);
      cols.forEach((c) => items.push({ key: r.id + "|" + c, file: r.label, col: c }));
    });
    state.personal = state.personal || {};
    if (!items.length) { $("#fa-personal").innerHTML = "<p>Nessuna colonna riconosciuta come dato personale nei file che vanno nel deposito.</p>"; return; }
    $("#fa-personal").innerHTML = "<p>Queste colonne sembrano identificare le persone. Quelle spuntate vengono tolte dalla copia nel deposito (i vostri file non cambiano).</p>"
      + items.map((it) => {
        const on = state.personal[it.key] !== false;
        return `<label class="fa-check"><input type="checkbox" data-personal="${esc(it.key)}"${on ? " checked" : ""}> <code>${esc(it.col)}</code> in <code>${esc(it.file)}</code></label>`;
      }).join("");
    $("#fa-personal").querySelectorAll("input[data-personal]").forEach((c) => c.addEventListener("change", (e) => {
      state.personal[e.target.dataset.personal] = e.target.checked;
      renderDictionaries();
    }));
  }

  function dropped(r) {
    const cols = r.kind === "set" ? setPersonal(r.set) : personalCols(r.path);
    return cols.filter((c) => (state.personal || {})[r.id + "|" + c] !== false);
  }

  function dictTarget(r) {
    if (r.dest === "data") return { file: r.name.replace(/_data\.csv$/, "").replace(/\.(csv|tsv)$/i, "") + "_dictionary.csv", of: "data/" + r.name };
    if (r.kind === "set") return { file: "raw-" + r.set.split("/").pop().replace(/[^A-Za-z0-9]/g, "").toLowerCase() + "_dictionary.csv", of: "data/raw/" + (r.name ? r.name + "/" : "") };
    return { file: "raw-" + r.name.replace(/\.(csv|tsv)$/i, "").replace(/[^A-Za-z0-9]/g, "").toLowerCase() + "_dictionary.csv", of: "data/raw/" + r.name };
  }

  function renderDictionaries() {
    const kept = keptData();
    const box = $("#fa-dicts");
    if (!kept.length) { box.innerHTML = "<p>Nessun file di dati nel deposito.</p>"; return; }
    if (!state.drafts) {
      const req = state.rows.filter((r) => /\.(csv|tsv)$/i.test(r.label) || r.kind === "set")
        .map((r) => ({ key: r.id, paths: r.kind === "set" ? state.proposal.sets[r.set] : [r.path] }));
      state.drafts = callPy("drafts", state.root, JSON.stringify(req));
    }
    let h = "<p>Una tabella per ogni file di dati: una riga per colonna. I campi con <mark>TODO</mark> li conoscete solo voi: scriveteli qui, oppure più tardi nei file CSV del deposito.</p>";
    kept.forEach((r) => {
      const d = state.drafts[r.id];
      const tgt = dictTarget(r);
      h += `<h4><code>${esc(tgt.of)}</code></h4>`;
      if (!d || d.error) { h += `<p class="fa-bad">${esc(d ? d.error : "nessuna bozza")}</p>`; return; }
      const drop = new Set(dropped(r));
      h += `<div class="fa-scroll"><table class="fa-dict"><thead><tr><th>variable_name</th>${DICT_COLS.map((c) => `<th>${c}</th>`).join("")}</tr></thead><tbody>`;
      d.rows.forEach((row, j) => {
        if (drop.has(row.variable_name)) return;
        h += `<tr><td><code>${esc(row.variable_name)}</code></td>` + DICT_COLS.map((c) =>
          `<td><input type="text" data-dict="${esc(r.id)}" data-row="${j}" data-col="${c}" value="${esc(row[c])}" class="${/TODO/.test(row[c] || "") ? "fa-todo" : ""}" aria-label="${c} di ${esc(row.variable_name)}"></td>`).join("") + "</tr>";
      });
      h += "</tbody></table></div>";
    });
    box.innerHTML = h;
    box.querySelectorAll("input[data-dict]").forEach((inp) => inp.addEventListener("input", (e) => {
      const t = e.target;
      state.drafts[t.dataset.dict].rows[+t.dataset.row][t.dataset.col] = t.value;
      t.classList.toggle("fa-todo", /TODO/.test(t.value));
    }));
  }

  function renderLicenses() {
    const code = state.report.materials_present.code;
    $("#fa-lic-code-row").hidden = !code;
  }

  // ----------------------------------------------------------------- build

  function collect() {
    const study = $("#fa-study").value.trim();
    const errors = [];
    if (!/^[A-Za-z0-9]+$/.test(study)) errors.push("Il nome breve dello studio può contenere solo lettere e numeri, senza spazi.");
    const files = [], data = {}, setSummary = {}, dicts = [];
    state.rows.forEach((r) => {
      if (r.dest === "exclude") return;
      if (r.kind === "set") {
        const sub = r.name ? r.name + "/" : "";
        state.proposal.sets[r.set].forEach((p) => {
          const to = "data/raw/" + sub + p.split("/").pop();
          files.push({ from: p, to, set: r.set });
          const drop = dropped(r);
          if (drop.length) data[to] = { drop, normalise: false };
        });
        setSummary["data/raw/" + (r.name || "")] = state.proposal.sets[r.set].length;
      } else {
        if (!r.name) { errors.push(`Manca il nome nel deposito per ${r.label}.`); return; }
        const to = r.dest === "." ? r.name : r.dest + "/" + r.name;
        files.push({ from: r.path, to });
        if (r.dest === "data") {
          if (!/^([a-z]+-[a-zA-Z0-9]+_)+data\.csv$/.test(r.name)) errors.push(`"${r.name}": i file in data/ devono chiamarsi chiave-valore_..._data.csv (per esempio study-${study}_data.csv).`);
          data[to] = { drop: dropped(r) };
        } else if (/\.(csv|tsv)$/i.test(r.name) && dropped(r).length) {
          data[to] = { drop: dropped(r), normalise: false };
        }
      }
      if (keptData().includes(r)) {
        const d = state.drafts && state.drafts[r.id];
        const tgt = dictTarget(r);
        if (d && d.rows) dicts.push({ file: tgt.file, of: tgt.of, rows: d.rows, dropped: dropped(r) });
      }
    });
    const tos = files.map((f) => f.to);
    const dup = tos.filter((t, i) => tos.indexOf(t) !== i);
    if (dup.length) errors.push("Due file hanno lo stesso nome nel deposito: " + [...new Set(dup)].join(", "));
    const hasCode = files.some((f) => f.to.startsWith("scripts/"));
    const dataLic = $("#fa-lic-data").value;
    const licenses = [{ what: "Dati (data/, dictionaries/, dataset_description.json)", license: dataLic }];
    if (hasCode) licenses.push({ what: "Codice (scripts/)", license: "GPL-3.0" });
    licenses.push({ what: "README, documenti, figure e materiali propri (docs/, output/, materials/)", license: "CC-BY-4.0" });
    const lang = $("#fa-lang").value;
    if (lang === "en") {
      licenses[0].what = "Data (data/, dictionaries/, dataset_description.json)";
      if (hasCode) licenses[1].what = "Code (scripts/)";
      licenses[licenses.length - 1].what = "README, documents, figures and own materials (docs/, output/, materials/)";
    }
    const form = {
      lang, title: $("#fa-title").value.trim(), description: $("#fa-description").value.trim(),
      authors: $("#fa-authors").value, contact: $("#fa-contact").value.trim(), provenance: $("#fa-provenance").value.trim(),
      dates: $("#fa-dates").value.trim(), keywords: $("#fa-keywords").value.trim(), article: $("#fa-article").value.trim(),
      prereg: $("#fa-prereg").value.trim(), holder: $("#fa-holder").value.trim(), data_license: dataLic, licenses,
    };
    return { errors, plan: { files, data, set_summary: setSummary }, dicts, form };
  }

  async function build() {
    const { errors, plan, dicts, form } = collect();
    const box = $("#fa-errors");
    if (errors.length) { box.innerHTML = `<ul>${errors.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>`; box.hidden = false; box.scrollIntoView({ behavior: "smooth" }); return; }
    box.hidden = true;
    status("Costruisco la versione da depositare…");
    await tick();
    const out = `/out/${state.project}_deposit`;
    py.runPython("import shutil; shutil.rmtree('/out', ignore_errors=True)");
    py.FS.mkdirTree("/out");
    let res;
    try {
      res = callPy("build", state.root, out, JSON.stringify(plan), JSON.stringify(dicts), JSON.stringify(form));
    } catch (e) {
      status("Errore nella costruzione del deposito: " + e.message.split("\n").slice(-2).join(" "), "bad");
      return;
    }
    renderResult(res);
    status("Versione da depositare pronta.", "ok");
  }

  function renderResult(res) {
    const v = res.verify, b = res.build;
    const its = [];
    const ok = (good, text) => its.push(`<li>${good ? ICON.ok : ICON.bad} ${text}</li>`);
    const p = v.psychds;
    ok(p.valid_minimum, p.valid_minimum ? "Psych-DS: cartella <code>data/</code>, nomi dei file e <code>dataset_description.json</code> rispettano le regole minime."
      : "Psych-DS: " + esc(p.problems.map(tr).join("; ")));
    const cov = v.dictionaries.coverage.filter((c) => !c.dictionary || (c.data_columns_not_in_dictionary || []).length);
    if (v.data.length) ok(!cov.length, cov.length ? "Data dictionary mancanti per: " + esc(cov.map((c) => c.data).join(", ")) : "Ogni file di dati ha il suo data dictionary.");
    const pers = v.data.flatMap((t) => (t.possible_personal_data || []).map((x) => (typeof x === "string" ? x : x.column)));
    if (v.data.length) ok(!pers.length, pers.length ? "Restano colonne che sembrano dati personali: " + esc(pers.join(", ")) : "Nessuna colonna riconosciuta come dato personale.");
    ok(!v.naming.problems.length, v.naming.problems.length ? "Nomi ancora da sistemare: " + esc(v.naming.problems.map((x) => x.path).join(", ")) : "Nomi di file e cartelle senza spazi, accenti o parole di versione.");
    let h = `<ul class="fa-verify">${its.join("")}</ul>`;
    const unresolved = Object.entries(b.unresolved_paths || {});
    if (unresolved.length) {
      h += `<div class="fa-box fa-box-warn"><strong>Da sistemare a mano negli script</strong><ul>`
        + unresolved.map(([f, xs]) => `<li><code>${esc(f)}</code>: ${esc(xs.map(tr).join("; "))}</li>`).join("") + "</ul></div>";
    }
    const rw = Object.entries(b.rewrites || {});
    if (rw.length) h += `<details><summary>Percorsi aggiornati negli script (${rw.reduce((s, [, x]) => s + x.length, 0)})</summary><ul>`
      + rw.map(([f, xs]) => `<li><code>${esc(f)}</code><ul>${xs.map((x) => `<li><code>${esc(x)}</code></li>`).join("")}</ul></li>`).join("") + "</ul></details>";
    const dc = Object.entries(b.data_changes || {});
    if (dc.length) h += `<details><summary>Modifiche ai file di dati (${dc.length})</summary><ul>`
      + dc.map(([f, xs]) => `<li><code>${esc(f)}</code>: ${esc(xs.map(tr).join("; "))}</li>`).join("") + "</ul></details>";
    if (b.left_out.length) h += `<details><summary>Lasciati fuori (${b.left_out.length})</summary><ul>${b.left_out.map((x) => `<li><code>${esc(x)}</code></li>`).join("")}</ul></details>`;
    const todo = Object.entries(res.todo || {}).filter(([, n]) => n > 0);
    if (todo.length) h += `<p>Restano campi <mark>TODO</mark> da completare: ${todo.map(([f, n]) => `<code>${esc(f)}</code> (${n})`).join(", ")}.</p>`;
    const bytes = py.FS.readFile(res.zip);
    const url = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }));
    const name = res.zip.split("/").pop();
    h += `<p><a class="fa-button" href="${url}" download="${esc(name)}">Scarica ${esc(name)}</a> <span class="fa-muted">${res.n_files} file, ${Math.max(1, Math.round(bytes.length / 1024))} KB</span></p>`;
    h += `<h4>Prima di caricarlo</h4><ol>
      <li>Aprite lo zip e controllate il contenuto.</li>
      ${b.rewrites && Object.keys(b.rewrites).length || unresolved.length || v.code.files.length ? "<li>Eseguite gli script dalla cartella del deposito, sul vostro computer: la pagina ha aggiornato i percorsi ma non può eseguire il codice.</li>" : ""}
      <li>Completate i campi TODO nel README e nei data dictionary.</li>
      <li>Caricate la cartella sul <a href="https://psych-ds.github.io/validator/" target="_blank">validator di Psych-DS</a>.</li>
      <li>Caricate lo zip su <a href="zenodo.html">Zenodo</a>; quando avete il DOI, scrivetelo nel README e nella Data availability dell'articolo.</li></ol>`;
    $("#fa-result").innerHTML = h;
    $("#fa-result-section").hidden = false;
    $("#fa-result-section").scrollIntoView({ behavior: "smooth" });
  }

  // ------------------------------------------------------------------ init

  function init() {
    const input = $("#fa-input"), drop = $("#fa-drop");
    if (!input) return;
    const run = async (getEntries) => {
      try {
        await loadEntries(await getEntries());
      } catch (e) {
        status(e.message, "bad");
        console.error(e);
      }
    };
    input.addEventListener("change", () => run(() => filesFromInput(input.files)));
    ["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("fa-over"); }));
    ["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove("fa-over")));
    drop.addEventListener("drop", (e) => { e.preventDefault(); run(() => filesFromDrop(e.dataTransfer.items)); });
    $("#fa-build").addEventListener("click", () => build());
    $("#fa-study").addEventListener("change", (e) => {
      const s = e.target.value.trim();
      state.rows.forEach((r, i) => {
        if (r.dest === "data" && /^study-[A-Za-z0-9]+_/.test(r.name)) {
          r.name = r.name.replace(/^study-[A-Za-z0-9]+_/, `study-${s}_`);
          const inp = $(`input[data-name="${i}"]`);
          if (inp) inp.value = r.name;
        }
      });
      renderDictionaries();
    });
  }

  // used by the page and by tests: entries = [{path: "progetto/…", bytes: Uint8Array}]
  window.FairDeposit = { loadEntries, build, get state() { return state; }, get python() { return py; } };
  document.addEventListener("DOMContentLoaded", init);
})();
