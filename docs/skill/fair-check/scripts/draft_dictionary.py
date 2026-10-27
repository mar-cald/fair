#!/usr/bin/env python3
"""Draft a data dictionary for a data file, with the booklet's columns.

Usage: python3 draft_dictionary.py <data file> [<more files> ...] [--out <path>] [--sheet <name>] [--force]

Reads CSV/TSV and delimited .txt (any encoding), JSON (jsPsych, JATOS), E-Prime
logs, and Excel/SPSS files when openpyxl/pyreadstat are installed. Several files
with (nearly) the same columns, e.g. one PsychoPy file per participant, are
described together in one dictionary: pass them all and give --out.

Writes <stem>_dictionary.csv next to the data file (or to --out), one row per
column: variable_name, label, type, unit, allowed_values, coding,
missing_values, source, notes.

Filled from the data: variable_name, type, allowed_values (range or list of
observed values), missing_values (how missing cells appear). For categorical
columns, coding gets the observed codes with an empty meaning ("1 = ; 2 = ").

Filled from the file itself, when it says it:
- label from the rows an export puts under the header (Qualtrics question
  text), or from the variable labels of an SPSS file;
- label, unit and coding of the columns that Qualtrics, PsychoPy, jsPsych,
  Gorilla, OpenSesame and E-Prime write on their own (key_resp.rt, Reaction
  Time, subject_nr ...), from software.py, marked "to check" in notes.

Left as TODO: everything else, because it cannot be read from the data.
Refuses to overwrite an existing file unless --force is given.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fair_scan import (NOT_PARTICIPANT_ID, PARTICIPANT_ID, detect_decimal_comma, infer_column, load_stat,  # noqa: E402
                       load_table, personal_flags, split_export)
from software import describe_column, detect_software  # noqa: E402

def num_text(x):
    """1.1e7 -> '11000001', 463.2351 -> '463.2351' (no scientific notation)."""
    x = float(x)
    if x.is_integer():
        return str(int(x))
    return f"{x:.6f}".rstrip("0").rstrip(".")


COLUMNS = ["variable_name", "label", "type", "unit", "allowed_values", "coding", "missing_values", "source", "notes"]
IDLIKE = re.compile(r"(?i)(^id$|_id$|^id_|subj|participant|partecipante|soggetto|^sub$|^pp$|responseid|trial)")


def read(paths, sheet=None):
    """Rows of one or more files with (nearly) the same columns, merged by name.
    Returns (header, body, labels, info, n_files_per_column, spss_labels)."""
    header, body, labels, info, present, spss = [], [], {}, None, {}, {"variable_labels": {}, "value_labels": {}}
    for p in paths:
        rows, info = load_table(p, sheet)
        h, b, lab, _ = split_export(rows)
        if header and len(set(h) & set(header)) < 0.8 * len(set(h) | set(header)):
            raise ValueError(f"{p.name} has different columns from {paths[0].name}: describe it separately")
        for c in h:
            if c not in header:
                header.append(c)
            present[c] = present.get(c, 0) + 1
        idx = {c: j for j, c in enumerate(h)}
        body += [[r[idx[c]] if c in idx and idx[c] < len(r) else "" for c in header] for r in b]
        if lab:
            for j, c in enumerate(h):
                txt = lab[0][j].strip() if j < len(lab[0]) else ""
                if txt and not txt.startswith('{"ImportId"') and txt != c:
                    labels.setdefault(c, txt)
        if p.suffix.lower() in (".sav", ".zsav", ".por", ".dta", ".sas7bdat"):
            try:
                _, sl = load_stat(p)
                spss["variable_labels"].update(sl["variable_labels"])
                spss["value_labels"].update(sl["value_labels"])
            except ImportError:
                pass
    # rows written before a column first appeared
    body = [r + [""] * (len(header) - len(r)) for r in body]
    return header, body, labels, info or {}, present, spss


def draft(paths, sheet=None):
    """Draft dictionary rows (list of dicts with COLUMNS)."""
    paths = [Path(p) for p in paths]
    header, body, labels, info, present, spss = read(paths, sheet)
    decimal_comma = detect_decimal_comma(body, info.get("delimiter"))
    program, _ = detect_software(header)
    if not program and labels:
        program, _ = detect_software(list(labels.values()))
    lines = []
    for j, h in enumerate(header):
        vals = [r[j] if j < len(r) else "" for r in body]
        c = infer_column(h, vals, decimal_comma)
        private = bool(personal_flags(h, vals, labels.get(h, "")))
        t = c.get("type", "string")
        allowed, coding, notes = "", "", []
        idlike = IDLIKE.search(h)
        if t in ("integer", "numeric") and "min" in c and not private:
            lo, hi = (num_text(x) for x in (c["min"], c["max"]))
            allowed = f"{lo} to {hi}" if c["min"] < 0 else f"{lo}-{hi}"
            if c.get("values") and len(c["values"]) <= 6 and not idlike:
                coding = "; ".join(f"{v} = TODO" for v in c["values"])
                notes.append("integer with few values: categorical? if so set type and coding")
        elif idlike and t in ("categorical", "string") and not private:
            # an identifier: describe its form (p01-p30), not each value
            ids = sorted({v.strip() for v in vals if v.strip()})
            t, allowed = "string", f"{ids[0]}-{ids[-1]}" if ids else ""
            if PARTICIPANT_ID.search(h) and not NOT_PARTICIPANT_ID.search(h) and any(not re.search(r"\d", i) for i in ids):
                allowed = "TODO"
                notes.append("some IDs have no digits (initials or names?): check they cannot identify anyone; "
                             "their range is not shown here")
        elif t in ("categorical", "boolean") and c.get("values") and not private:
            allowed = "; ".join(c["values"])
            coding = "; ".join(f"{v} = TODO" for v in c["values"]) if t == "categorical" else ""
        elif t == "mixed":
            t = "TODO (mixed numbers and text)"
        elif t in ("JSON object", "list"):
            if c.get("json_keys"):
                notes.append("keys in the cells: " + ", ".join(c["json_keys"][:15]))
        if c.get("json_keys") and t not in ("JSON object", "list"):
            notes.append("some cells are JSON objects, with keys: " + ", ".join(c["json_keys"][:15]))
        label, unit, source = "TODO", "TODO" if t in ("integer", "numeric") and not idlike else "", "TODO"
        # what the file itself says about the column
        known = describe_column(program, h)
        if known:
            label = known["label"]
            unit = known.get("unit", "")
            if known.get("coding") and t in ("integer", "categorical", "boolean", "string"):
                coding, t = known["coding"], "categorical"
                notes = [n for n in notes if not n.startswith("integer with few values")]
            source = f"{program} (column written by the software)"
            notes.append(f"standard {program} column: to check")
        if h in spss["variable_labels"]:
            label = spss["variable_labels"][h]
            source = "SPSS variable label" if source == "TODO" else source
        if h in spss["value_labels"]:
            coding = "; ".join(f"{k} = {v}" for k, v in spss["value_labels"][h].items())
        if h in labels and not known:
            label = labels[h]
            notes.append("label from the question text in the export: to check")
        if private:
            notes.append("possible personal data: check before sharing")
        if len(paths) > 1 and present.get(h, 0) < len(paths):
            notes.append(f"present in {present.get(h, 0)} of {len(paths)} files")
        for i in c.get("issues", []):
            notes.append(i)
        miss = "; ".join(c.get("missing_tokens", {}).keys())
        lines.append({"variable_name": h, "label": label, "type": t, "unit": unit,
                      "allowed_values": allowed, "coding": coding,
                      "missing_values": miss if miss else "none in data",
                      "source": source, "notes": " | ".join(notes)})
    return lines


def write_dictionary(lines, out):
    with Path(out).open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data", nargs="+")
    ap.add_argument("--out")
    ap.add_argument("--sheet", help="sheet of an Excel file")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    paths = [Path(d).expanduser().resolve() for d in args.data]
    if len(paths) > 1 and not args.out:
        sys.exit("With several files, say where to write the dictionary with --out")
    path = paths[0]
    stem = path.stem[:-5] if path.stem.lower().endswith("_data") else path.stem
    out = Path(args.out) if args.out else path.with_name(f"{stem}_dictionary.csv")
    if out.exists() and not args.force:
        sys.exit(f"{out} already exists: not overwritten (use --force)")
    try:
        lines = draft(paths, args.sheet)
    except ValueError as e:
        sys.exit(str(e))
    write_dictionary(lines, out)
    n_auto = sum(1 for x in lines if x["label"] != "TODO")
    print(f"Wrote {out} ({len(lines)} variables; {n_auto} labels from the file itself, to check; "
          f"{len(lines) - n_auto} labels TODO)")


if __name__ == "__main__":
    main()
