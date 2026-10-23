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
  "dirs": {"Results": "output"}      optional: old folder -> new folder, for
                                     outputs that do not exist yet
}

Prints JSON: files copied, files of the project left out, path rewrites made
in each script, and path-like strings that could not be resolved (to fix by
hand). Refuses to write into an existing <out_dir>.

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
        for c in cands:  # folders and files that do not exist yet (outputs)
            if not c:
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

    out = STRING.sub(sub, text)
    if re.search(r"\bhere\s*\(\s*[\"'][^\"']+[\"']\s*,", text):
        unresolved.append("here(...) with several pieces: check by hand")
    return out, rewrites, sorted(set(unresolved))


def build(args):
    src = Path(args.project).expanduser().resolve()
    out = Path(args.out_dir).expanduser().resolve()
    if out.exists():
        sys.exit(f"{out} already exists: choose another name or remove it first")
    plan = json.loads(Path(args.plan).read_text())
    files_map = {}
    for f in plan["files"]:
        k = norm(f["from"])
        if not (src / k).is_file():
            sys.exit(f"Not a file in the project: {f['from']}")
        files_map[k] = norm(f["to"])
    if len(set(files_map.values())) != len(files_map):
        sys.exit("Two files are mapped to the same destination")
    dirs_map = {norm(k): norm(v) for k, v in plan.get("dirs", {}).items()}

    out.mkdir(parents=True)
    report = {"out": str(out), "copied": [], "rewrites": {}, "unresolved_paths": {}}
    for old, new in files_map.items():
        dst = out / new
        dst.parent.mkdir(parents=True, exist_ok=True)
        if Path(old).suffix.lower() in CODE_EXT:
            text = (src / old).read_text(errors="replace")
            text, rw, un = rewrite_code(text, old, new, files_map, dirs_map)
            dst.write_text(text)
            if rw:
                report["rewrites"][new] = rw
            if un:
                report["unresolved_paths"][new] = un
        else:
            shutil.copy2(src / old, dst)
        report["copied"].append(f"{old} -> {new}" if old != new else new)

    all_files = []
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in ("renv", "__pycache__", "node_modules")]
        for fn in filenames:
            if fn in SKIP or fn.startswith("."):
                continue
            all_files.append(norm(os.path.relpath(Path(dirpath) / fn, src)))
    report["left_out"] = sorted(f for f in all_files if f not in files_map)
    print(json.dumps(report, indent=1, ensure_ascii=False))


LICENSE_NAMES = {"CC0-1.0": "Creative Commons Zero v1.0 Universal (CC0-1.0)",
                 "GPL-3.0": "GNU General Public License v3.0 (GPL-3.0)",
                 "CC-BY-4.0": "Creative Commons Attribution 4.0 International (CC-BY-4.0)"}


def make_license(args):
    out = Path(args.out_dir).expanduser().resolve()
    assets = Path(__file__).resolve().parent.parent / "assets" / "licenses"
    parts, used = [], []
    for p in args.part:
        what, _, lic = p.rpartition("=")
        if lic not in LICENSE_NAMES:
            sys.exit(f"Unknown license {lic}: use one of {', '.join(LICENSE_NAMES)}")
        parts.append((what.strip(), lic))
        if lic not in used:
            used.append(lic)
    lines = ["This repository contains material under different licenses.", ""]
    lines += [f"- {what}: {LICENSE_NAMES[lic]}" for what, lic in parts]
    lines += ["- Third-party materials, if any are cited: not included, subject to the conditions of their owners", ""]
    if args.holder:
        lines += [f"Copyright (c) {args.year} {args.holder}", ""]
    lines += ["The full text of each license follows.", ""]
    for lic in used:
        lines += ["", "=" * 78, LICENSE_NAMES[lic], "=" * 78, "", (assets / f"{lic}.txt").read_text().rstrip(), ""]
    (out / "LICENSE").write_text("\n".join(lines) + "\n")
    print(f"Wrote {out / 'LICENSE'} ({', '.join(used)})")


def make_zip(args):
    out = Path(args.out_dir).expanduser().resolve()
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
    {"build": build, "license": make_license, "zip": make_zip}[args.cmd](args)


if __name__ == "__main__":
    main()
