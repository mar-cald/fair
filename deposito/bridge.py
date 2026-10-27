"""Glue between the "Prepara il deposito" page and the fair-check scripts.

Runs in the browser (Pyodide). The page writes the chosen folder into the
in-memory file system, then calls the functions below with JSON strings and
gets JSON strings back. The checks and the deposit are the same as in the
fair-check skill: this module only proposes defaults for the form and writes
the README from what the researcher filled in.
"""

import json
import re
import unicodedata
from pathlib import Path, PurePosixPath

import build_deposit as bd
import draft_dictionary as dd
import make_psychds as mp
from fair_scan import (CODE_EXT, DICT_NAME, PROPRIETARY_DATA, PSYCHDS_NAME, VERSION_WORDS, parse_dictionary, scan)

LICENSES_DIR = "/fair/licenses"
JUNK = {"rplots.pdf", ".rhistory", ".rdata", "thumbs.db", "desktop.ini"}
TEST_RUNS = re.compile(r"(?i)^(quickrun|defaultlog)\.csv$")
RAW_DIRS = {"raw", "raw_data", "rawdata", "grezzi", "sourcedata", "original"}
OUTPUT_DIRS = {"output", "outputs", "results", "risultati", "figures", "figure", "figs", "plots", "tables", "tabelle"}
MATERIAL_DIRS = {"materials", "materiali", "stimuli", "stimoli", "questionnaires", "questionari", "task", "experiment", "esperimento"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".tif", ".tiff", ".gif", ".eps"}
DESTINATIONS = ["data", "data/raw", "scripts", "output/figures", "output/tables", "materials", "docs", ".", "exclude"]
_LAST = {}  # the last scan, reused by drafts()


def safe_name(name):
    """File name without spaces, accents, special characters or words like "final"."""
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    stem, dot, ext = folded.rpartition(".") if "." in folded else (folded, "", "")
    stem = re.sub(r"[^A-Za-z0-9_-]+", "_", stem).strip("_")
    cleaned = re.sub(r"(?i)(?:^|[_-])(final[ei]?|definitiv[oaie]|def|nuov[oaie]|new|old|vecchi[oaie]?|copy|copia|ultim[oaie]|last|latest)(?=$|[_-])", "", stem).strip("_-")
    stem = cleaned or stem or "file"
    return f"{stem}.{ext}" if dot else stem


def alnum(s):
    folded = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]", "", folded).lower() or "study"


def _parts(path):
    return [p.lower() for p in PurePosixPath(path).parts[:-1]]


def _base(name):
    """'data/x.xlsx [Sheet1]' -> 'data/x.xlsx'"""
    return name.split(" [")[0]


def _sheet(name):
    m = re.search(r" \[(.+)\]$", name)
    return m.group(1) if m else None


def raw_name(path):
    """Name under data/raw/: the path without the leading data/ and raw/ folders."""
    p = PurePosixPath(path)
    sub = [x for x in p.parent.parts if x.lower() not in ("data", "dati") and x.lower() not in RAW_DIRS]
    return "/".join(sub + [safe_name(p.name)])


def _units(report):
    """The tables the scan found: single files (one per sheet) and file sets."""
    units = []
    for t in report["data"]:
        if "file_set" in t:
            units.append({"key": t["file_set"], "label": t["file_set"], "paths": [_base(f) for f in t.get("files", [])],
                          "sheet": None, "set": True, "csv": all(f.lower().endswith((".csv", ".tsv")) for f in t.get("files", [])),
                          "personal": t.get("possible_personal_data", []), "software": t.get("software"),
                          "format": t.get("format")})
        elif "columns" in t:
            f = t["file"]
            ext = PurePosixPath(_base(f)).suffix.lower()
            units.append({"key": f, "label": f, "paths": [_base(f)], "sheet": _sheet(f), "set": False,
                          "csv": ext in (".csv", ".tsv") and not t.get("format"),
                          "personal": [p["column"] for p in t.get("possible_personal_data", [])],
                          "software": t.get("software"), "format": t.get("format"),
                          "export_structure": t.get("export_structure"),
                          "id_is_personal": t.get("participant_id_column_is_personal")})
    return units


def propose(report, root):
    """A destination, a new name and a reason for every file of the project, and
    the open CSV copies to make of the data that are not CSV."""
    root = Path(root)
    study = alnum(Path(report["project"]).name)
    manuscripts = {m["file"] for m in report.get("manuscripts", [])}
    experiment = {e["file"]: e["what"] for e in report.get("experiment_files", [])}
    archives = set((report.get("archives") or {}).get("files", []))
    not_read = {e["file"]: e.get("reason") or "" for e in report.get("data_not_read", [])}
    code_text = ""
    for c in report["code"]["files"]:
        try:
            code_text += (root / c["file"]).read_text(errors="replace") + "\n"
        except OSError:
            pass
    units = _units(report)
    by_path = {}
    for u in units:
        for p in u["paths"]:
            by_path.setdefault(p, []).append(u)

    def is_test(p):
        return bool(TEST_RUNS.match(PurePosixPath(p).name))

    def in_dirs(p, dirs):
        return any(x in dirs for x in _parts(p))

    # tables that end up in data/: CSV files outside raw/output folders, and CSV copies of the others
    targets = [u for u in units if not u["set"] and u["csv"] and not in_dirs(u["paths"][0], RAW_DIRS | OUTPUT_DIRS)
               and not is_test(u["paths"][0])]
    # tables that get an open CSV copy in data/: files that are not CSV, and raw CSV
    # exports that no script reads (in a project without code, the copy is the data)
    exports = [u for u in units if not u["set"] and not is_test(u["paths"][0])
               and PurePosixPath(u["paths"][0]).name not in code_text
               and (not u["csv"] or in_dirs(u["paths"][0], RAW_DIRS))]
    n_targets = len(targets) + len(exports)

    used = set()

    def data_name(stem, ext=""):
        """Psych-DS name, unique in data/ (an .xlsx and a .csv with the same stem get different names)."""
        name = f"study-{study}_data.csv" if n_targets == 1 else f"study-{study}_description-{alnum(stem)}_data.csv"
        if name in used:
            name = name.replace("_data.csv", f"{alnum(ext)}_data.csv")
        i = 2
        while name in used:
            name = re.sub(r"\d*_data\.csv$", f"{i}_data.csv", name)
            i += 1
        used.add(name)
        return name

    rows, sets = [], {}
    for item in report["inventory"]:
        path = item["path"]
        p = PurePosixPath(path)
        name, ext, parts = p.name, p.suffix.lower(), _parts(path)
        row = {"path": path, "size_kb": item["size_kb"], "dest": "exclude", "name": safe_name(name), "reason": "", "kind": "other"}
        mine = by_path.get(path, [])
        set_unit = next((u for u in mine if u["set"]), None)
        if name.lower() in JUNK:
            row.update(reason="file prodotto da R o dal sistema")
        elif re.match(r"(?i)^(readme|leggimi)", name) and ext in ("", ".md", ".txt", ".rst", ".markdown", ".html", ".pdf", ".docx"):
            row.update(reason="sostituito dal README generato", kind="readme")
        elif re.match(r"(?i)^(licen[cs]e|copying)", name):
            row.update(reason="sostituito dal LICENSE generato", kind="license")
        elif DICT_NAME.search(p.stem) and not mine and ext in (".csv", ".tsv", ".docx", ".doc", ".pdf", ".xlsx", ".txt"):
            row.update(reason="il contenuto passa nel data dictionary qui sotto", kind="dictionary")
        elif path in archives:
            row.update(kind="archive", reason="archivio compresso: la pagina non ne legge il contenuto. Estraetelo nella "
                                              "cartella del progetto e caricatela di nuovo")
        elif is_test(path):
            row.update(kind="test", reason="prova dell'esperimento (OpenSesame): lasciatela fuori, a meno che l'analisi non la usi")
        elif any(VERSION_WORDS.search(x) for x in PurePosixPath(path).parts[:-1]):
            row.update(reason="in una cartella di versioni vecchie: includetelo solo se fa parte dell'analisi",
                       kind="code" if ext in CODE_EXT else "other")
        elif path in experiment:
            row.update(dest="materials", kind="experiment", what=experiment[path],
                       reason=f"esperimento ({experiment[path]}): va in materials/, non viene eseguito")
        elif set_unit:
            row.update(dest="data/raw", name=raw_name(path), kind="set", set=set_unit["key"])
            sets.setdefault(set_unit["key"], []).append(path)
        elif path in not_read:
            why = not_read[path]
            why = ("i file SPSS, Stata e SAS non si leggono nel browser" if why.startswith("pyreadstat") else
                   "la lettura dei file Excel non è disponibile" if why.startswith("openpyxl") else
                   "JSON non valido o troppo grande" if "JSON" in why else "file illeggibile")
            row.update(kind="proprietary", reason="la pagina non riesce ad aprirlo (" + why + "): se è l'export "
                       "originale e non contiene dati personali, mettetelo in data/raw; se i dati servono, salvatene una "
                       "copia CSV e caricate di nuovo la cartella")
        elif mine and all(u["csv"] for u in mine):
            u = mine[0]
            if in_dirs(path, OUTPUT_DIRS):
                row.update(dest="output/tables", kind="output")
            elif in_dirs(path, RAW_DIRS):
                row.update(dest="data/raw", kind="raw", unit=u["key"], name=raw_name(path))
                if u in exports:
                    row["reason"] = "export originale: resta in data/raw; la copia CSV pulita va in data/ (qui sotto)"
            else:
                es = u.get("export_structure") or {}
                referenced = name in code_text
                row.update(dest="data", kind="data", unit=u["key"],
                           name=name if PSYCHDS_NAME.match(name) else data_name(p.stem),
                           remove_rows=bool(es) and not referenced, export_structure=es)
                if es and referenced:
                    row["reason"] = ("le righe aggiunte dall'export restano: uno script legge questo file e potrebbe già "
                                     "saltarle")
        elif mine:
            # a table that is not CSV (JSON, E-Prime log, Excel, SPSS ...): the original goes in data/raw,
            # an open CSV copy in data/
            personal = sorted({c for u in mine for c in u["personal"]})
            copied = any(u in exports for u in mine)
            if personal:
                reason = (f"contiene colonne personali ({', '.join(personal[:4])}) e non può essere ripulito: "
                          + ("nel deposito va la copia CSV senza quelle colonne" if copied else
                             "uno script lo legge, quindi va tolto a mano prima di depositarlo"))
            else:
                reason = ("l'originale va in data/raw; la copia CSV in data/ (qui sotto)" if copied else
                          "l'originale va in data/raw: uno script lo legge e ne ricava i dati")
            row.update(dest="exclude" if personal else "data/raw", kind="export", unit=mine[0]["key"], name=raw_name(path),
                       reason=reason)
        elif ext in PROPRIETARY_DATA:
            row.update(kind="proprietary",
                       reason=f"formato {PROPRIETARY_DATA[ext]}: la pagina non può aprirlo per controllarlo. Se è l'export "
                              "originale e non contiene dati personali, mettetelo in data/raw; se i dati servono, salvatene "
                              "una copia CSV e caricate di nuovo la cartella")
        elif ext in CODE_EXT and path not in manuscripts:
            row.update(dest="scripts", kind="code")
        elif ext == ".rproj":
            row.update(dest=".", kind="rproj")
        elif path in manuscripts:
            row.update(dest="docs", kind="manuscript")
        elif ext in IMAGE_EXT or (ext == ".pdf" and in_dirs(path, OUTPUT_DIRS)):
            row.update(dest="output/figures", kind="output")
        elif in_dirs(path, MATERIAL_DIRS):
            row.update(dest="materials", kind="material",
                       reason="se è uno strumento di terzi (test pubblicati, stimoli con copyright) lasciatelo fuori")
        elif ext in (".pdf", ".docx", ".doc", ".odt", ".md", ".txt", ".html"):
            row.update(dest="docs", kind="doc")
        rows.append(row)

    sheets_per_file = {}
    for u in exports:
        sheets_per_file[u["paths"][0]] = sheets_per_file.get(u["paths"][0], 0) + 1

    def copy_stem(u):
        stem = safe_name(PurePosixPath(u["paths"][0]).stem)
        return f"{stem}{u['sheet']}" if u["sheet"] and sheets_per_file[u["paths"][0]] > 1 else stem

    copies = [{"key": u["key"], "from": u["paths"][0], "sheet": u["sheet"], "label": u["label"], "include": True,
               "name": data_name(copy_stem(u), PurePosixPath(u["paths"][0]).suffix), "software": u.get("software"),
               "format": u.get("format")} for u in exports]
    return {"study": study, "files": rows, "sets": sets, "units": units, "copies": copies, "destinations": DESTINATIONS}


def _existing_entries(root, report):
    entries = {}
    for d in report["dictionaries"]["dictionary_files"]:
        try:
            parsed = parse_dictionary(Path(root) / d["file"], Path(root))
        except Exception:  # noqa: BLE001
            continue
        for k, v in parsed.get("entries", {}).items():
            entries.setdefault(k, v)
    return entries


def drafts(root, files_json):
    """Dictionary drafts for the tables the researcher kept.

    files_json: [{"key": id, "paths": [project paths], "sheet": name or null}].
    Values found in a dictionary already in the project are carried over."""
    root = Path(root)
    report = _LAST.get(str(root)) or scan(root)
    existing = _existing_entries(root, report)
    out = {}
    for f in json.loads(files_json):
        try:
            rows = dd.draft([root / p for p in f["paths"]], f.get("sheet"))
        except Exception as e:  # noqa: BLE001
            out[f["key"]] = {"error": str(e)}
            continue
        for r in rows:
            old = existing.get(r["variable_name"])
            if old:
                for k in dd.COLUMNS:
                    if k != "variable_name" and old.get(k):
                        r[k] = old[k]
        out[f["key"]] = {"rows": rows}
    return json.dumps(out, ensure_ascii=False)


def scan_json(root):
    report = scan(root)
    _LAST.clear()
    _LAST[str(Path(root).expanduser().resolve())] = report
    _LAST[str(root)] = report
    return json.dumps({"report": report, "proposal": propose(report, root)}, ensure_ascii=False, default=str)


# --------------------------------------------------------------------- README

T = {
    "it": {
        "authors": "Autori", "contact": "Contatto", "study": "Lo studio", "contents": "Contenuto",
        "read": "Come leggere i dati", "repro": "Come riprodurre i risultati", "changes": "Modifiche rispetto ai file originali",
        "license": "Licenza", "cite": "Come citare", "links": "Materiali collegati",
        "read_text": ("I file di dati sono testo separato da virgole (UTF-8), con una riga di intestazione. "
                      "Si aprono con qualunque foglio di calcolo, con R (`read.csv()`) o con Python (`pandas.read_csv()`). "
                      "Ogni colonna è descritta nei file di `dictionaries/` (significato, tipo, unità, valori ammessi, "
                      "codifica, valori mancanti) e, in forma leggibile dalle macchine, in `dataset_description.json` (Psych-DS)."),
        "repro_text": "Gli script vanno eseguiti in quest'ordine, dalla cartella principale del progetto:",
        "packages": "Pacchetti usati", "rproj": "Aprire prima `{}` in RStudio: imposta la cartella di lavoro.",
        "renv": "Per registrare le versioni esatte dei pacchetti: `renv::init()` e poi `renv::snapshot()`.",
        "version": "Versione del software: TODO (per esempio R 4.4.2).",
        "renamed": "File rinominati o spostati", "paths": "Negli script sono stati aggiornati i percorsi dei file",
        "removed_cols": "colonne tolte", "converted": "convertito in CSV separato da virgole",
        "third": "Materiali di terzi: non inclusi, soggetti alle condizioni dei rispettivi titolari.",
        "full": "Testi completi in `LICENSE`.", "article": "Articolo", "prereg": "Preregistrazione",
        "this_readme": "questo file", "lic_file": "licenze", "psychds": "metadati Psych-DS e descrizione di ogni colonna",
        "dict_of": "descrizione delle colonne di", "set_of": "file con le stesse colonne",
    },
    "en": {
        "authors": "Authors", "contact": "Contact", "study": "About the study", "contents": "Contents",
        "read": "How to read the data", "repro": "How to reproduce the results", "changes": "Changes from the original files",
        "license": "License", "cite": "How to cite", "links": "Related materials",
        "read_text": ("The data files are comma-separated text (UTF-8) with one header row. They open in any spreadsheet "
                      "program, in R (`read.csv()`) or in Python (`pandas.read_csv()`). Every column is described in the "
                      "files in `dictionaries/` (meaning, type, unit, allowed values, coding, missing values) and, in "
                      "machine-readable form, in `dataset_description.json` (Psych-DS)."),
        "repro_text": "Run the scripts in this order, from the project's root folder:",
        "packages": "Packages used", "rproj": "Open `{}` in RStudio first: it sets the working directory.",
        "renv": "To record the exact package versions: `renv::init()`, then `renv::snapshot()`.",
        "version": "Software version: TODO (e.g. R 4.4.2).",
        "renamed": "Files renamed or moved", "paths": "The file paths inside the scripts were updated",
        "removed_cols": "columns removed", "converted": "converted to comma-separated CSV",
        "third": "Third-party materials: not included, subject to the conditions of their owners.",
        "full": "Full texts in `LICENSE`.", "article": "Article", "prereg": "Preregistration",
        "this_readme": "this file", "lic_file": "licenses", "psychds": "Psych-DS metadata, with the description of every column",
        "dict_of": "description of the columns of", "set_of": "files with the same columns",
    },
}
LIC_LABEL = {"CC0-1.0": "CC0 1.0 Universal (CC0-1.0)", "GPL-3.0": "GNU General Public License v3.0 (GPL-3.0)",
             "CC-BY-4.0": "Creative Commons Attribution 4.0 International (CC BY 4.0)"}


CHANGES_IT = [(r"^semicolon-separated -> comma-separated$", "da separato con punto e virgola a separato con virgole"),
              (r"^tab-separated -> comma-separated$", "da separato con tabulazioni a separato con virgole"),
              (r"^pipe-separated -> comma-separated$", "da separato con barre verticali a separato con virgole"),
              (r"^decimal comma -> decimal point$", "virgola decimale sostituita dal punto"),
              (r"^columns removed: ", "colonne tolte: "), (r"^columns left out: ", "colonne tolte: "),
              (r"^(\S+?)( with BOM)? -> UTF-8$", r"codifica \1 convertita in UTF-8"),
              (r"^removed (\d+) line\(s\) above the header$", r"tolte \1 righe sopra l'intestazione"),
              (r"^left out (\d+) line\(s\) above the header$", r"tolte \1 righe sopra l'intestazione"),
              (r"^removed (\d+) label row\(s\) under the header \((.*)\)$", r"tolte \1 righe di etichette sotto l'intestazione (\2)"),
              (r"^left out (\d+) label row\(s\) \((.*)\)$", r"tolte \1 righe di etichette sotto l'intestazione (\2)"),
              (r"^removed (\d+) footer row\(s\) \(END OF FILE\)$", r"tolte \1 righe finali (END OF FILE)"),
              (r"^left out the footer \(END OF FILE\)$", "tolta la riga finale (END OF FILE)"),
              (r"^removed the empty unnamed last column$", "tolta l'ultima colonna vuota e senza nome"),
              (r"^(\d+) rows, (\d+) columns, from (.*)$", r"\1 righe, \2 colonne, da \3"),
              (r"E-Prime log \(\.txt written during the session\)", "log di E-Prime (.txt scritto durante la sessione)"),
              (r"JSON records in a \.txt \(e\.g\. a JATOS result file\)", "record JSON in un .txt (risultato di JATOS)"),
              (r"JSON records", "record JSON")]


def tr_changes(ch, lang):
    if lang != "it":
        return ch
    out = []
    for c in ch:
        for pat, rep in CHANGES_IT:
            c = re.sub(pat, rep, c)  # several patterns can apply to one line
        out.append(c)
    return out


def readme_text(form, plan, packages, data_changes, lic_parts, lang, data_info=None, copies=None, rewrites=None):
    t = T.get(lang, T["en"])
    data_info = data_info or {}
    L = []
    L += [f"# {form.get('title') or 'TODO'}", ""]
    if form.get("description"):
        L += [form["description"].strip(), ""]
    authors = [a.strip() for a in (form.get("authors") or "").splitlines() if a.strip()]
    L += [f"{t['authors']}: " + ("; ".join(authors) if authors else "TODO (ORCID)")]
    L += [f"{t['contact']}: {form.get('contact') or 'TODO'}", ""]
    L += [f"## {t['study']}", ""]
    L += [(form.get("provenance") or "TODO").strip(), ""]

    L += [f"## {t['contents']}", "", "```"]
    entries = [("README.md", t["this_readme"]), ("LICENSE", t["lic_file"]), ("dataset_description.json", t["psychds"])]
    rows_word = "righe" if lang == "it" else "rows"
    cols_word = "colonne" if lang == "it" else "columns"
    for f in plan["files"]:
        if f["to"].startswith("data/raw/") and f.get("set"):
            continue
        info = data_info.get(f["to"])
        note = f.get("note") or (f"{info[0]} {rows_word}, {info[1]} {cols_word}" if info else "")
        entries.append((f["to"], note))
    for folder, n in plan.get("set_summary", {}).items():
        entries.append((folder + "/", f"{n} {t['set_of']}"))
    copy_of = "copia CSV di" if lang == "it" else "CSV copy of"
    for c in plan.get("csv_copies", []):
        if c["to"] in (copies or {}):
            info = data_info.get(c["to"])
            src = c["from"] + (f" [{c['sheet']}]" if c.get("sheet") else "")
            entries.append((c["to"], f"{copy_of} {src}" + (f": {info[0]} {rows_word}, {info[1]} {cols_word}" if info else "")))
    for d in plan.get("dictionaries", []):
        entries.append((d["path"], f"{t['dict_of']} {d['of']}"))
    width = min(max(len(e[0]) for e in entries) + 2, 60)
    for path, note in sorted(entries, key=lambda e: (e[0].count("/") > 0, e[0])):
        L.append(f"{path:<{width}} {note}".rstrip())
    L += ["```", ""]

    L += [f"## {t['read']}", "", t["read_text"], ""]
    if form.get("read_notes"):
        L += [form["read_notes"].strip(), ""]

    scripts = sorted(f["to"] for f in plan["files"] if f["to"].startswith("scripts/"))
    if scripts:
        L += [f"## {t['repro']}", "", t["version"], ""]
        rproj = [f["to"] for f in plan["files"] if f["to"].lower().endswith(".rproj")]
        if rproj:
            L += [t["rproj"].format(rproj[0]), ""]
        r_pk = [p for p in packages.get("R", [])]
        py_pk = [p for p in packages.get("Python", [])]
        if r_pk:
            L += [f"{t['packages']} (R): " + ", ".join(r_pk), "", "```r",
                  "install.packages(c(" + ", ".join(f'"{p}"' for p in r_pk) + "))", "```", ""]
        if py_pk:
            L += [f"{t['packages']} (Python): " + ", ".join(py_pk), "", "```", "pip install " + " ".join(py_pk), "```", ""]
        L += [t["repro_text"], "", "```"]
        L += [f'source("{s}")' if s.lower().endswith(".r") else s for s in scripts]
        L += ["```", ""]
        if r_pk:
            L += [t["renv"], ""]

    changes = []
    renamed = [f for f in plan["files"] if f["from"] != f["to"] and not f.get("set")]
    if renamed:
        changes.append(f"{t['renamed']}: " + "; ".join(f"`{f['from']}` → `{f['to']}`" for f in renamed[:30]))
    for path, ch in data_changes.items():
        changes.append(f"`{path}`: " + "; ".join(tr_changes(ch, lang)))
    for path, ch in (copies or {}).items():
        changes.append(f"`{path}` ({copy_of} `{next((c['from'] for c in plan.get('csv_copies', []) if c['to'] == path), '')}`): "
                       + "; ".join(tr_changes(ch, lang)))
    if rewrites:
        changes.append(t["paths"] + ".")
    if changes:
        L += [f"## {t['changes']}", ""] + [f"- {c}" for c in changes] + [""]

    L += [f"## {t['license']}", ""]
    L += [f"- {what}: {LIC_LABEL[lic]}" for what, lic in lic_parts]
    L += [f"- {t['third']}", "", t["full"], ""]
    L += [f"## {t['cite']}", "", form.get("citation") or "TODO: Authors (year). Title (Version 1.0) [Data set]. Repository. https://doi.org/TODO", ""]
    L += [f"## {t['links']}", "", f"{t['article']}: {form.get('article') or 'TODO'}", "",
          f"{t['prereg']}: {form.get('prereg') or 'TODO'}", ""]
    return "\n".join(L)


# ---------------------------------------------------------------------- build

def build(root, out, plan_json, dicts_json, form_json):
    """Build the deposit, write documentation, verify, zip. Returns JSON."""
    plan, dicts, form = json.loads(plan_json), json.loads(dicts_json), json.loads(form_json)
    lang = form.get("lang", "it")
    report = bd.build_deposit(root, {"files": plan["files"], "data": plan.get("data", {}),
                                     "csv_copies": plan.get("csv_copies", [])}, out)
    outp = Path(out)

    (outp / "dictionaries").mkdir(exist_ok=True)
    written = []
    for d in dicts:
        rows = [r for r in d["rows"] if r["variable_name"] not in set(d.get("dropped", []))]
        target = outp / "dictionaries" / d["file"]
        dd.write_dictionary(rows, target)
        written.append({"path": f"dictionaries/{d['file']}", "of": d["of"]})
    if not any((outp / "dictionaries").iterdir()):
        (outp / "dictionaries").rmdir()
    plan["dictionaries"] = written

    lic_parts = [(p["what"], p["license"]) for p in form["licenses"] if p.get("license")]
    bd.write_license(outp, lic_parts, form.get("holder") or None, assets=LICENSES_DIR)

    meta = {"license": {"CC0-1.0": "https://creativecommons.org/publicdomain/zero/1.0/",
                        "CC-BY-4.0": "https://creativecommons.org/licenses/by/4.0/"}.get(form.get("data_license"), "TODO")}
    authors = []
    for a in (form.get("authors") or "").splitlines():
        if not a.strip():
            continue
        orcid = re.search(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", a)
        name = re.sub(r"[,(]?\s*(https?://orcid\.org/)?\d{4}-\d{4}-\d{4}-\d{3}[\dX]\)?", "", a).strip(" ,;")
        person = {"@type": "Person", "name": name}
        if orcid:
            person["identifier"] = f"https://orcid.org/{orcid.group(0)}"
        authors.append(person)
    if authors:
        meta["author"] = authors
    kw = [k.strip() for k in (form.get("keywords") or "").split(",") if k.strip()]
    if kw:
        meta["keywords"] = kw
    if form.get("dates"):
        meta["temporalCoverage"] = form["dates"]
    psy = None
    if (outp / "data").is_dir():
        try:
            psy = mp.make_psychds(outp, form.get("title") or "TODO", form.get("description") or "TODO", meta)
        except ValueError as e:
            psy = {"problems": [str(e)]}

    report_scan = scan(outp)
    pk = {"R": [], "Python": []}
    for c in report_scan["code"]["files"]:
        lang_c = "Python" if "Python" in c["language"] else ("R" if c["language"].startswith(("R", "Quarto", "Jupyter (R)")) else None)
        if lang_c:
            pk[lang_c] += [p for p in c.get("packages", []) if p not in pk[lang_c]]
    info = {t["file"]: (t.get("n_rows"), t.get("n_cols")) for t in report_scan["data"] if t.get("file") and t.get("n_rows") is not None}
    (outp / "README.md").write_text(readme_text(form, plan, pk, report["data_changes"], lic_parts, lang, info,
                                                report.get("csv_copies", {}), report.get("rewrites")))

    final = scan(outp)
    todo = {str(p.relative_to(outp)): p.read_text(errors="replace").count("TODO")
            for p in [outp / "README.md", *sorted((outp / "dictionaries").glob("*.csv"))] if p.exists()}
    to_check = {str(p.relative_to(outp)): p.read_text(errors="replace").count("to check")
                for p in sorted((outp / "dictionaries").glob("*.csv"))}
    target, n = bd.zip_deposit(outp)
    return json.dumps({"build": report, "psychds_json": psy, "verify": final, "todo": todo, "to_check": to_check,
                       "zip": str(target), "n_files": n},
                      ensure_ascii=False, default=str)
