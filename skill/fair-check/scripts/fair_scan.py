#!/usr/bin/env python3
"""Read-only FAIR scan of a research project folder.

Usage: python3 fair_scan.py <project_folder> [--out report.json]

Prints a JSON report with: file inventory, naming problems, formats, folder
structure, README coverage, licenses, tabular data checks, data dictionary
coverage, code dependencies and portability problems.

The script never modifies the folder. It prints summaries of the data
(types, ranges, counts), not the rows themselves; columns that look like
personal data are reported without example values.
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(sys.maxsize)

SKIP_DIRS = {
    ".git", ".Rproj.user", ".quarto", "node_modules", "__pycache__",
    ".ipynb_checkpoints", ".venv", "venv", "env", ".mypy_cache", ".pytest_cache",
    ".idea", ".vscode", "renv/library", "renv/staging",
}
SKIP_FILES = {".DS_Store", "Thumbs.db", ".Rhistory", ".RData", ".Rapp.history"}

OPEN_TABULAR = {".csv", ".tsv"}
OPEN_TEXT = {".txt", ".json", ".md", ".yaml", ".yml", ".xml", ".cff", ".tex", ".bib", ".html"}
PROPRIETARY_DATA = {
    ".xlsx": "Excel", ".xls": "Excel", ".xlsm": "Excel", ".ods": "OpenDocument spreadsheet (open, but not plain text)",
    ".sav": "SPSS", ".zsav": "SPSS", ".por": "SPSS", ".dta": "Stata", ".sas7bdat": "SAS",
    ".mat": "MATLAB", ".rds": "R binary", ".rdata": "R binary", ".rda": "R binary",
    ".feather": "Arrow/Feather binary", ".parquet": "Parquet binary", ".pkl": "Python pickle",
    ".pickle": "Python pickle", ".h5": "HDF5", ".numbers": "Apple Numbers",
}
PROPRIETARY_DOCS = {".docx": "Word", ".doc": "Word", ".pptx": "PowerPoint", ".ppt": "PowerPoint", ".pages": "Apple Pages", ".odt": "OpenDocument text"}
CODE_EXT = {
    ".r": "R", ".rmd": "R Markdown", ".qmd": "Quarto", ".py": "Python", ".ipynb": "Jupyter",
    ".m": "MATLAB", ".sps": "SPSS syntax", ".do": "Stata", ".jl": "Julia", ".sh": "Shell",
    ".js": "JavaScript", ".psyexp": "PsychoPy", ".osexp": "OpenSesame", ".sas": "SAS",
}
ENV_FILES = ["renv.lock", "DESCRIPTION", "requirements.txt", "environment.yml", "environment.yaml",
             "pyproject.toml", "Pipfile", "Pipfile.lock", "poetry.lock", "setup.py", "Dockerfile",
             "install.R", "Project.toml", "sessionInfo.txt", "session_info.txt"]

VERSION_WORDS = re.compile(
    r"(?i)(?:^|[ _\-.(])(final[ei]?|def(?:initiv[oaie])?|nuov[oaie]|new|old|vecchi[oaie]?|copy|copia|"
    r"bozza|draft|ultim[oaie]|last|latest|ok|buon[oaie])(?=$|[ _\-.)0-9])"
)
DUPLICATE_MARK = re.compile(r"\(\d+\)|\s\d+$| - Copy| - Copia|_copy\b")
SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-]+$")

MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", ".", "-", "--", "?", "missing", "mancante", "#n/d", "#n/a", "nd"}
SENTINELS = {"-9", "-99", "-999", "-9999", "99", "999", "9999", "-1", "-77", "-88", "-98"}
BOOL_TOKENS = {"true", "false", "t", "f", "yes", "no", "y", "n", "si", "sì", "vero", "falso"}

PERSONAL_NAME_PATTERNS = [
    (r"(?i)^(first_?name|last_?name|surname|full_?name|nome|cognome|name|nominativo)$", "name"),
    (r"(?i)e_?mail|^mail$|posta", "e-mail"),
    (r"(?i)phone|telefono|cellulare|^tel$|mobile", "phone number"),
    (r"(?i)^ip$|ip_?address|ipaddress", "IP address"),
    (r"(?i)address|indirizzo|^via$|street|^cap$|zip_?code|postcode", "address"),
    (r"(?i)birth|nascita|^dob$|data_?di_?nascita|birthday", "birth date"),
    (r"(?i)codice_?fiscale|^cf$|fiscal|ssn|tax_?code", "tax / national ID"),
    (r"(?i)^(lat|latitude|lon|lng|longitude|location_?latitude|location_?longitude)$", "GPS coordinates"),
    (r"(?i)matricola|student_?id|badge", "institutional ID"),
    (r"(?i)prolific_?pid|mturk|worker_?id|workerid", "crowdsourcing worker ID"),
]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
CF_RE = re.compile(r"^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$", re.I)
PHONE_RE = re.compile(r"^\+?[\d\s\-]{9,15}$")
DATE_RE = re.compile(r"^(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})([ T]\d{1,2}:\d{2}(:\d{2})?)?$")

ID_LIKE = re.compile(r"(?i)(^id$|_id$|^id_|subj|participant|partecipante|soggetto|^sub$|^pp$|session)")
# columns that identify the participant (for grouping rows), not trials or sessions
PARTICIPANT_ID = re.compile(r"(?i)(^id$|^ids?_|_id$|subj|participant|partecipante|soggetto|^sub$|^pp$|^code$|^codice$|"
                            r"response_?id|record_?id|^uid$)")
# columns that describe the participant: one value per person, whatever the number of rows
PERSON_LEVEL = re.compile(r"(?i)^(age|eta|age_years|gender|sex|sesso|genere|education|istruzione|years_of_education|"
                          r"handedness|lateralita|group|gruppo|nationality|nazionalita|native_language|language|lingua|occupation)$")
SYNONYMS = {"eta": "age", "age_years": "age", "sesso": "sex", "genere": "gender", "gruppo": "group",
            "istruzione": "education", "lateralita": "handedness", "nazionalita": "nationality", "lingua": "language"}
DICT_NAME = re.compile(r"(?i)(dictionary|codebook|dizionario|data_?dict|variables|variabili|metadata)")
DICT_COLUMNS = ["variable_name", "label", "type", "unit", "allowed_values", "coding", "missing_values", "source", "notes"]
DICT_ALIASES = {
    "variable_name": ["variable_name", "variable", "var", "name", "column", "colonna", "variabile", "nome_variabile", "field"],
    "label": ["label", "description", "descrizione", "etichetta", "meaning", "significato"],
    "type": ["type", "tipo", "data_type", "datatype", "class"],
    "unit": ["unit", "units", "unita", "unità", "unit_of_measure"],
    "allowed_values": ["allowed_values", "range", "values", "valori", "valid_values", "levels"],
    "coding": ["coding", "codes", "codifica", "value_labels", "levels_labels"],
    "missing_values": ["missing_values", "missing", "na", "mancanti", "valori_mancanti"],
    "source": ["source", "fonte", "origin", "instrument", "strumento"],
    "notes": ["notes", "note", "comments", "commenti"],
}

R_BASE = {"base", "stats", "utils", "graphics", "grDevices", "methods", "datasets", "tools",
          "parallel", "grid", "splines", "stats4", "tcltk", "compiler"}

README_SECTIONS = {
    "title": None,  # checked separately: first heading / first line
    "authors_orcid": r"(?i)(author|autor|autrice|orcid|contact|contatt|corresponding|maintainer)",
    "description": r"(?i)(about|description|descrizione|overview|study|studio|abstract|panoramica|di cosa)",
    "contents": r"(?i)(contents?|contenut|files?\b|structure|struttura|organi[sz]|folder|cartell)",
    "how_to_read": r"(?i)(how to read|reading the data|come leggere|data format|formato dei dati|codebook|dictionary|dizionario)",
    "how_to_reproduce": r"(?i)(reproduc|riprodu|how to run|usage|utilizzo|requirements|requisiti|install|software|dependencies|dipendenze|renv|sessioninfo)",
    "license": r"(?i)(licen[sc]e|licenza)",
    "citation": r"(?i)(cit(e|ation|are|azione)|doi\.org|10\.\d{4,9}/)",
    "related_materials": r"(?i)(related|links?\b|collegat|preregistr|article|articolo|paper|publication|pubblicazion|preprint)",
    "provenance": r"(?i)(collected|raccolt|recruited|reclutat|participants|partecipanti|sample|campione|data collection|between .* and|fra .* e|tra .* e)",
}

LICENSE_SIGNATURES = [
    ("CC0-1.0", [r"CC0 1\.0", r"Creative Commons Legal Code\s+CC0", r"publicdomain/zero", r"\bCC0\b"]),
    ("CC-BY-NC-ND-4.0", [r"Attribution-NonCommercial-NoDerivatives", r"by-nc-nd/4", r"CC[ -]BY[ -]NC[ -]ND"]),
    ("CC-BY-NC-SA-4.0", [r"Attribution-NonCommercial-ShareAlike", r"by-nc-sa/4", r"CC[ -]BY[ -]NC[ -]SA"]),
    ("CC-BY-NC-4.0", [r"Attribution-NonCommercial 4\.0", r"licenses/by-nc/4", r"CC[ -]BY[ -]NC(?![ -](SA|ND))"]),
    ("CC-BY-ND-4.0", [r"Attribution-NoDerivatives 4\.0", r"licenses/by-nd/4", r"CC[ -]BY[ -]ND"]),
    ("CC-BY-SA-4.0", [r"Attribution-ShareAlike 4\.0", r"licenses/by-sa/4", r"CC[ -]BY[ -]SA"]),
    ("CC-BY-4.0", [r"Attribution 4\.0 International", r"licenses/by/4\.0", r"CC[ -]BY[ -]?4(\.0)?(?![ -]?(NC|SA|ND))", r"CC[ -]BY(?![ -]?(NC|SA|ND|-?\d))"]),
    ("AGPL-3.0", [r"GNU AFFERO GENERAL PUBLIC LICENSE", r"\bAGPL"]),
    ("LGPL-3.0", [r"GNU LESSER GENERAL PUBLIC LICENSE", r"\bLGPL"]),
    ("GPL-3.0", [r"GNU GENERAL PUBLIC LICENSE\s+Version 3", r"\bGPL[ -]?(v)?3", r"GPL-3\.0"]),
    ("GPL-2.0", [r"GNU GENERAL PUBLIC LICENSE\s+Version 2", r"\bGPL[ -]?(v)?2"]),
    ("MIT", [r"\bMIT License\b", r"Permission is hereby granted, free of charge", r"\bMIT\b"]),
    ("Apache-2.0", [r"Apache License,?\s+Version 2\.0", r"Apache[ -]2\.0"]),
    ("BSD", [r"Redistribution and use in source and binary forms", r"\bBSD[ -]?[023]"]),
    ("0BSD", [r"\b0BSD\b", r"Zero-Clause BSD"]),
    ("scientific-use-only", [r"(?i)scientific use file", r"(?i)scientific purposes only", r"(?i)uso scientifico"]),
]


def rel(p, root):
    return str(Path(p).relative_to(root))


def walk(root):
    files, dirs = [], []
    for dirpath, dirnames, filenames in os.walk(root):
        relp = os.path.relpath(dirpath, root)
        keep = []
        for d in sorted(dirnames):
            r = os.path.normpath(os.path.join(relp, d)) if relp != "." else d
            if d in SKIP_DIRS or r in SKIP_DIRS or d.startswith(".") and d not in {".github"}:
                continue
            keep.append(d)
            dirs.append(r)
        dirnames[:] = keep
        for f in sorted(filenames):
            if f in SKIP_FILES or f.startswith("~$") or f.startswith("._"):
                continue
            files.append(Path(dirpath) / f)
    return files, dirs


def name_problems(name, is_dir=False):
    probs = []
    stem = name if is_dir else Path(name).stem
    if " " in name:
        probs.append("spaces")
    if any(unicodedata.category(c).startswith("L") and ord(c) > 127 for c in name):
        probs.append("accented/non-ASCII letters")
    elif not SAFE_NAME.match(name.replace(" ", "_")):
        bad = sorted({c for c in name if not re.match(r"[A-Za-z0-9._\- ]", c)})
        probs.append("special characters " + "".join(bad))
    if VERSION_WORDS.search(stem):
        probs.append("manual versioning word (" + VERSION_WORDS.search(stem).group(1) + ")")
    if DUPLICATE_MARK.search(stem):
        probs.append("looks like a duplicate copy")
    return probs


def check_numbering(files, root):
    """Numbered files in the same folder without leading zeros."""
    by_dir = defaultdict(list)
    for f in files:
        m = re.match(r"^(\d+)[_\-. ]", f.name)
        if m:
            by_dir[f.parent].append((m.group(1), f.name))
    out = []
    for d, items in by_dir.items():
        widths = {len(n) for n, _ in items}
        if len(items) >= 2 and (len(widths) > 1 or (widths == {1} and len(items) >= 2)):
            out.append({"folder": rel(d, root) if d != root else ".",
                        "files": [n for _, n in sorted(items)],
                        "problem": "numbers without leading zeros (use 01_, 02_ ...)"})
    return out


# ---------------------------------------------------------------- tabular data

def read_table(path):
    raw = path.read_bytes()
    info = {"encoding": None, "bom": raw.startswith(b"\xef\xbb\xbf")}
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            info["encoding"] = "utf-8" if enc == "utf-8-sig" else enc
            break
        except UnicodeDecodeError:
            continue
    if "\r\n" in text[:5000]:
        info["line_endings"] = "CRLF"
    sample = text[:20000]
    first_line = sample.split("\n", 1)[0]
    if path.suffix.lower() == ".tsv":
        delim = "\t"
    else:
        counts = {d: first_line.count(d) for d in [",", ";", "\t", "|"]}
        delim = max(counts, key=counts.get) if max(counts.values()) > 0 else ","
    info["delimiter"] = {",": "comma", ";": "semicolon", "\t": "tab", "|": "pipe"}[delim]
    rows = list(csv.reader(text.splitlines(), delimiter=delim))
    return rows, info


def to_number(v, decimal_comma=False):
    s = v.strip()
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".") if re.match(r"^-?\d{1,3}(\.\d{3})*(,\d+)?$", s) else s.replace(",", ".")
    try:
        x = float(s)
        if x != x:  # nan
            return None
        return x
    except ValueError:
        return None


def infer_column(name, values, decimal_comma):
    n = len(values)
    stripped = [v.strip() for v in values]
    missing = Counter(v for v in stripped if v.lower() in MISSING_TOKENS)
    present = [v for v in stripped if v.lower() not in MISSING_TOKENS]
    col = {"name": name, "n_missing": sum(missing.values()),
           "missing_tokens": {(k if k else "<empty>"): c for k, c in missing.items()}}
    issues = []
    if len(missing) > 1:
        issues.append("missing values coded in more than one way: " + ", ".join(col["missing_tokens"]))
    ws = sum(1 for v in values if v != v.strip() and v.strip())
    if ws:
        issues.append(f"{ws} values with leading/trailing spaces")
    if not present:
        col["type"] = "empty"
        issues.append("column is entirely empty")
        col["issues"] = issues
        return col

    nums = [to_number(v, decimal_comma) for v in present]
    num_ok = [x for x in nums if x is not None]
    lower = [v.lower() for v in present]
    uniq = Counter(present)
    col["n_unique"] = len(uniq)

    if all(l in BOOL_TOKENS for l in lower) and len(set(lower)) <= 2:
        col["type"] = "boolean"
        col["values"] = sorted(uniq)
    elif len(num_ok) == len(present):
        col["type"] = "integer" if all(float(x).is_integer() for x in num_ok) else "numeric"
        col["min"], col["max"] = min(num_ok), max(num_ok)
        if col["type"] == "integer":
            col["min"], col["max"] = int(col["min"]), int(col["max"])
        sent = {v: c for v, c in uniq.items() if v in SENTINELS}
        if sent and len(uniq) > 3:
            vals_wo = [x for x, v in zip(nums, present) if v not in SENTINELS and x is not None]
            if vals_wo and any(abs(float(s)) > 3 * max(abs(min(vals_wo)), abs(max(vals_wo)), 1) or float(s) < 0 <= min(vals_wo) for s in sent):
                issues.append("possible numeric missing-value codes: " + ", ".join(f"{k} (x{c})" for k, c in sent.items()))
        if col["type"] == "integer" and len(uniq) <= 10:
            col["values"] = sorted(uniq, key=lambda s: float(to_number(s, decimal_comma)))
        if not decimal_comma and any("," in v for v in present):
            issues.append("decimal comma inside a comma-delimited file")
    elif len(num_ok) >= 0.8 * len(present):
        col["type"] = "mixed"
        bad = Counter(v for v, x in zip(present, nums) if x is None)
        issues.append("mostly numeric but contains text: " + ", ".join(f"'{k}' (x{c})" for k, c in bad.most_common(5)))
    elif all(DATE_RE.match(v) for v in present):
        col["type"] = "date"
        formats = {re.sub(r"\d", "9", v) for v in present}
        if len(formats) > 1:
            issues.append("dates written in more than one format: " + ", ".join(sorted(formats)[:4]))
    else:
        col["type"] = "categorical" if len(uniq) <= max(12, 0.05 * n) else "string"
        if col["type"] == "categorical":
            col["values"] = sorted(uniq)
            folded = defaultdict(set)
            for v in uniq:
                folded[v.lower().strip()].add(v)
            clash = [sorted(s) for s in folded.values() if len(s) > 1]
            if clash:
                issues.append("same category written differently: " + "; ".join(" / ".join(c) for c in clash))
    if len(uniq) == 1 and n > 1 and not ID_LIKE.search(name):
        issues.append("constant column (one value only)")
    col["issues"] = issues
    return col


def personal_flags(name, values):
    flags = []
    for pat, label in PERSONAL_NAME_PATTERNS:
        if re.search(pat, name):
            flags.append(f"column name suggests {label}")
            break
    vals = [v.strip() for v in values if v.strip()][:2000]
    if vals:
        if sum(bool(EMAIL_RE.match(v)) for v in vals) > 0.3 * len(vals):
            flags.append("values look like e-mail addresses")
        if sum(bool(CF_RE.match(v)) for v in vals) > 0.3 * len(vals):
            flags.append("values look like Italian tax codes (codice fiscale)")
        if sum(bool(PHONE_RE.match(v)) and len(re.sub(r"\D", "", v)) >= 9 for v in vals) > 0.5 * len(vals) and not re.search(r"(?i)(rt|time|ms|id|code)", name):
            flags.append("values look like phone numbers")
    return flags


def canon_name(name):
    folded = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    n = re.sub(r"[^a-z0-9]+", "_", folded.strip().lower()).strip("_")
    return SYNONYMS.get(n, n)


def is_missing(v):
    return v.strip().lower() in MISSING_TOKENS


def participant_values(header, body, cols, privacy_cols):
    """Group participant-level columns by participant ID.

    Returns (id_column, {id: {column: set(values)}}, list of within-participant problems).
    A column counts as participant-level when its name says so (age, sex, group, ...)
    or when it has more than two values and is constant for at least 80% of the
    participants with two or more rows: then the remaining ones are likely errors.
    """
    idx = next((j for j, h in enumerate(header) if PARTICIPANT_ID.search(h.strip()) and h not in privacy_cols), None)
    if idx is None:
        return None, {}, []
    groups = defaultdict(lambda: defaultdict(set))
    for r in body:
        pid = r[idx].strip() if idx < len(r) else ""
        if not pid or is_missing(pid):
            continue
        for j, h in enumerate(header):
            if j != idx and j < len(r) and not is_missing(r[j]):
                groups[pid][h].add(r[j].strip())
    problems, person_cols = [], []
    n_rows = Counter(r[idx].strip() for r in body if idx < len(r))
    multi = [pid for pid in groups if n_rows[pid] > 1]
    for j, h in enumerate(header):
        if j == idx or h in privacy_cols:
            continue
        col = cols[j]
        varying = [pid for pid in multi if len(groups[pid].get(h, ())) > 1]
        named = bool(PERSON_LEVEL.match(canon_name(h)))
        generic = (col.get("n_unique", 0) > 2 and len(multi) >= 5 and 0 < len(varying) <= 0.2 * len(multi))
        if named or generic or not varying and multi:
            person_cols.append(h)
        if varying and (named or generic):
            ex = "; ".join(f"{pid}: {' / '.join(sorted(groups[pid][h]))}" for pid in varying[:5])
            problems.append(f"'{h}' should have one value per participant but has more for "
                            f"{len(varying)} of {len(multi)} participants ({ex})")
    by_id = {pid: {h: v for h, v in g.items() if h in person_cols} for pid, g in groups.items()}
    return header[idx], by_id, problems


def scan_table(path, root):
    try:
        rows, info = read_table(path)
    except Exception as e:  # noqa: BLE001
        return {"file": rel(path, root), "error": f"could not read: {e}"}
    res = {"file": rel(path, root), **info}
    rows = [r for r in rows if any(c.strip() for c in r)] if rows else rows
    if not rows:
        res["error"] = "empty file"
        return res
    header = rows[0]
    body = rows[1:]
    res["n_rows"], res["n_cols"] = len(body), len(header)
    issues = []
    ragged = [i + 2 for i, r in enumerate(body) if len(r) != len(header)]
    if ragged:
        issues.append(f"{len(ragged)} rows with a different number of fields than the header (first lines: {ragged[:5]})")
    hdr_issues = []
    for i, h in enumerate(header):
        if not h.strip():
            hdr_issues.append(f"column {i + 1} has no name")
        else:
            p = [x for x in name_problems(h.strip(), is_dir=True) if not x.startswith("manual") and not x.startswith("looks like")]
            if p:
                hdr_issues.append(f"'{h}': {', '.join(p)}")
            if re.match(r"^\d", h.strip()):
                hdr_issues.append(f"'{h}': starts with a digit")
    dups = [h for h, c in Counter(header).items() if c > 1 and h.strip()]
    if dups:
        hdr_issues.append("duplicated column names: " + ", ".join(dups))
    if all(to_number(h) is not None for h in header if h.strip()):
        hdr_issues.append("the first row looks like data, not column names (no header?)")
    if hdr_issues:
        res["header_issues"] = hdr_issues
    tuples = [tuple(r) for r in body]
    dupe_rows = sum(c - 1 for c in Counter(tuples).values() if c > 1)
    if dupe_rows:
        issues.append(f"{dupe_rows} exact duplicate rows")
    decimal_comma = info["delimiter"] == "semicolon" and any(re.match(r"^-?\d+,\d+$", c.strip()) for r in body[:500] for c in r)
    if decimal_comma:
        res["decimal_comma"] = True
    cols = []
    privacy = []
    for j, h in enumerate(header):
        vals = [r[j] if j < len(r) else "" for r in body]
        c = infer_column(h, vals, decimal_comma)
        pf = personal_flags(h, vals)
        if pf:
            privacy.append({"column": h, "flags": pf})
            c.pop("values", None)  # do not echo possibly identifying values
            c.pop("min", None)
            c.pop("max", None)
        cols.append(c)
    res["columns"] = cols
    if privacy:
        res["possible_personal_data"] = privacy
    id_col, by_id, within = participant_values(header, body, cols, {p["column"] for p in privacy})
    if id_col:
        res["participant_id_column"] = id_col
        res["n_participants"] = len(by_id)
        res["_by_id"] = by_id  # used for the cross-file comparison, removed before output
    if within:
        res["within_participant_inconsistencies"] = within
    res["issues"] = issues
    return res


def compare_participants(tables):
    """For each pair of files with a participant ID: which IDs are only in one of
    them, and whether shared participant-level columns (age, sex, ...) agree."""
    out = []
    with_ids = [t for t in tables if t.get("_by_id")]
    for i, a in enumerate(with_ids):
        for b in with_ids[i + 1:]:
            ida, idb = set(a["_by_id"]), set(b["_by_id"])
            key = {"a": lambda v: v, "b": lambda v: v}
            note = None
            if not ida & idb:
                # same participants written differently? ('sub-01' vs '1')
                def digits(v):
                    d = re.sub(r"\D", "", v).lstrip("0")
                    return d or v
                if {digits(v) for v in ida} & {digits(v) for v in idb}:
                    key = {"a": digits, "b": digits}
                    note = "IDs match only after removing prefixes and leading zeros: write them the same way in every file"
                else:
                    continue  # no participants in common: probably unrelated tables
            ma = {key["a"](k): k for k in ida}
            mb = {key["b"](k): k for k in idb}
            entry = {"files": [a["file"], b["file"]],
                     "id_columns": [a["participant_id_column"], b["participant_id_column"]],
                     "only_in_first": sorted(ma[k] for k in set(ma) - set(mb))[:15],
                     "only_in_second": sorted(mb[k] for k in set(mb) - set(ma))[:15]}
            if a["participant_id_column"] != b["participant_id_column"]:
                entry["note_names"] = "the same ID column has different names in the two files"
            if note:
                entry["note_format"] = note
            # shared participant-level columns
            cols_a = {canon_name(h): h for g in a["_by_id"].values() for h in g}
            cols_b = {canon_name(h): h for g in b["_by_id"].values() for h in g}
            disagreements = []
            for cn in sorted(set(cols_a) & set(cols_b)):
                ha, hb = cols_a[cn], cols_b[cn]
                bad = []
                for k in sorted(set(ma) & set(mb)):
                    va = {v.lower() for v in a["_by_id"][ma[k]].get(ha, set())}
                    vb = {v.lower() for v in b["_by_id"][mb[k]].get(hb, set())}
                    na = {to_number(v) for v in va} if all(to_number(v) is not None for v in va) else va
                    nb = {to_number(v) for v in vb} if all(to_number(v) is not None for v in vb) else vb
                    if va and vb and na != nb:
                        bad.append(f"{ma[k]}: {' / '.join(sorted(va))} vs {' / '.join(sorted(vb))}")
                if bad:
                    disagreements.append({"columns": [ha, hb], "n_participants": len(bad), "examples": bad[:6]})
            if disagreements:
                entry["values_disagree"] = disagreements
            if entry["only_in_first"] or entry["only_in_second"] or disagreements or note or "note_names" in entry:
                out.append(entry)
    return out


def group_file_sets(tables):
    """Files with the same columns in the same folder (e.g. one PsychoPy file per
    participant) are one dataset: check them together, report them once.

    Returns (tables to use for the cross-file and dictionary checks, entries for
    the report)."""
    sets = defaultdict(list)
    for t in tables:
        if "columns" in t:
            sets[(str(Path(t["file"]).parent), tuple(c["name"] for c in t["columns"]))].append(t)
    for_checks, for_report = [], []
    for (parent, header), ts in sets.items():
        if len(ts) < 3:
            for_checks += ts
            for_report += ts
            continue
        ext = Path(ts[0]["file"]).suffix
        name = f"{parent}/*{ext} ({len(ts)} files with the same columns)"
        merged = defaultdict(dict)
        for t in ts:
            for pid, cols in t.get("_by_id", {}).items():
                for h, v in cols.items():
                    merged[pid].setdefault(h, set()).update(v)
        rep = {"file": name, "columns": ts[0]["columns"], "participant_id_column": ts[0].get("participant_id_column"),
               "_by_id": dict(merged)}
        for_checks.append(rep)
        per_file = {}
        for t in ts:
            found = t.get("header_issues", []) + t.get("issues", []) + t.get("within_participant_inconsistencies", []) + \
                [f"{c['name']}: {i}" for c in t["columns"] for i in c.get("issues", []) if not i.startswith("constant column")]
            if found:
                per_file[Path(t["file"]).name] = found
        types = defaultdict(set)
        for t in ts:
            for c in t["columns"]:
                types[c["name"]].add(c.get("type"))
        for_report.append({
            "file_set": name, "n_files": len(ts), "n_rows_total": sum(t.get("n_rows", 0) for t in ts),
            "participant_id_column": rep["participant_id_column"], "n_participants": len(merged),
            "columns": [{"name": h, "types": sorted(x for x in types[h] if x)} for h in header],
            "issues_by_file": per_file,
            "possible_personal_data": sorted({p["column"] for t in ts for p in t.get("possible_personal_data", [])})})
    for_checks += [t for t in tables if "columns" not in t]
    for_report += [t for t in tables if "columns" not in t]
    return for_checks, for_report  # "_by_id" is removed in main() after the cross-file check


# --------------------------------------------------------------- dictionaries

def norm(s):
    return re.sub(r"[^a-z0-9]", "_", s.strip().lower()).strip("_")


def parse_dictionary(path, root):
    rows, info = read_table(path)
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        return {"file": rel(path, root), "error": "empty"}
    header = [norm(h) for h in rows[0]]
    mapping = {}
    for std, aliases in DICT_ALIASES.items():
        for a in aliases:
            if norm(a) in header:
                mapping[std] = header.index(norm(a))
                break
    entries = {}
    if "variable_name" in mapping:
        for r in rows[1:]:
            k = mapping["variable_name"]
            if k < len(r) and r[k].strip():
                entries[r[k].strip()] = {std: (r[i].strip() if i < len(r) else "") for std, i in mapping.items()}
    return {"file": rel(path, root), "columns_present": [s for s in DICT_COLUMNS if s in mapping],
            "columns_missing": [s for s in DICT_COLUMNS if s not in mapping], "entries": entries}


def parse_codes(coding):
    """'1 = Psychology; 2 = Economics' -> {'1','2'}"""
    codes = set()
    for part in re.split(r"[;|\n]", coding):
        m = re.match(r"\s*([^=:]+?)\s*[=:]", part)
        if m:
            codes.add(m.group(1).strip())
    return codes


def compare_dictionary(table, dic):
    out = {"dictionary": dic["file"]}
    data_cols = [c["name"] for c in table.get("columns", [])]
    entries = dic.get("entries", {})
    out["data_columns_not_in_dictionary"] = [c for c in data_cols if c not in entries]
    out["dictionary_entries_not_in_data"] = [e for e in entries if e not in data_cols]
    near = []
    for c in out["data_columns_not_in_dictionary"]:
        for e in out["dictionary_entries_not_in_data"]:
            if norm(c) == norm(e):
                near.append(f"data '{c}' vs dictionary '{e}' (differ only in case/spacing)")
    if near:
        out["name_mismatches"] = near
    problems = []
    for col in table.get("columns", []):
        e = entries.get(col["name"])
        if not e:
            continue
        if not e.get("label"):
            problems.append(f"{col['name']}: no label")
        declared = (e.get("type") or "").lower()
        if declared not in ("string", "date", "numeric") and (
                col.get("type") in ("categorical", "boolean") or (col.get("type") == "integer" and col.get("values") and len(col["values"]) <= 6)):
            if "coding" in e and not e["coding"] and not e.get("allowed_values"):
                problems.append(f"{col['name']}: categorical-looking column without coding")
            codes = parse_codes(e.get("coding", ""))
            rng = re.match(r"^\s*(-?[\d.]+)\s*(?:-|–|to)\s*(-?[\d.]+)\s*$", e.get("allowed_values", ""))
            if rng and "min" in col and float(rng.group(1)) <= col["min"] and col["max"] <= float(rng.group(2)):
                codes = set()  # a scale: the coding labels its anchors, the range covers the values
            if codes and col.get("values"):
                extra = [v for v in col["values"] if v not in codes]
                if extra:
                    problems.append(f"{col['name']}: values in data not described in coding: {extra[:8]}")
        av = e.get("allowed_values", "")
        m = re.match(r"^\s*(-?[\d.]+)\s*(?:-|–|to|a|:)\s*(-?[\d.]+)\s*$", av)
        if m and "min" in col:
            lo, hi = float(m.group(1)), float(m.group(2))
            declared_missing = {to_number(x) for x in re.split(r"[;,|]", e.get("missing_values", "")) if to_number(x) is not None}
            if (col["min"] < lo and col["min"] not in declared_missing) or (col["max"] > hi and col["max"] not in declared_missing):
                problems.append(f"{col['name']}: data range {col['min']}–{col['max']} outside allowed_values {av}")
        if col.get("n_missing") and "missing_values" in e and not e["missing_values"]:
            problems.append(f"{col['name']}: has {col['n_missing']} missing values but missing_values is empty")
    out["entry_problems"] = problems
    return out


# ----------------------------------------------------------------------- code

def scan_code(path, root, all_files_rel):
    text = path.read_text(errors="replace")
    ext = path.suffix.lower()
    lang = CODE_EXT.get(ext, "?")
    res = {"file": rel(path, root), "language": lang, "lines": text.count("\n") + 1}
    if ext == ".ipynb":
        try:
            nb = json.loads(text)
            text = "\n".join("".join(c.get("source", [])) for c in nb.get("cells", []) if c.get("cell_type") == "code")
            kern = nb.get("metadata", {}).get("kernelspec", {}).get("language", "python")
            lang = "R" if kern.lower() == "r" else "Python"
            res["language"] = f"Jupyter ({lang})"
        except Exception:  # noqa: BLE001
            pass
    code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#") or ext in (".py", ".ipynb") and l.lstrip().startswith("#!"))
    pkgs = set()
    if lang in ("R", "R Markdown", "Quarto") or res["language"] == "Jupyter (R)":
        for m in re.finditer(r"\b(?:library|require|requireNamespace)\s*\(\s*[\"']?([A-Za-z][A-Za-z0-9.]*)", code):
            pkgs.add(m.group(1))
        for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9.]*)::", code):
            pkgs.add(m.group(1))
        for m in re.finditer(r"p_load\s*\(([^)]*)\)", code):
            for p in re.split(r"[,\s]+", m.group(1)):
                p = p.strip("\"' ")
                if re.match(r"^[A-Za-z][A-Za-z0-9.]*$", p) and "=" not in p:
                    pkgs.add(p)
        pkgs -= R_BASE
        if ext == ".rmd" or ext == ".qmd":
            pkgs.add("rmarkdown" if ext == ".rmd" else "knitr")
    elif lang in ("Python",) or res["language"] == "Jupyter (Python)":
        std = set(getattr(sys, "stdlib_module_names", ()))
        local = {Path(f).stem for f in all_files_rel if f.endswith(".py")}
        for m in re.finditer(r"^\s*(?:import\s+([\w.]+(?:\s*,\s*[\w.]+)*)|from\s+([\w.]+)\s+import)", code, re.M):
            names = (m.group(1) or m.group(2)).split(",")
            for nme in names:
                top = nme.strip().split(".")[0].split(" as ")[0].strip()
                if top and top not in std and top not in local:
                    pkgs.add(top)
    res["packages"] = sorted(pkgs)
    issues = []
    for m in re.finditer(r"setwd\s*\(([^)]*)\)", code):
        issues.append(f"setwd({m.group(1).strip()}) — ties the script to one computer")
    abs_paths = set(re.findall(r"[\"']((?:[A-Za-z]:[\\/]|/Users/|/home/|~/|\\\\[A-Za-z])[^\"']*)[\"']", code))
    for p in sorted(abs_paths)[:10]:
        issues.append(f"absolute path '{p}'")
    if re.search(r"rm\s*\(\s*list\s*=\s*ls\s*\(", code):
        issues.append("rm(list = ls()) — does not give a clean session; restart R instead")
    if re.search(r"install\.packages\s*\(|pip install|!pip", code):
        issues.append("installs packages inside the script")
    # files the script writes (so a later script reading them is not a "missing file")
    res["writes"] = sorted({Path(m.group(1)).name for m in re.finditer(
        r"(?:write[._]\w*|to_csv|to_excel|saveRDS|save|ggsave|fwrite|sink|savefig|png|pdf|jpeg)\s*\([^)]*?[\"']([^\"'\n]+\.\w+)[\"']", code)})
    # file references that do not exist
    missing = []
    for m in re.finditer(r"[\"']([^\"'\n]+\.(?:csv|tsv|txt|xlsx|xls|sav|rds|RData|rda|json|dta|mat|feather|parquet))[\"']", code):
        ref = m.group(1)
        if re.match(r"^(?:[A-Za-z]:[\\/]|/|~|https?:)", ref) or "*" in ref or "%" in ref or "{" in ref:
            continue
        cand = [root / ref, path.parent / ref, root / ref.lstrip("./")]
        # a bare file name may be one piece of here("data", "x.csv") or file.path(...)
        if "/" not in ref and any(Path(f).name == ref for f in all_files_rel):
            continue
        if not any(c.exists() for c in cand):
            missing.append(ref)
    if missing:
        res["referenced_files_not_found"] = sorted(set(missing))[:20]
    res["issues"] = issues
    res["uses_here"] = bool(re.search(r"\bhere\s*::\s*here|library\s*\(\s*here\s*\)", code))
    res["sets_seed"] = bool(re.search(r"set\.seed|np\.random\.seed|random\.seed|default_rng\(\s*\d", code))
    res["random_calls"] = bool(re.search(r"\b(sample|rnorm|runif|rbinom|brm|stan|sampling|bootstrap|boot)\s*\(|np\.random|random\.", code))
    return res


def parse_env(root):
    env = {}
    p = root / "renv.lock"
    if p.exists():
        try:
            lock = json.loads(p.read_text())
            env["renv.lock"] = {"R": lock.get("R", {}).get("Version"), "packages": sorted(lock.get("Packages", {}))}
        except Exception as e:  # noqa: BLE001
            env["renv.lock"] = {"error": str(e)}
    p = root / "requirements.txt"
    if p.exists():
        env["requirements.txt"] = [re.split(r"[<>=!~\[; ]", l.strip())[0] for l in p.read_text().splitlines() if l.strip() and not l.startswith("#")]
    for name in ("environment.yml", "environment.yaml", "DESCRIPTION", "pyproject.toml", "sessionInfo.txt", "session_info.txt"):
        if (root / name).exists():
            env[name] = "present"
    return env


# -------------------------------------------------------- manuscript, psych-ds

MANUSCRIPT_NAME = re.compile(r"(?i)(manuscript|manoscritto|paper|preprint|article|articolo|draft|submission|thesis|tesi)")
MANUSCRIPT_EXT = {".pdf", ".docx", ".doc", ".odt", ".md", ".qmd", ".rmd", ".tex", ".html"}
PSYCHDS_NAME = re.compile(r"^([a-z]+-[a-zA-Z0-9]+_)+data\.csv$")


def find_manuscripts(root, files):
    out = []
    for f in files:
        r = rel(f, root)
        if f.suffix.lower() not in MANUSCRIPT_EXT or re.match(r"(?i)^(readme|leggimi|licen[cs]e|changelog)", f.name):
            continue
        in_docs = any(p.lower() in {"docs", "doc", "manuscript", "manoscritto", "paper", "preprint", "article", "articolo"}
                      for p in Path(r).parts[:-1])
        if in_docs or MANUSCRIPT_NAME.search(f.stem):
            out.append({"file": r, "format": f.suffix.lower(), "size_kb": round(f.stat().st_size / 1024, 1)})
    return out


def psychds_check(root, tables):
    """The minimum rules of Psych-DS, as listed on the booklet's page."""
    res = {"data_dir": (root / "data").is_dir(), "problems": []}
    dd = root / "dataset_description.json"
    if not dd.exists():
        res["problems"].append("no dataset_description.json in the root")
        meta = None
    else:
        try:
            meta = json.loads(dd.read_text())
        except json.JSONDecodeError as e:
            res["problems"].append(f"dataset_description.json is not valid JSON: {e}")
            meta = None
    if (root / "data" / "dataset_description.json").exists():
        res["problems"].append("dataset_description.json is inside data/: it must be in the root")
    in_data = [t for t in tables if t["file"].startswith("data/") and not t["file"].startswith("data/raw/")]
    bad_names = [t["file"] for t in in_data if not PSYCHDS_NAME.match(Path(t["file"]).name)]
    if bad_names:
        res["problems"].append("files in data/ not named key-value_..._data.csv: " + ", ".join(bad_names))
    if not res["data_dir"]:
        res["problems"].append("no data/ folder in the root")
    if meta is not None:
        for req in ("name", "description", "variableMeasured"):
            if not meta.get(req):
                res["problems"].append(f"dataset_description.json: required field '{req}' missing or empty")
        declared = {v if isinstance(v, str) else v.get("name") for v in meta.get("variableMeasured", [])}
        cols = {c["name"] for t in in_data if PSYCHDS_NAME.match(Path(t["file"]).name) for c in t.get("columns", [])}
        if cols - declared:
            res["problems"].append("columns not in variableMeasured: " + ", ".join(sorted(cols - declared)))
        if declared - cols and cols:
            res["problems"].append("variableMeasured entries that are not columns of any data file: " + ", ".join(sorted(declared - cols)))
        res["n_variables_described"] = sum(1 for v in meta.get("variableMeasured", []) if isinstance(v, dict) and v.get("description"))
    res["valid_minimum"] = not res["problems"]
    return res


# --------------------------------------------------------------------- readme

def find_readme(root):
    for f in sorted(root.iterdir()):
        if f.is_file() and re.match(r"(?i)^(readme|leggimi)(\.(md|txt|rst|markdown|html|pdf|docx))?$", f.name):
            return f
    return None


def scan_readme(path, root, files_rel):
    res = {"file": rel(path, root), "format": path.suffix.lower() or "(none)"}
    if path.suffix.lower() in (".pdf", ".docx", ".html"):
        res["issues"] = [f"README in {path.suffix} — use Markdown or plain text"]
        return res
    text = path.read_text(errors="replace")
    res["n_words"] = len(text.split())
    lines = [l for l in text.splitlines() if l.strip()]
    res["first_line"] = lines[0][:120] if lines else ""
    headings = [l.strip("# ").strip() for l in text.splitlines() if re.match(r"^#{1,6}\s", l)]
    res["headings"] = headings[:40]
    found = {}
    for sec, pat in README_SECTIONS.items():
        if pat is None:
            found[sec] = bool(lines)
            continue
        in_head = any(re.search(pat, h) for h in headings)
        in_text = bool(re.search(pat, text))
        found[sec] = "heading" if in_head else ("mentioned" if in_text else False)
    res["sections"] = found
    res["orcid_ids"] = re.findall(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", text)
    res["dois"] = sorted(set(re.findall(r"10\.\d{4,9}/[^\s)\]>\"']+", text)))[:10]
    res["placeholders"] = sorted(set(re.findall(r"(?i)(TODO|TBD|XXXX+|lorem ipsum|\[insert[^\]]*\])", text)))
    mentioned, not_mentioned = [], []
    for f in files_rel:
        if Path(f).name.lower().startswith(("readme", "leggimi")):
            continue
        if Path(f).name in text or f in text or Path(f).stem in text:
            mentioned.append(f)
        else:
            parent = str(Path(f).parent)
            if parent != "." and (parent + "/" in text or parent + "\\" in text or
                                  (Path(parent).name not in ("data", "raw", "scripts", "code") and Path(parent).name + "/" in text)):
                mentioned.append(f)
            else:
                not_mentioned.append(f)
    res["files_mentioned"] = len(mentioned)
    res["files_not_mentioned"] = not_mentioned[:60]
    return res


# -------------------------------------------------------------------- license

def detect_licenses(text):
    found = []
    for spdx, pats in LICENSE_SIGNATURES:
        for p in pats:
            if re.search(p, text):
                if spdx == "GPL-3.0" and ("AGPL-3.0" in found or "LGPL-3.0" in found) and not re.search(r"(?<![AL])GPL", text):
                    break
                if spdx.startswith("CC-BY") and any(f.startswith("CC-BY") and f != spdx and len(f) > len(spdx) for f in found) and not re.search(pats[0], text):
                    break
                found.append(spdx)
                break
    return found


def scan_licenses(root, files):
    out = {"files": []}
    for f in files:
        if re.match(r"(?i)^(licen[cs]e|copying|copyright)", f.name):
            txt = f.read_text(errors="replace")[:200000]
            out["files"].append({"file": rel(f, root), "detected": detect_licenses(txt),
                                 "n_chars": len(txt),
                                 "looks_like_full_text": len(txt) > 900})
    return out


# ----------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--out")
    args = ap.parse_args()
    root = Path(args.folder).expanduser().resolve()
    if not root.is_dir():
        sys.exit(f"Not a folder: {root}")

    files, dirs = walk(root)
    files_rel = [rel(f, root) for f in files]
    report = {"project": str(root), "n_files": len(files), "n_dirs": len(dirs)}

    # inventory
    inv = []
    total = 0
    for f in files:
        size = f.stat().st_size
        total += size
        inv.append({"path": rel(f, root), "size_kb": round(size / 1024, 1)})
    report["total_size_mb"] = round(total / 1e6, 2)
    report["inventory"] = inv[:400]
    if len(inv) > 400:
        report["inventory_truncated"] = len(inv)
    report["root_entries"] = sorted(p.name + ("/" if p.is_dir() else "") for p in root.iterdir()
                                    if not p.name.startswith(".") and p.name not in SKIP_FILES)

    # naming
    naming = []
    for d in dirs:
        p = name_problems(Path(d).name, is_dir=True)
        if p:
            naming.append({"path": d + "/", "problems": p})
    for f in files:
        p = name_problems(f.name)
        if p:
            naming.append({"path": rel(f, root), "problems": p})
    report["naming"] = {"problems": naming, "numbering": check_numbering(files, root)}

    # formats
    fmt = {"proprietary_data": [], "proprietary_docs": [], "open_tabular": [], "other_binary": []}
    stems_open = {(f.parent, f.stem.lower()) for f in files if f.suffix.lower() in OPEN_TABULAR}
    stems_open_any = {f.stem.lower() for f in files if f.suffix.lower() in OPEN_TABULAR}
    for f in files:
        ext = f.suffix.lower()
        r = rel(f, root)
        if ext in PROPRIETARY_DATA:
            fmt["proprietary_data"].append({"file": r, "format": PROPRIETARY_DATA[ext],
                                            "open_copy_exists": (f.parent, f.stem.lower()) in stems_open or f.stem.lower() in stems_open_any,
                                            "in_raw_folder": "raw" in [p.lower() for p in Path(r).parts[:-1]]})
        elif ext in PROPRIETARY_DOCS:
            fmt["proprietary_docs"].append({"file": r, "format": PROPRIETARY_DOCS[ext]})
        elif ext in OPEN_TABULAR:
            fmt["open_tabular"].append(r)
    report["formats"] = fmt

    # structure
    lower_dirs = {d.lower() for d in dirs}
    top_dirs = {d.lower() for d in dirs if "/" not in d and os.sep not in d}
    report["structure"] = {
        "readme": bool(find_readme(root)),
        "license_file": any(re.match(r"(?i)^(licen[cs]e|copying)", f.name) for f in files if f.parent == root),
        "citation_cff": (root / "CITATION.cff").exists(),
        "rproj": [rel(f, root) for f in files if f.suffix.lower() == ".rproj"],
        "dataset_description_json": (root / "dataset_description.json").exists(),
        "data_dir": sorted(d for d in top_dirs if d in {"data", "dati", "dataset", "datasets"}),
        "raw_dir": sorted(d for d in lower_dirs if Path(d).name in {"raw", "raw_data", "rawdata", "grezzi", "sourcedata", "original"}),
        "code_dir": sorted(d for d in top_dirs if d in {"scripts", "script", "code", "codice", "analysis", "analyses", "analisi", "r", "src", "notebooks"}),
        "output_dir": sorted(d for d in top_dirs if d in {"output", "outputs", "results", "risultati", "figures", "figure", "plots", "tables"}),
        "materials_dir": sorted(d for d in top_dirs if d in {"materials", "materiali", "stimuli", "stimoli", "questionnaires", "questionari", "task", "experiment", "esperimento"}),
        "docs_dir": sorted(d for d in top_dirs if d in {"docs", "doc", "documents", "documenti", "manuscript", "paper", "preprint"}),
        "files_in_root": [f.name for f in files if f.parent == root],
        "empty_dirs": [d + "/" for d in dirs if not any(r.startswith(d + "/") for r in files_rel)],
        "max_depth": max((len(Path(r).parts) for r in files_rel), default=0),
        "environment_files": [e for e in ENV_FILES if (root / e).exists()],
    }

    # readme
    rd = find_readme(root)
    report["readme"] = scan_readme(rd, root, files_rel) if rd else None
    nested = [r for r in files_rel if re.match(r"(?i)^(readme|leggimi)", Path(r).name) and "/" in r]
    if nested:
        report["nested_readmes"] = nested

    # licenses
    lic = scan_licenses(root, files)
    if rd and rd.suffix.lower() in (".md", ".txt", "", ".rst", ".markdown"):
        rtxt = rd.read_text(errors="replace")
        m = re.search(r"(?is)#+\s*(licen[sc]e|licenza)[^\n]*\n(.*?)(?=\n#{1,6}\s|\Z)", rtxt)
        lic["readme_license_section"] = m.group(2).strip()[:1500] if m else None
        lic["readme_detected"] = detect_licenses(m.group(2)) if m else detect_licenses(rtxt)
    for meta in ("CITATION.cff", "DESCRIPTION", "dataset_description.json", "codemeta.json", ".zenodo.json"):
        p = root / meta
        if p.exists():
            mm = re.search(r"(?im)^\s*\"?licen[sc]e\"?\s*[:=]\s*(.+)$", p.read_text(errors="replace"))
            if mm:
                lic.setdefault("metadata_files", {})[meta] = mm.group(1).strip().strip('",')
    report["licenses"] = lic

    # data + dictionaries
    tables, dicts = [], {}
    for f in files:
        if f.suffix.lower() in OPEN_TABULAR:
            if DICT_NAME.search(f.stem):
                try:
                    dicts[rel(f, root)] = parse_dictionary(f, root)
                except Exception as e:  # noqa: BLE001
                    dicts[rel(f, root)] = {"file": rel(f, root), "error": str(e)}
            else:
                tables.append(scan_table(f, root))
    other_dicts = [r for r in files_rel if DICT_NAME.search(Path(r).stem) and Path(r).suffix.lower() not in OPEN_TABULAR]
    all_tables = tables
    tables, report["data"] = group_file_sets(tables)
    # shared columns with different types across files
    by_name = defaultdict(set)
    for t in tables:
        for c in t.get("columns", []):
            if c.get("type") not in (None, "empty"):
                by_name[c["name"]].add((c["type"], t["file"]))
    incons = {}
    for n, s in by_name.items():
        types = {t for t, _ in s}
        if len(types) > 1 and not types <= {"integer", "numeric"}:
            incons[n] = sorted(f"{f}: {t}" for t, f in s)
    if incons:
        report["cross_file_type_inconsistencies"] = incons
    report["cross_file_participants"] = compare_participants(tables)
    for t in tables + all_tables:
        t.pop("_by_id", None)

    dict_report = {"dictionary_files": [{k: v for k, v in d.items() if k != "entries"} | {"n_entries": len(d.get("entries", {}))} for d in dicts.values()],
                   "non_csv_dictionaries": other_dicts, "coverage": []}
    psychds = root / "dataset_description.json"
    psychds_vars = []
    if psychds.exists():
        try:
            dd = json.loads(psychds.read_text())
            psychds_vars = [v if isinstance(v, str) else v.get("name") for v in dd.get("variableMeasured", [])]
            dict_report["dataset_description_variables"] = psychds_vars
        except Exception as e:  # noqa: BLE001
            dict_report["dataset_description_error"] = str(e)
    for t in tables:
        if "columns" not in t:
            continue
        tf = Path(t["file"])
        match = None
        for dname, d in dicts.items():
            dp = Path(dname)
            dstem = DICT_NAME.sub("", dp.stem).strip("_- ").lower()
            tstem = re.sub(r"(?i)[_-]?data$", "", tf.stem).lower()
            if dstem and (dstem == tf.stem.lower() or dstem == tstem or tf.stem.lower().startswith(dstem) or dstem.startswith(tstem)):
                match = d
                break
        if match is None:
            # a single generic dictionary that covers this file's columns
            cols = {c["name"] for c in t["columns"]}
            best = max(dicts.values(), key=lambda d: len(cols & set(d.get("entries", {}))), default=None)
            if best and len(cols & set(best.get("entries", {}))) >= max(1, len(cols) // 2):
                match = best
        if match is None and psychds_vars:
            cols = [c["name"] for c in t["columns"]]
            dict_report["coverage"].append({
                "data": t["file"], "dictionary": "dataset_description.json (variableMeasured: names only)",
                "data_columns_not_in_dictionary": [c for c in cols if c not in psychds_vars]})
        elif match is None:
            dict_report["coverage"].append({"data": t["file"], "dictionary": None})
        else:
            dict_report["coverage"].append({"data": t["file"], **compare_dictionary(t, match)})
    report["dictionaries"] = dict_report

    # code
    code_files = [f for f in files if f.suffix.lower() in CODE_EXT and not (f.suffix.lower() == ".m" and f.stat().st_size == 0)]
    code = [scan_code(f, root, files_rel) for f in code_files]
    written = {w for c in code for w in c.get("writes", [])}
    for c in code:
        if "referenced_files_not_found" in c:
            c["referenced_files_not_found"] = [r for r in c["referenced_files_not_found"] if Path(r).name not in written]
            if not c["referenced_files_not_found"]:
                del c["referenced_files_not_found"]
    report["code"] = {"files": code, "environment": parse_env(root)}
    report["manuscripts"] = find_manuscripts(root, files)
    report["psychds"] = psychds_check(root, all_tables)
    allp = sorted({p for c in code for p in c.get("packages", [])})
    report["code"]["all_packages"] = allp
    lock = report["code"]["environment"].get("renv.lock", {})
    if isinstance(lock, dict) and lock.get("packages"):
        report["code"]["packages_not_in_renv_lock"] = [p for p in allp if p not in lock["packages"]]

    report["materials_present"] = {
        "data": bool(tables) or bool(fmt["proprietary_data"]),
        "code": bool(code),
        "manuscript": bool(report["manuscripts"]),
    }
    text = json.dumps(report, indent=1, ensure_ascii=False, default=str)
    if args.out:
        Path(args.out).write_text(text)
        print(f"Report written to {args.out} ({len(text)} chars)")
    else:
        print(text)


if __name__ == "__main__":
    main()
