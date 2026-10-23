"""Glue between the "Prepara il deposito" page and the fair-check scripts.

Runs in the browser (Pyodide). The page writes the chosen folder into the
in-memory file system, then calls the functions below with JSON strings and
gets JSON strings back. The checks and the deposit are the same as in the
fair-check skill: this module only proposes defaults for the form and writes
the README from what the researcher filled in.
"""

import csv
import json
import re
import unicodedata
from pathlib import Path, PurePosixPath

import build_deposit as bd
import draft_dictionary as dd
import make_psychds as mp
from fair_scan import (CODE_EXT, DICT_NAME, MANUSCRIPT_NAME, PROPRIETARY_DATA, PSYCHDS_NAME, VERSION_WORDS,
                       parse_dictionary, scan)

LICENSES_DIR = "/fair/licenses"
JUNK = {"rplots.pdf", ".rhistory", ".rdata", "thumbs.db", "desktop.ini"}
RAW_DIRS = {"raw", "raw_data", "rawdata", "grezzi", "sourcedata", "original"}
OUTPUT_DIRS = {"output", "outputs", "results", "risultati", "figures", "figure", "figs", "plots", "tables", "tabelle"}
MATERIAL_DIRS = {"materials", "materiali", "stimuli", "stimoli", "questionnaires", "questionari", "task", "experiment", "esperimento"}
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".tif", ".tiff", ".gif", ".eps"}
DESTINATIONS = ["data", "data/raw", "scripts", "output/figures", "output/tables", "materials", "docs", ".", "exclude"]


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


def propose(report):
    """A destination, a new name and a reason for every file of the project."""
    study = alnum(Path(report["project"]).name)
    manuscripts = {m["file"] for m in report.get("manuscripts", [])}
    sets = {}  # folder -> file set entry
    for t in report["data"]:
        if "file_set" in t:
            sets[t["file_set"].split("/*")[0]] = t
    data_files = [t["file"] for t in report["data"] if "file" in t and not any(p in RAW_DIRS for p in _parts(t["file"]))]
    rows, groups = [], {}
    for item in report["inventory"]:
        path = item["path"]
        p = PurePosixPath(path)
        name, ext, parts = p.name, p.suffix.lower(), _parts(path)
        folder = str(p.parent)
        row = {"path": path, "size_kb": item["size_kb"], "dest": "exclude", "name": safe_name(name), "reason": "", "kind": "other"}
        in_set = folder in sets and ext in (".csv", ".tsv")
        if name.lower() in JUNK:
            row.update(reason="file prodotto da R o dal sistema")
        elif re.match(r"(?i)^(readme|leggimi)", name):
            row.update(reason="sostituito dal README generato", kind="readme")
        elif re.match(r"(?i)^(licen[cs]e|copying)", name):
            row.update(reason="sostituito dal LICENSE generato", kind="license")
        elif DICT_NAME.search(p.stem) and ext in (".csv", ".tsv", ".docx", ".doc", ".pdf", ".xlsx", ".txt"):
            row.update(reason="il contenuto passa nel data dictionary qui sotto", kind="dictionary")
        elif any(VERSION_WORDS.search(x) for x in PurePosixPath(path).parts[:-1]):
            row.update(reason="in una cartella di versioni vecchie: includetelo solo se fa parte dell'analisi",
                       kind="code" if ext in CODE_EXT else "other")
        elif in_set:
            sub = PurePosixPath(*[x for x in PurePosixPath(folder).parts if x.lower() not in ("data", "dati") + tuple(RAW_DIRS)]) \
                if PurePosixPath(folder).parts else PurePosixPath("")
            row.update(dest="data/raw", name=str(sub / safe_name(name)) if str(sub) != "." else safe_name(name),
                       kind="set", set=folder)
            groups.setdefault(folder, []).append(path)
        elif ext in (".csv", ".tsv") and any(x in OUTPUT_DIRS for x in parts):
            row.update(dest="output/tables", kind="output")
        elif ext in (".csv", ".tsv") and any(x in RAW_DIRS for x in parts):
            row.update(dest="data/raw", kind="raw")
        elif ext in (".csv", ".tsv"):
            if PSYCHDS_NAME.match(name):
                new = name
            elif len(data_files) == 1:
                new = f"study-{study}_data.csv"
            else:
                new = f"study-{study}_description-{alnum(p.stem)}_data.csv"
            row.update(dest="data", name=new, kind="data")
        elif ext in PROPRIETARY_DATA:
            row.update(dest="exclude", kind="proprietary",
                       reason=f"formato {PROPRIETARY_DATA[ext]}: la pagina non può aprirlo per controllarlo. Se è l'export "
                              "originale e non contiene dati personali, mettetelo in data/raw; se i dati servono, salvatene "
                              "una copia CSV e caricate di nuovo la cartella")
        elif ext in CODE_EXT and path not in manuscripts:
            row.update(dest="scripts", kind="code")
        elif ext == ".rproj":
            row.update(dest=".", kind="rproj")
        elif path in manuscripts:
            row.update(dest="docs", kind="manuscript")
        elif ext in IMAGE_EXT or (ext == ".pdf" and any(x in OUTPUT_DIRS for x in parts)):
            row.update(dest="output/figures", kind="output")
        elif any(x in MATERIAL_DIRS for x in parts):
            row.update(dest="materials", kind="material",
                       reason="se è uno strumento di terzi (test pubblicati, stimoli con copyright) lasciatelo fuori")
        elif ext in (".pdf", ".docx", ".doc", ".odt", ".md", ".txt", ".html"):
            row.update(dest="docs", kind="doc")
        rows.append(row)
    return {"study": study, "files": rows, "sets": groups, "destinations": DESTINATIONS}


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
    """Dictionary drafts for the data files and file sets the researcher kept.

    files_json: [{"key": id, "paths": [project paths]}]. Values found in a
    dictionary already in the project are carried over."""
    root = Path(root)
    report = scan(root)
    existing = _existing_entries(root, report)
    out = {}
    for f in json.loads(files_json):
        try:
            rows = dd.draft([root / p for p in f["paths"]])
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
    return json.dumps({"report": report, "proposal": propose(report)}, ensure_ascii=False, default=str)


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
              (r"^decimal comma -> decimal point$", "virgola decimale sostituita dal punto"),
              (r"^columns removed: ", "colonne tolte: "), (r" -> UTF-8$", " convertito in UTF-8")]


def readme_text(form, plan, packages, data_changes, lic_parts, lang, data_info=None):
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
        if lang == "it":
            for pat, rep in CHANGES_IT:
                ch = [re.sub(pat, rep, c) for c in ch]
        changes.append(f"`{path}`: " + "; ".join(ch))
    if any(f["to"].startswith("scripts/") for f in renamed) or (renamed and scripts):
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
    report = bd.build_deposit(root, {"files": plan["files"], "data": plan.get("data", {})}, out)
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
    (outp / "README.md").write_text(readme_text(form, plan, pk, report["data_changes"], lic_parts, lang, info))

    final = scan(outp)
    todo = {str(p.relative_to(outp)): p.read_text(errors="replace").count("TODO")
            for p in [outp / "README.md", *sorted((outp / "dictionaries").glob("*.csv"))] if p.exists()}
    target, n = bd.zip_deposit(outp)
    return json.dumps({"build": report, "psychds_json": psy, "verify": final, "todo": todo, "zip": str(target), "n_files": n},
                      ensure_ascii=False, default=str)
