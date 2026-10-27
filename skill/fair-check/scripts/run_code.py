#!/usr/bin/env python3
"""Run a project's scripts in a throw-away copy of the folder.

Usage: python3 run_code.py <project_folder> [script ...] [--timeout 600]

Without explicit scripts, runs every R / Rmd / qmd / Python / notebook file in
order: numbered files first (01_, 02_ ...), then the rest alphabetically.
Pass scripts explicitly (paths relative to the project) when the README gives
a different order. Experiment scripts (PsychoPy, jsPsych, OpenSesame ...) are
part of the instrument, not of the analysis: they are listed as "not run".

The original folder is never touched: everything runs in a temporary copy,
from the project root (like an RStudio project). If a script fails because it
cannot find a file, it is retried from its own folder, and the result says so.

Prints JSON: per script, the command, exit status, duration, the last lines of
the error output, packages reported as missing, and the files it created.
Packages are never installed by this script.

--timeout is per script (default 600 s). A script that reaches it is stopped
together with every process it started (e.g. MCMC chains run in parallel), and
reported with status "timeout" and what it printed until then.

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
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from software import experiment_role  # noqa: E402

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


def _text(b):
    """Output of a script as text, whatever its encoding."""
    if b is None:
        return ""
    if isinstance(b, str):
        return b
    for enc in ("utf-8", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1")


def _stop(proc):
    """Stop a script and every process it started (parallel chains, workers)."""
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGTERM)
        else:
            proc.terminate()
        proc.wait(timeout=10)
    except Exception:  # noqa: BLE001
        pass
    if proc.poll() is None:
        try:
            if os.name == "posix":
                os.killpg(proc.pid, signal.SIGKILL)
            else:
                proc.kill()
        except Exception:  # noqa: BLE001
            pass
    if os.name == "posix":  # children that outlived the group leader
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:  # noqa: BLE001
            pass


def run_one(cmd, cwd, timeout):
    """Run one command; returns (exit code or "timeout", stdout, stderr, seconds)."""
    t0 = time.time()
    # English messages, so that errors read the same on every machine
    env = {**os.environ, "LANGUAGE": "en", "LC_MESSAGES": "en_US.UTF-8"}
    kw = {"start_new_session": True} if os.name == "posix" else \
        {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw)
    except OSError as e:
        return 127, "", f"could not start {cmd[0]}: {e}", 0.0
    try:
        out, err = proc.communicate(timeout=timeout)
        code = proc.returncode
    except subprocess.TimeoutExpired:
        _stop(proc)
        try:
            out, err = proc.communicate(timeout=10)
        except Exception:  # noqa: BLE001
            out, err = b"", b""
        code = "timeout"
    return code, _text(out), _text(err), round(time.time() - t0, 1)


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

    results = []
    if args.scripts:
        scripts = [work / s for s in args.scripts]
        missing = [s for s in scripts if not s.is_file()]
        if missing:
            sys.exit("Not found in the project: " + ", ".join(str(m.relative_to(work)) for m in missing))
    else:
        scripts = [p for p in work.rglob("*") if p.is_file() and p.suffix.lower() in RUNNABLE
                   and not any(part in SKIP_DIRS for part in p.relative_to(work).parts)]
        kept = []
        for p in order(scripts):
            role = experiment_role(p, p.read_text(errors="replace") if p.suffix.lower() in (".py",) else "")
            if role:
                results.append({"script": str(p.relative_to(work)), "status": "not run",
                                "reason": f"{role}: part of the experiment, not of the analysis"})
            else:
                kept.append(p)
        scripts = kept

    env_info = {"Rscript": shutil.which("Rscript"), "python": sys.executable}
    if env_info["Rscript"]:
        v = subprocess.run(["Rscript", "-e", "cat(R.version.string)"], capture_output=True, text=True)
        env_info["R_version"] = v.stdout.strip()

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
        if code == "timeout":
            res["note"] = (f"stopped after {args.timeout} s, with every process it started; "
                           "it may need a longer --timeout, or it may hang")
            res["output_tail"] = ((out or "") + "\n" + (err or "")).strip().splitlines()[-15:]
        elif code != 0:
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
