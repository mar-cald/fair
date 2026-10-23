#!/usr/bin/env python3
"""Draft a data dictionary for a CSV/TSV file, with the booklet's columns.

Usage: python3 draft_dictionary.py <data.csv> [--out <path>] [--force]

Writes <stem>_dictionary.csv next to the data file (or to --out), one row per
column: variable_name, label, type, unit, allowed_values, coding,
missing_values, source, notes.

Filled from the data: variable_name, type, allowed_values (range or list of
observed values), missing_values (how missing cells appear). For categorical
columns, coding gets the observed codes with an empty meaning ("1 = ; 2 = ").
Left as TODO: label, unit, source, and the meaning of each code, because they
cannot be read from the data. Refuses to overwrite an existing file unless
--force is given.
"""

import argparse
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fair_scan import infer_column, personal_flags, read_table  # noqa: E402

COLUMNS = ["variable_name", "label", "type", "unit", "allowed_values", "coding", "missing_values", "source", "notes"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("--out")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    path = Path(args.data).expanduser().resolve()
    rows, info = read_table(path)
    rows = [r for r in rows if any(c.strip() for c in r)]
    header, body = rows[0], rows[1:]
    stem = path.stem[:-5] if path.stem.lower().endswith("_data") else path.stem
    out = Path(args.out) if args.out else path.with_name(f"{stem}_dictionary.csv")
    if out.exists() and not args.force:
        sys.exit(f"{out} already exists: not overwritten (use --force)")

    decimal_comma = info["delimiter"] == "semicolon" and any(
        re.match(r"^-?\d+,\d+$", c.strip()) for r in body[:500] for c in r)
    lines = []
    for j, h in enumerate(header):
        vals = [r[j] if j < len(r) else "" for r in body]
        c = infer_column(h, vals, decimal_comma)
        private = bool(personal_flags(h, vals))
        t = c.get("type", "string")
        allowed, coding, notes = "", "", []
        idlike = re.search(r"(?i)(^id$|_id$|^id_|subj|participant|partecipante|soggetto|^sub$|^pp$|trial)", h)
        if t in ("integer", "numeric") and "min" in c and not private:
            lo, hi = (f"{x:g}" for x in (c["min"], c["max"]))
            allowed = f"{lo} to {hi}" if c["min"] < 0 else f"{lo}-{hi}"
            if c.get("values") and len(c["values"]) <= 6 and not idlike:
                coding = "; ".join(f"{v} = TODO" for v in c["values"])
                notes.append("integer with few values: categorical? if so set type and coding")
        elif idlike and t in ("categorical", "string") and not private:
            # an identifier: describe its form (p01-p30), not each value
            ids = sorted({v.strip() for v in vals if v.strip()})
            t, allowed = "string", f"{ids[0]}-{ids[-1]}" if ids else ""
        elif t in ("categorical", "boolean") and c.get("values") and not private:
            allowed = "; ".join(c["values"])
            coding = "; ".join(f"{v} = TODO" for v in c["values"]) if t == "categorical" else ""
        elif t == "mixed":
            t = "TODO (mixed numbers and text)"
        if private:
            notes.append("possible personal data: check before sharing")
        for i in c.get("issues", []):
            notes.append(i)
        miss = "; ".join(c.get("missing_tokens", {}).keys())
        lines.append({"variable_name": h, "label": "TODO", "type": t, "unit": "TODO" if t in ("integer", "numeric") and not idlike else "",
                      "allowed_values": allowed, "coding": coding,
                      "missing_values": miss if miss else "none in data",
                      "source": "TODO", "notes": " | ".join(notes)})

    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(lines)
    print(f"Wrote {out} ({len(lines)} variables)")


if __name__ == "__main__":
    main()
