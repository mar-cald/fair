#!/usr/bin/env python3
"""Build the deposit version of a project, and zip it for upload.

  python3 build_deposit.py build <project> <plan.json> <out_dir>
  python3 build_deposit.py license <out_dir> --part "Data (data/, dictionaries/, dataset_description.json)=CC0-1.0" \
                                              --part "Code (scripts/)=GPL-3.0" --holder "Name Surname"
  python3 build_deposit.py zip <out_dir>

`build` copies into <out_dir> only the files listed in the plan, under their
new names, and rewrites the file paths written inside the scripts so they point
to the new locations. The original project is never modified.

plan.json:
{
  "files": [
    {"from": "data/stroop data.csv", "to": "data/study-stroop_task-flanker_data.csv"},
    {"from": "analysis/clean.R",     "to": "scripts/01_cleaning.R"}
  ],
  "dirs": {"Results": "output"},     optional: old folder -> new folder, for
                                     outputs that do not exist yet
  "data": {                          optional: deposit copies to rewrite
    "data/raw/survey.csv": {"drop": ["IPAddress", "LocationLatitude"]},
    "data/x_data.csv": {"drop": ["email"], "normalise": true, "remove_export_rows": false}
  },
  "csv_copies": [                    optional: open CSV copies of other formats
    {"from": "data/raw/gonogo.json", "to": "data/study-gonogo_data.csv", "drop": ["PROLIFIC_PID"]},
    {"from": "data/raw/flanker.xlsx", "sheet": "data", "to": "data/study-flanker_data.csv"}
  ]
}

"data" entries (paths in the deposit):
  drop                columns to remove (personal data), in every row, label
                      rows included;
  normalise           (default true) write comma-separated UTF-8 with decimal
                      points; scripts that read the file with read.csv2,
                      sep = ";", dec = ",", or a UTF-16 encoding are adjusted.
                      false keeps the file's own encoding and separator;
  remove_export_rows  (default false) also remove what the export adds around
                      the data: the line above the header (E-DataAid's file
                      path), the label rows under it (Qualtrics question text
                      and ImportId), the footer ("END OF FILE"), an empty last
                      column (PsychoPy). Leave it false for files the scripts
                      read: they may already skip those rows.

"csv_copies" make a comma-separated UTF-8 file from JSON (jsPsych, JATOS), an
E-Prime log, a TSV or a UTF-16 text export, an Excel sheet or an SPSS file
(with pyreadstat), with the export rows removed and the listed columns
dropped. "from" is a path in the deposit or, if not there, in the project.

Prints JSON: files copied, files of the project left out, path rewrites made
in each script, data changes, CSV copies made, path-like strings that could not
be resolved and reading lines to check by hand. Refuses to write into an
existing <out_dir>.

`license` writes <out_dir>/LICENSE: a header saying which license applies to
which part, then the full official text of each license used, copied from the
skill's assets/licenses/ (CC0-1.0, GPL-3.0, CC-BY-4.0).

`zip` writes <out_dir>.zip with the folder inside, skipping hidden files and
system files, ready to upload as a single file (Zenodo shows its contents).
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path, PurePosixPath

CODE_EXT = {".r", ".rmd", ".qmd", ".py", ".ipynb", ".m", ".sps", ".do", ".jl", ".sh"}
SKIP = {".DS_Store", "Thumbs.db", ".Rhistory", ".RData"}
STRING = re.compile(r"(?P<q>[\"'])(?P<s>[^\"'\n]{1,300}?)(?P=q)")
CALL = re.compile(r"(?P<fn>\b(?:here::here|here|file\.path))\(\s*(?P<args>[\"'][^\"'\n]*[\"'](?:\s*,\s*[\"'][^\"'\n]*[\"'])*)\s*\)")
PATHLIKE = re.compile(r"(/|\\|\.[A-Za-z0-9]{1,5}$)")


def norm(p):
    """Normalise a relative path ('./data/../data/x.csv' -> 'data/x.csv')."""
    parts = []
    for part in PurePosixPath(p.replace("\\", "/")).parts:
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                return None  # goes above the project root
            parts.pop()
        else:
            parts.append(part)
    return "/".join(parts)


def rewrite_code(text, old_script, new_script, files_map, dirs_map):
    """Replace path literals that point to moved files, relative to the project root."""
    old_dir = str(PurePosixPath(old_script).parent)
    rewrites, unresolved = [], []

    def resolve(s):
        cands = [norm(s)]
        if old_dir != ".":
            cands.append(norm(f"{old_dir}/{s}"))
        for c in cands:
            if c and c in files_map:
                return files_map[c]
        # folders, and files that do not exist yet (outputs): only for strings that
        # are written as paths from the project root ("figures/x.png"), never for
        # arbitrary strings resolved against the script's own folder
        for c in cands[:1]:
            if not c or "/" not in s.replace("\\", "/"):
                continue
            for old, new in sorted(dirs_map.items(), key=lambda kv: -len(kv[0])):
                if c == old or c.startswith(old + "/"):
                    return new + c[len(old):]
            # a folder all of whose files moved to one new folder
            inside = {str(PurePosixPath(v).parent) for k, v in files_map.items() if k.startswith(c.rstrip("/") + "/")}
            if len(inside) == 1 and c.rstrip("/") not in ("", "."):
                tail = "/" if s.endswith("/") else ""
                return inside.pop() + tail
        return None

    def sub(m):
        s = m.group("s")
        if re.match(r"^([A-Za-z]:[\\/]|/|~)", s) and re.search(r"\.[A-Za-z0-9]{1,5}$|[\\/]$", s):
            unresolved.append(f"{s} (absolute path: rewrite it relative to the project root)")
            return m.group(0)
        if re.match(r"^(https?:|[A-Za-z]:[\\/]|/|~)", s) or not PATHLIKE.search(s) or " " in s.strip() and "/" not in s:
            return m.group(0)
        new = resolve(s)
        if new is None:
            if re.search(r"\.(csv|tsv|txt|xlsx?|sav|rds|rdata|json|png|pdf|jpe?g|svg|html|docx)$", s, re.I):
                unresolved.append(s)
            return m.group(0)
        if new != s:
            rewrites.append(f"{s} -> {new}")
        return f"{m.group('q')}{new}{m.group('q')}"

    # here("data", "x.csv") and file.path("data", "x.csv"): join the pieces,
    # resolve the path, write it back as pieces
    def sub_call(m):
        pieces = re.findall(r"[\"']([^\"']*)[\"']", m.group("args"))
        joined = "/".join(p.strip("/") for p in pieces if p)
        new = resolve(joined)
        if new is None:
            if re.search(r"\.(csv|tsv|txt|xlsx?|sav|rds|rdata|json|png|pdf|jpe?g|svg|html|docx)$", joined, re.I):
                unresolved.append(f"{m.group(0)} (could not map {joined})")
            return m.group(0)
        if new.rstrip("/") == joined:
            return m.group(0)
        q = '"' if '"' in m.group("args") else "'"
        rewrites.append(f"{m.group(0)} -> {m.group('fn')}({', '.join(q + x + q for x in new.rstrip('/').split('/'))})")
        return f"{m.group('fn')}({', '.join(q + x + q for x in new.rstrip('/').split('/'))})"

    text = CALL.sub(sub_call, text)
    # a bare folder name in calls that create or test a folder: dir.create("results")
    for old, new in sorted(dirs_map.items(), key=lambda kv: -len(kv[0])):
        pat = re.compile(r"(?P<fn>\b(?:dir\.create|dir\.exists|os\.makedirs|os\.mkdir|os\.path\.exists|os\.path\.isdir|"
                         r"fs::dir_create|Path|mkdir)\s*\(\s*)(?P<q>[\"'])" + re.escape(old) + r"/?(?P=q)")
        if pat.search(text):
            rewrites.append(f"{old} -> {new} (folder creation)")
            text = pat.sub(lambda m: f"{m.group('fn')}{m.group('q')}{new}{m.group('q')}", text)
    spans = [(m.start(), m.end()) for m in CALL.finditer(text)]

    def sub_outside_calls(m):
        if any(a <= m.start() < b for a, b in spans):
            return m.group(0)
        return sub(m)

    out = STRING.sub(sub_outside_calls, text)
    return out, rewrites, sorted(set(unresolved))


def _fair_scan():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import fair_scan  # noqa: PLC0415
    return fair_scan


ENC_NAMES = {"utf-8": "utf-8", "cp1252": "cp1252", "latin-1": "latin-1", "utf-16": "utf-16",
             "utf-16-le": "utf-16-le", "utf-16-be": "utf-16-be"}


def _write_rows(path, rows, preamble=(), encoding="utf-8", delimiter=",", bom=False):
    import csv  # noqa: PLC0415
    enc = "utf-8-sig" if encoding == "utf-8" and bom else ENC_NAMES.get(encoding, "utf-8")
    with open(path, "w", newline="", encoding=enc) as fh:
        for line in preamble:
            fh.write(line + "\r\n")
        csv.writer(fh, delimiter=delimiter).writerows(rows)


def normalise_csv(path, drop=(), normalise=True, remove_export_rows=False):
    """Rewrite a data file in the deposit: without the columns in `drop`; as
    comma-separated UTF-8 with decimal points (normalise); without the rows the
    export adds around the data (remove_export_rows). Returns what changed."""
    fs = _fair_scan()
    rows, info = fs.read_table(path)
    rows = [r for r in rows if any(c.strip() for c in r)]
    preamble = info.get("preamble", [])
    changes = []
    if remove_export_rows:
        header, body, labels, layout = fs.split_export(rows)
        rows = [header] + body
        if preamble:
            changes.append(f"removed {len(preamble)} line(s) above the header")
            preamble = []
        if layout.get("label_rows"):
            changes.append(f"removed {layout['label_rows']} label row(s) under the header ({layout['label_rows_hold']})")
        if layout.get("footer_rows"):
            changes.append(f"removed {layout['footer_rows']} footer row(s) (END OF FILE)")
        if layout.get("empty_last_column"):
            changes.append("removed the empty unnamed last column")
    header = rows[0]
    keep = [i for i, h in enumerate(header) if h not in set(drop)]
    removed = [h for h in header if h in set(drop)]
    missing = [d for d in drop if d not in header]
    if removed:
        changes.append("columns removed: " + ", ".join(removed))
    if missing:
        changes.append("columns to drop not found in the file: " + ", ".join(missing))
    dec = fs.detect_decimal_comma(rows[1:], info.get("delimiter"))
    if normalise:
        if info["delimiter"] != "comma":
            changes.append(f"{info['delimiter']}-separated -> comma-separated")
        if dec:
            changes.append("decimal comma -> decimal point")
        if info.get("encoding") not in ("utf-8", None) or info.get("bom"):
            changes.append(f"{info.get('encoding')}{' with BOM' if info.get('bom') else ''} -> UTF-8")
    if not changes or changes == [c for c in changes if c.startswith("columns to drop not found")]:
        return changes
    out = []
    for r in rows:
        r = [r[i] if i < len(r) else "" for i in keep]
        if normalise and dec:
            r = [re.sub(r"^(-?\d+),(\d+)$", r"\1.\2", c.strip()) if re.match(r"^-?\d+,\d+$", c.strip()) else c for c in r]
        out.append(r)
    if normalise:
        _write_rows(path, out, preamble)
    else:
        delim = {"comma": ",", "semicolon": ";", "tab": "\t", "pipe": "|"}[info["delimiter"]]
        _write_rows(path, out, preamble, info.get("encoding") or "utf-8", delim, info.get("bom", False))
    return changes


def csv_copy(src, dst, sheet=None, drop=()):
    """Write `dst` as a comma-separated UTF-8 copy of the table in `src`, with
    the export rows removed and the `drop` columns left out."""
    fs = _fair_scan()
    rows, info = fs.load_table(src, sheet)
    header, body, labels, layout = fs.split_export(rows)
    keep = [i for i, h in enumerate(header) if h not in set(drop)]
    dec = fs.detect_decimal_comma(body, info.get("delimiter"))
    out = []
    for r in [header] + body:
        r = [r[i] if i < len(r) else "" for i in keep]
        if dec:
            r = [re.sub(r"^(-?\d+),(\d+)$", r"\1.\2", c.strip()) if re.match(r"^-?\d+,\d+$", c.strip()) else c for c in r]
        out.append(r)
    Path(dst).parent.mkdir(parents=True, exist_ok=True)
    _write_rows(dst, out)
    notes = [f"{len(body)} rows, {len(keep)} columns, from {info.get('format') or info.get('delimiter', '')} "
             f"({info.get('encoding', '')})".replace(" ()", "")]
    if info.get("preamble"):
        notes.append(f"left out {len(info['preamble'])} line(s) above the header")
    if layout.get("label_rows"):
        notes.append(f"left out {layout['label_rows']} label row(s) ({layout['label_rows_hold']})")
    if layout.get("footer_rows"):
        notes.append("left out the footer (END OF FILE)")
    removed = [h for h in header if h in set(drop)]
    if removed:
        notes.append("columns left out: " + ", ".join(removed))
    if dec:
        notes.append("decimal comma -> decimal point")
    return notes


READER_FIXES = [(r"read\.csv2\(", "read.csv("), (r"read_csv2\(", "read_csv("),
                (r"(sep|delim|delimiter)\s*=\s*([\"']);\2", r"\1 = \2,\2"),
                (r"(sep|delim|delimiter)\s*=\s*([\"'])\\t\2", r"\1 = \2,\2"),
                (r"read\.delim2?\(", "read.csv("), (r"read_tsv\(", "read_csv("),
                (r"dec\s*=\s*([\"']),\1", r"dec = \1.\1"),
                (r"(?i)((?:file)?[Ee]ncoding\s*=\s*)([\"'])(utf-?16(?:-?le|-?be)?|ucs-?2(?:-?le)?)\2", r"\1\2UTF-8\2")]
SUSPECT = re.compile(r"read\.csv2|read_csv2|read\.delim|read_tsv|sep\s*=\s*[\"'](;|\\t)|dec\s*=\s*[\"'],|(?i:utf-?16)")


def fix_readers(text, converted_names, kept_names=()):
    """On lines that read a file converted to comma-separated UTF-8, switch the
    reader and its arguments. Returns (text, changes, lines to check by hand):
    reading calls that may read a converted file through a variable (lines that
    name a file that was not converted are fine)."""
    changes, check = [], []
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if any(n in line for n in converted_names):
            new = line
            for pat, rep in READER_FIXES:
                new = re.sub(pat, rep, new)
            if new != line:
                changes.append(f"line {i + 1}: {line.strip()} -> {new.strip()}")
                lines[i] = new
        elif converted_names and SUSPECT.search(line) and not line.lstrip().startswith("#") \
                and not any(n in line for n in kept_names):
            check.append(f"line {i + 1}: {line.strip()[:120]}")
    return "\n".join(lines), changes, check


def build_deposit(src, plan, out):
    """Copy the files listed in `plan` from `src` into the new folder `out`.

    plan = {"files": [{"from", "to"}], "dirs": {old: new},
            "data": {"<to path>": {"drop": [columns], "normalise": true}}}
    Data files listed under "data" are rewritten comma-separated (see
    normalise_csv), and the scripts that read them are adjusted."""
    src, out = Path(src).expanduser().resolve(), Path(out).expanduser().resolve()
    if out.exists():
        raise ValueError(f"{out} already exists: choose another name or remove it first")
    files_map = {}
    for f in plan["files"]:
        k = norm(f["from"])
        if not (src / k).is_file():
            raise ValueError(f"Not a file in the project: {f['from']}")
        files_map[k] = norm(f["to"])
    if len(set(files_map.values())) != len(files_map):
        raise ValueError("Two files are mapped to the same destination")
    dirs_map = {norm(k): norm(v) for k, v in plan.get("dirs", {}).items()}
    # a folder whose files all moved to one new folder: outputs written there later follow
    by_parent = {}
    for k, v in files_map.items():
        by_parent.setdefault(str(PurePosixPath(k).parent), set()).add(str(PurePosixPath(v).parent))
    for k, v in by_parent.items():
        if len(v) == 1 and k != "." and k not in dirs_map:
            dirs_map[k] = v.pop()

    out.mkdir(parents=True)
    report = {"out": str(out), "copied": [], "rewrites": {}, "unresolved_paths": {}, "data_changes": {}}
    for new in plan.get("dirs", {}).values():  # output folders the scripts write into
        (out / norm(new)).mkdir(parents=True, exist_ok=True)
    for old, new in files_map.items():
        dst = out / new
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / old, dst)
        report["copied"].append(f"{old} -> {new}" if old != new else new)
    converted, rows_removed = [], []
    for new, opts in plan.get("data", {}).items():
        new = norm(new)
        if not (out / new).is_file():
            report.setdefault("check_by_hand", []).append(f"data entry {new}: no such file in the deposit")
            continue
        ch = normalise_csv(out / new, opts.get("drop", ()), opts.get("normalise", True), opts.get("remove_export_rows", False))
        if ch:
            report["data_changes"][new] = ch
            if any("-separated" in c or "-> UTF-8" in c or "decimal comma" in c for c in ch):
                converted.append(PurePosixPath(new).name)
            if any(c.startswith("removed") and "column" not in c for c in ch):
                rows_removed.append(new)
    for cp in plan.get("csv_copies", []):
        frm, to = norm(cp["from"]), norm(cp["to"])
        source = out / frm if (out / frm).is_file() else src / frm
        if not source.is_file():
            report.setdefault("check_by_hand", []).append(f"csv copy {to}: source {cp['from']} not found")
            continue
        if (out / to).exists():
            report.setdefault("check_by_hand", []).append(f"csv copy {to}: already exists, not overwritten")
            continue
        try:
            report.setdefault("csv_copies", {})[to] = csv_copy(source, out / to, cp.get("sheet"), cp.get("drop", ()))
        except (ValueError, ImportError) as e:
            report.setdefault("check_by_hand", []).append(f"csv copy {to}: {e}")
    for old, new in files_map.items():
        if Path(old).suffix.lower() in CODE_EXT:
            text = (src / old).read_text(errors="replace")
            text, rw, un = rewrite_code(text, old, new, files_map, dirs_map)
            kept = {PurePosixPath(v).name for v in files_map.values()} - set(converted)
            text, rd, check = fix_readers(text, converted, kept)
            (out / new).write_text(text)
            if rw or rd:
                report["rewrites"][new] = rw + rd
            if un:
                report["unresolved_paths"][new] = un
            if check:
                report.setdefault("check_by_hand", []).append(
                    {new: ["reads a file with a semicolon/tab separator, decimal comma or UTF-16, maybe a converted one "
                           "through a variable"] + check})
            names = {PurePosixPath(n).name for n in rows_removed} | \
                {PurePosixPath(k).name for k, v in files_map.items() if v in rows_removed}
            hit = [n for n in names if n in text]
            if hit:
                report.setdefault("check_by_hand", []).append(
                    {new: [f"reads {', '.join(hit)}, whose export rows were removed: if the script skipped them "
                           "(skip =, [-c(1, 2), ], qualtRics::read_survey), it would now drop real rows"]})

    all_files = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("renv", "__pycache__", "node_modules")]
        for fn in filenames:
            if fn in SKIP or fn.startswith("."):
                continue
            all_files.append(norm(os.path.relpath(Path(dirpath) / fn, src)))
    report["left_out"] = sorted(f for f in all_files if f not in files_map)
    return report


LICENSE_NAMES = {"CC0-1.0": "Creative Commons Zero v1.0 Universal (CC0-1.0)",
                 "GPL-3.0": "GNU General Public License v3.0 (GPL-3.0)",
                 "CC-BY-4.0": "Creative Commons Attribution 4.0 International (CC-BY-4.0)"}


def write_license(out, parts, holder=None, year=None, assets=None):
    """parts = [(what it covers, license id)]. Writes <out>/LICENSE."""
    out = Path(out)
    assets = Path(assets) if assets else Path(__file__).resolve().parent.parent / "assets" / "licenses"
    used = []
    for _, lic in parts:
        if lic not in LICENSE_NAMES:
            raise ValueError(f"Unknown license {lic}: use one of {', '.join(LICENSE_NAMES)}")
        if lic not in used:
            used.append(lic)
    lines = ["This repository contains material under different licenses.", ""]
    lines += [f"- {what}: {LICENSE_NAMES[lic]}" for what, lic in parts]
    lines += ["- Third-party materials, if any are cited: not included, subject to the conditions of their owners", ""]
    if holder:
        lines += [f"Copyright (c) {year or __import__('datetime').date.today().year} {holder}", ""]
    lines += ["The full text of each license follows.", ""]
    for lic in used:
        lines += ["", "=" * 78, LICENSE_NAMES[lic], "=" * 78, "", (assets / f"{lic}.txt").read_text().rstrip(), ""]
    (out / "LICENSE").write_text("\n".join(lines) + "\n")
    return used


def zip_deposit(out):
    """Write <out>.zip with the folder inside; returns (zip path, number of files)."""
    out = Path(out).expanduser().resolve()
    target = out.with_suffix(".zip")
    n = 0
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):
            rel = p.relative_to(out)
            if any(part.startswith(".") or part in ("__pycache__", ".Rproj.user") for part in rel.parts) or p.name in SKIP:
                continue
            if p.is_file():
                z.write(p, PurePosixPath(out.name) / PurePosixPath(*rel.parts))
                n += 1
    return target, n


def cli_build(args):
    try:
        report = build_deposit(args.project, json.loads(Path(args.plan).read_text()), args.out_dir)
    except ValueError as e:
        sys.exit(str(e))
    print(json.dumps(report, indent=1, ensure_ascii=False))


def cli_license(args):
    parts = []
    for p in args.part:
        what, _, lic = p.rpartition("=")
        parts.append((what.strip(), lic))
    try:
        used = write_license(args.out_dir, parts, args.holder, args.year)
    except ValueError as e:
        sys.exit(str(e))
    print(f"Wrote {Path(args.out_dir) / 'LICENSE'} ({', '.join(used)})")


def cli_zip(args):
    target, n = zip_deposit(args.out_dir)
    print(f"Wrote {target} ({n} files, {round(target.stat().st_size / 1024)} KB)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("project")
    b.add_argument("plan")
    b.add_argument("out_dir")
    lc = sub.add_parser("license")
    lc.add_argument("out_dir")
    lc.add_argument("--part", action="append", required=True, help='"what it covers=LICENSE-ID"')
    lc.add_argument("--holder")
    lc.add_argument("--year", default=str(__import__("datetime").date.today().year))
    z = sub.add_parser("zip")
    z.add_argument("out_dir")
    args = ap.parse_args()
    {"build": cli_build, "license": cli_license, "zip": cli_zip}[args.cmd](args)


if __name__ == "__main__":
    main()
