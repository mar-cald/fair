#!/usr/bin/env python3
"""Write dataset_description.json (Psych-DS) from the CSV data dictionaries.

Usage: python3 make_psychds.py <deposit_dir> --name "Title" --description "..."
                               [--meta extra.json]

Reads every data/**/*_data.csv (data/raw/ excluded) and the dictionaries in
dictionaries/<stem>_dictionary.csv, where <stem> is the data file name without
"_data.csv". Builds "variableMeasured" with one schema.org PropertyValue per
column, as on the booklet's Psych-DS page:

  name         the column name
  description  label, then the coding if any ("0 = incorrect; 1 = correct")
               and how missing values are written
  unitText     unit
  minValue / maxValue   from a numeric allowed_values range ("200-2000")
  value        the allowed values of a categorical column ("a | b")

--meta adds or overrides top-level fields (author, license, keywords,
temporalCoverage, ...). An existing dataset_description.json is kept and its
fields are preserved, except variableMeasured which is rebuilt.

Checks that every column of every data file is in variableMeasured and that
every variable has a dictionary entry; prints what is missing.
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fair_scan import read_table  # noqa: E402


def num(s):
    try:
        x = float(s)
        return int(x) if x.is_integer() else x
    except ValueError:
        return None


def property_value(entry):
    pv = {"@type": "PropertyValue", "name": entry["variable_name"]}
    desc = (entry.get("label") or "").strip()
    if desc.upper() == "TODO":
        desc = ""
    coding = (entry.get("coding") or "").strip()
    if coding and "TODO" not in coding:
        desc = f"{desc}. Coding: {coding}" if desc else f"Coding: {coding}"
    miss = (entry.get("missing_values") or "").strip()
    if miss and miss.lower() not in ("none", "none in data", ""):
        desc = f"{desc}. Missing values: {miss}" if desc else f"Missing values: {miss}"
    if desc:
        desc = desc[0].upper() + desc[1:]
        pv["description"] = desc if desc.endswith(".") else desc + "."
    unit = (entry.get("unit") or "").strip()
    if unit and unit.upper() != "TODO":
        pv["unitText"] = unit
    av = (entry.get("allowed_values") or "").strip()
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(-?\d+(?:\.\d+)?)\s*$", av)
    typ = (entry.get("type") or "").lower()
    if m and typ in ("integer", "numeric", ""):
        pv["minValue"], pv["maxValue"] = num(m.group(1)), num(m.group(2))
    elif av and av.upper() != "TODO" and typ in ("categorical", "boolean"):
        pv["value"] = " | ".join(v.strip() for v in re.split(r"[;|]", av) if v.strip())
    return pv


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deposit")
    ap.add_argument("--name")
    ap.add_argument("--description")
    ap.add_argument("--meta")
    args = ap.parse_args()
    root = Path(args.deposit).expanduser().resolve()
    data_files = sorted(p for p in (root / "data").rglob("*_data.csv") if "raw" not in p.relative_to(root / "data").parts)
    if not data_files:
        sys.exit("No data/*_data.csv files found")

    columns, entries, problems = {}, {}, []
    for f in data_files:
        rows, _ = read_table(f)
        header = [h.strip() for h in rows[0]]
        for h in header:
            columns.setdefault(h, []).append(f.name)
        d = root / "dictionaries" / (f.name[: -len("_data.csv")] + "_dictionary.csv")
        if not d.exists():
            problems.append(f"no dictionary for {f.name} (expected dictionaries/{d.name})")
            continue
        with d.open(newline="", encoding="utf-8-sig") as fh:
            for e in csv.DictReader(fh):
                n = (e.get("variable_name") or "").strip()
                if not n:
                    continue
                if n not in header:
                    problems.append(f"{d.name}: '{n}' is not a column of {f.name}")
                if n in entries and property_value(e) != property_value(entries[n]):
                    problems.append(f"'{n}' is described differently in two dictionaries: kept the first ({entries[n]['_from']})")
                    continue
                entries.setdefault(n, {**e, "_from": d.name})

    variables = []
    for col in columns:  # order of first appearance
        if col in entries:
            variables.append(property_value(entries[col]))
        else:
            problems.append(f"column '{col}' ({', '.join(columns[col])}) has no dictionary entry: listed by name only")
            variables.append(col)

    out = root / "dataset_description.json"
    desc = json.loads(out.read_text()) if out.exists() else {}
    base = {"@context": "https://schema.org/", "@type": "Dataset"}
    desc = {**base, **desc}
    if args.name:
        desc["name"] = args.name
    if args.description:
        desc["description"] = args.description
    if args.meta:
        desc.update(json.loads(Path(args.meta).read_text()))
    desc["variableMeasured"] = variables
    for req in ("name", "description"):
        if not desc.get(req):
            problems.append(f"required field '{req}' is empty")
    ordered = {k: desc[k] for k in ["@context", "@type", "name", "description"] if k in desc}
    ordered.update({k: v for k, v in desc.items() if k not in ordered and k != "variableMeasured"})
    ordered["variableMeasured"] = variables
    out.write_text(json.dumps(ordered, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"written": str(out), "n_variables": len(variables), "data_files": [f.name for f in data_files],
                      "problems": problems}, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
