#!/usr/bin/env python3
"""Run a project's scripts in a throw-away copy of the folder.

Usage: python3 run_code.py <project_folder> [script ...] [--timeout 600]

Without explicit scripts, runs every R / Rmd / qmd / Python / notebook file in
order: numbered files first (01_, 02_ ...), then the rest alphabetically.
Pass scripts explicitly (paths relative to the project) when the README gives
a different order.

The original folder is never touched: everything runs in a temporary copy,
from the project root (like an RStudio project). If a script fails because it
cannot find a file, it is retried from its own folder, and the result says so.

Prints JSON: per script, the command, exit status, duration, the last lines of
the error output, packages reported as missing, and the files it created.
Packages are never installed by this script.

--logs DIR saves what each script prints (DIR/<script>.log), to compare with
the numbers in a manuscript. --in-place runs in the folder itself instead of a
copy: use it only on the deposit version built by build_deposit.py, never on
the researcher's own folder.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

IGNORE = shutil.ignore_patterns(".git", ".Rproj.user", "renv/library", "node_modules", "__pycache__",
                                ".ipynb_checkpoints", ".venv", "venv", ".quarto", ".DS_Store")
RUNNABLE = {".r", ".rmd", ".qmd", ".py", ".ipynb"}
SKIP_DIRS = {".git", ".Rproj.user", "renv", "node_modules", "__pycache__", ".ipynb_checkpoints", ".venv", "venv"}

MISSING_PATTERNS = [
    r"there is no package called [‘'\"]([^’'\"]+)",
    r"non c'è alcun pacchetto chiamato [‘'\"]([^’'\"]+)",
    r"No module named [‘'\"]([^’'\".]+)",
    r"package [‘'\"]([^’'\"]+)[’'\"] required by .* could not be found",
]
FILE_ERROR = re.compile(r"(cannot open file|No such file or directory|does not exist|FileNotFoundError|cannot open the connection|'.*' does not exist in current working directory)", re.I)


def order(scripts):
    def key(p):
        m = re.match(r"^(\d+)", p.name)
        return (0, int(m.group(1)), str(p)) if m else (1, 0, str(p))
    return sorted(scripts, key=key)


def command(path):
    ext = path.suffix.lower()
    if ext == ".r":
        return ["Rscript", "--no-save", "--no-restore", str(path)] if shutil.which("Rscript") else None
    if ext == ".rmd":
        return ["Rscript", "-e", f"rmarkdown::render({json.dumps(str(path))}, quiet = TRUE)"] if shutil.which("Rscript") else None
    if ext == ".qmd":
        q = shutil.which("quarto") or next((p for p in ["/Applications/RStudio.app/Contents/Resources/app/quarto/bin/quarto",
                                                         "/usr/local/bin/quarto", "/opt/quarto/bin/quarto"] if Path(p).exists()), None)
        return [q, "render", str(path)] if q else None
    if ext == ".py":
        return [sys.executable, str(path)]
    if ext == ".ipynb":
        j = shutil.which("jupyter")
        return [j, "nbconvert", "--to", "notebook", "--execute", "--output", path.stem + "_executed", str(path)] if j else None
    return None


def snapshot(root):
    return {str(p.relative_to(root)): p.stat().st_mtime for p in root.rglob("*") if p.is_file()}


def run_one(cmd, cwd, timeout):
    t0 = time.time()
    try:
        # English messages, so that errors read the same on every machine
        env = {**os.environ, "LANGUAGE": "en", "LC_MESSAGES": "en_US.UTF-8"}
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, env=env)
        return p.returncode, p.stdout, p.stderr, round(time.time() - t0, 1)
    except subprocess.TimeoutExpired as e:
        return "timeout", e.stdout or "", e.stderr or "", round(time.time() - t0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("scripts", nargs="*")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy and print its path")
    ap.add_argument("--logs", help="folder where to save each script's printed output (<script>.log)")
    ap.add_argument("--in-place", action="store_true",
                    help="run in the folder itself: only for the deposit version built by build_deposit.py")
    args = ap.parse_args()

    src = Path(args.folder).expanduser().resolve()
    if args.in_place:
        tmp, work = None, src
    else:
        tmp = Path(tempfile.mkdtemp(prefix="fair-run-"))
        work = tmp / src.name
        shutil.copytree(src, work, ignore=IGNORE, symlinks=True)
    logs = Path(args.logs).expanduser().resolve() if args.logs else None
    if logs:
        logs.mkdir(parents=True, exist_ok=True)

    if args.scripts:
        scripts = [work / s for s in args.scripts]
    else:
        scripts = [p for p in work.rglob("*") if p.is_file() and p.suffix.lower() in RUNNABLE
                   and not any(part in SKIP_DIRS for part in p.relative_to(work).parts)]
        scripts = order(scripts)

    env_info = {"Rscript": shutil.which("Rscript"), "python": sys.executable}
    if env_info["Rscript"]:
        v = subprocess.run(["Rscript", "-e", "cat(R.version.string)"], capture_output=True, text=True)
        env_info["R_version"] = v.stdout.strip()

    results = []
    for s in scripts:
        relp = str(s.relative_to(work))
        cmd = command(s)
        if cmd is None:
            results.append({"script": relp, "status": "not run", "reason": f"no interpreter found for {s.suffix}"})
            continue
        before = snapshot(work)
        code, out, err, dur = run_one(cmd, work, args.timeout)
        res = {"script": relp, "cwd": "project root", "exit": code, "seconds": dur}
        if code != 0 and FILE_ERROR.search(err or "") and s.parent != work:
            code2, out2, err2, dur2 = run_one(cmd, s.parent, args.timeout)
            if code2 == 0:
                res = {"script": relp, "cwd": "script folder", "exit": 0, "seconds": dur2,
                       "note": "fails from the project root, works only when run from its own folder",
                       "error_from_root": (err or "").strip().splitlines()[-8:]}
                out, err, code = out2, err2, 0
        res["status"] = "ok" if code == 0 else ("timeout" if code == "timeout" else "error")
        if code != 0:
            res["error_tail"] = (err or "").strip().splitlines()[-25:]
        missing = sorted({m for pat in MISSING_PATTERNS for m in re.findall(pat, err or "")})
        if missing:
            res["missing_packages"] = missing
        warn = re.findall(r"(?m)^Warning message[s]?:?.*$", err or "")
        if warn and code == 0:
            res["n_warnings"] = len(warn)
        after = snapshot(work)
        res["files_created"] = sorted(f for f in after if f not in before)[:40]
        res["files_modified"] = sorted(f for f in after if f in before and after[f] != before[f])[:40]
        if logs:
            log = logs / (relp.replace("/", "__") + ".log")
            log.write_text((out or "") + "\n--- messages and errors ---\n" + (err or ""))
            res["log"] = str(log)
        results.append(res)

    where = "(in place)" if args.in_place else (str(work) if args.keep else "(deleted)")
    print(json.dumps({"copy": where, "environment": env_info,
                      "results": results}, indent=1, ensure_ascii=False))
    if tmp and not args.keep:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
