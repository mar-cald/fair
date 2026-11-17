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
the error output, packages reported as missing, the files it created, and the
files whose content it changed (compared by SHA-256: a file rewritten with the
same content is listed apart, as files_rewritten_same_content).
Packages are never installed into the user's R library by this script.

--timeout is per script (default 600 s). A script that reaches it is stopped
together with every process it started (e.g. MCMC chains run in parallel), and
reported with status "timeout" and what it printed until then.

Projects that use renv (renv.lock, plus renv/activate.R started by .Rprofile)
get their packages the renv way before the scripts run: renv::restore() in
the copy installs the versions in renv.lock into the copy's own library (and
renv's cache), not into the user's R library; renv itself is installed first
if needed. --no-renv skips this; --renv-timeout limits it (default 1800 s).

--logs DIR saves what each script prints (DIR/<script>.log), to compare with
the numbers in a manuscript.

What it prints is short, one line per script: status, the probable cause of a
failure (missing package, setwd(), an absolute path, a missing file), and
whether it failed after an earlier script had already failed (then it is
probably a consequence). If a script stops because of setwd() (or os.chdir()),
everything is run again in a second copy with those lines commented out, and
both results are reported ("fails as deposited; with setwd() removed, it
runs"); --no-fix skips this. The full JSON goes to --out (default:
DIR/run_code.json with --logs, otherwise a temporary file); --json prints it
instead of the short version. --in-place runs in the folder itself instead of a
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


def sha256(path, chunk=1 << 20):
    import hashlib  # noqa: PLC0415
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def hashes(root, limit=200_000_000):
    """Content fingerprints of the files present before the scripts run (files up to `limit` bytes)."""
    out = {}
    for p in root.rglob("*"):
        if p.is_file() and p.stat().st_size <= limit and ".Rproj.user" not in p.parts and "renv" not in p.parts[:1]:
            try:
                out[str(p.relative_to(root))] = sha256(p)
            except OSError:
                pass
    return out


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


ERROR_LINE = re.compile(r"(?i)^(error|errore|.*Error[: ]|Traceback|Execution halted|Quitting from)")


def cause(res):
    """The probable cause of a failure, from the error output: a guess to verify."""
    err = "\n".join(res.get("error_tail") or res.get("error_from_root") or [])
    if res.get("missing_packages"):
        return "missing package: " + ", ".join(res["missing_packages"])
    if re.search(r"setwd|cannot change working directory", err):
        return "portability: setwd()"
    m = FILE_ERROR.search(err)
    if m:
        if re.search(r"(/Users/|/home/|[A-Za-z]:[\\/]|~/)", err):
            return "portability: an absolute path"
        f = re.search(r"[‘'\"]([^’'\"]+\.\w{1,6})[’'\"]", err)
        return "a file it reads is missing" + (f": {f.group(1)}" if f else "")
    return None


def annotate(results):
    """Probable cause of each failure; failures after the first one are flagged
    as probable consequences (a later script often fails only because an
    earlier one did not write its outputs)."""
    first = None
    for r in results:
        if r.get("status") not in ("error", "timeout"):
            continue
        c = cause(r)
        if c:
            r["probable_cause"] = c
        tail = [x.strip() for x in (r.get("error_tail") or []) if x.strip()]
        idx = next((i for i, x in enumerate(tail) if ERROR_LINE.search(x)), None)
        if idx is None and tail:
            idx = len(tail) - 1
        if idx is not None:
            line = tail[idx]
            if line.endswith(":") and idx + 1 < len(tail):  # R puts the message on the next line
                line += " " + tail[idx + 1]
            r["error_line"] = line[:200]
        # only a missing file (or an unknown cause) can come from an earlier failure;
        # a missing package or setwd() is the script's own problem
        if first and (not c or c.startswith("a file it reads is missing")):
            r["after_failure_of"] = first
        if not first:
            first = r["script"]


def short_report(out, results, dest, logs):
    env = out["environment"]
    head = f"run_code: {len(results)} scripts, copy {out['copy']}. " + \
        (env.get("R_version") or "no R") + f". Full detail: {dest}"
    lines = [head]
    if out.get("renv"):
        rv = out["renv"]
        lines.append(f"renv: restore {rv.get('restore')}" + (f" ({rv['seconds']} s)" if rv.get("seconds") else "") +
                     (f"; {rv['note']}" if rv.get("note") else "") +
                     (f"; last line: {rv['error_tail'][-1]}" if rv.get("error_tail") else ""))
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
        s = f"- {r['script']} — {r['status']}"
        if r["status"] == "not run":
            lines.append(s + f": {r.get('reason', '')}")
            continue
        s += f" ({r.get('seconds')} s)"
        if r.get("after_failure_of"):
            s += f", after the failure of {r['after_failure_of']} (probably a consequence)"
        if r.get("probable_cause"):
            s += f" · probable cause: {r['probable_cause']}"
        if r.get("error_line"):
            s += f" · {r['error_line']}"
        if r.get("note"):
            s += f" · {r['note']}"
        if r.get("n_warnings"):
            s += f" · {r['n_warnings']} warnings"
        created = r.get("files_created") or []
        if created:
            s += f" · created {len(created)}: " + ", ".join(created[:4]) + (" …" if len(created) > 4 else "")
        mod = r.get("files_modified") or []
        raw = [f for f in mod if re.search(r"(^|/)raw(/|$)", f)]
        if raw:
            s += " · MODIFIES RAW DATA: " + ", ".join(raw[:4])
        elif mod:
            s += f" · modified {len(mod)}: " + ", ".join(mod[:4]) + (" …" if len(mod) > 4 else "")
        lines.append(s)
    lines.append("Totals: " + ", ".join(f"{v} {k}" for k, v in counts.items()))
    if logs:
        lines.append(f"Logs: {logs}")
    fx = out.get("after_removing_setwd")
    if fx:
        lines.append("")
        lines.append("Rerun in a second copy with setwd() removed (" + "; ".join(fx["removed"][:4]) + "):")
        for r in fx["results"]:
            s = f"- {r['script']} — {r['status']}"
            if r.get("after_failure_of"):
                s += f", after the failure of {r['after_failure_of']}"
            if r.get("probable_cause"):
                s += f" · probable cause: {r['probable_cause']}"
            if r.get("error_line") and r["status"] != "ok":
                s += f" · {r['error_line']}"
            lines.append(s)
        if fx.get("logs"):
            lines.append(f"Logs of this run (use them for the manuscript numbers): {fx['logs']}")
    return "\n".join(lines)


def run_scripts(work, scripts, timeout, logs):
    """Run each script from the project root of `work`; one result per script."""
    results = []
    content = hashes(work)  # to tell a file whose content changed from one rewritten identical
    for s in scripts:
        relp = str(s.relative_to(work))
        cmd = command(s)
        if cmd is None:
            results.append({"script": relp, "status": "not run", "reason": f"no interpreter found for {s.suffix}"})
            continue
        before = snapshot(work)
        code, out, err, dur = run_one(cmd, work, timeout)
        res = {"script": relp, "cwd": "project root", "exit": code, "seconds": dur}
        if code != 0 and FILE_ERROR.search(err or "") and s.parent != work:
            code2, out2, err2, dur2 = run_one(cmd, s.parent, timeout)
            if code2 == 0:
                res = {"script": relp, "cwd": "script folder", "exit": 0, "seconds": dur2,
                       "note": "fails from the project root, works only when run from its own folder",
                       "error_from_root": (err or "").strip().splitlines()[-8:]}
                out, err, code = out2, err2, 0
        res["status"] = "ok" if code == 0 else ("timeout" if code == "timeout" else "error")
        if code == "timeout":
            res["note"] = (f"stopped after {timeout} s, with every process it started; "
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
        touched = [f for f in after if f in before and after[f] != before[f]]
        changed, same = [], []
        for f in touched:
            if f in content:
                h = sha256(work / f)
                (same if h == content[f] else changed).append(f)
                content[f] = h
            else:
                changed.append(f)
        res["files_modified"] = sorted(changed)[:40]
        if same:
            res["files_rewritten_same_content"] = sorted(same)[:40]
        if logs:
            log = logs / (relp.replace("/", "__") + ".log")
            log.write_text((out or "") + "\n--- messages and errors ---\n" + (err or ""))
            res["log"] = str(log)
        results.append(res)
    return results


SETWD = re.compile(r"^(\s*)(setwd\s*\(.*|os\.chdir\s*\(.*)$")


def remove_setwd(work, scripts):
    """In a copy only: comment out setwd() / os.chdir() lines, which tie a script to
    one computer. Returns the lines removed, as 'file:line: text'."""
    removed = []
    for s in scripts:
        if s.suffix.lower() not in (".r", ".rmd", ".qmd", ".py"):
            continue
        lines = s.read_text(errors="replace").splitlines(keepends=True)
        changed = False
        for n, line in enumerate(lines):
            m = SETWD.match(line.rstrip("\n"))
            if m:
                removed.append(f"{s.relative_to(work)}:{n + 1}: {line.strip()[:120]}")
                lines[n] = f"{m.group(1)}# [fair-check, copy only] {m.group(2)}\n"
                changed = True
        if changed:
            s.write_text("".join(lines))
    return removed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("scripts", nargs="*")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--keep", action="store_true", help="keep the temporary copy and print its path")
    ap.add_argument("--logs", help="folder where to save each script's printed output (<script>.log)")
    ap.add_argument("--no-renv", action="store_true", help="do not run renv::restore() in renv projects")
    ap.add_argument("--renv-timeout", type=int, default=1800)
    ap.add_argument("--in-place", action="store_true",
                    help="run in the folder itself: only for the deposit version built by build_deposit.py")
    ap.add_argument("--out", help="where to save the full JSON")
    ap.add_argument("--json", action="store_true", help="print the full JSON instead of the short summary")
    ap.add_argument("--no-fix", action="store_true",
                    help="do not rerun with setwd() removed when a script stops because of it")
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

    renv = None
    uses_renv = (work / "renv.lock").is_file() and (work / "renv" / "activate.R").is_file()
    if uses_renv and env_info["Rscript"] and not args.no_renv:
        # .Rprofile activates renv (and installs renv itself if missing); restore installs renv.lock
        code, out, err, dur = run_one(["Rscript", "-e", "renv::restore(prompt = FALSE)"], work, args.renv_timeout)
        renv = {"restore": "ok" if code == 0 else ("timeout" if code == "timeout" else "error"), "seconds": dur}
        if code != 0:
            renv["error_tail"] = ((out or "") + "\n" + (err or "")).strip().splitlines()[-15:]
        if not (work / ".Rprofile").is_file():
            renv["note"] = "no .Rprofile: renv is not activated when the scripts run, they use the user's R library"
    elif uses_renv:
        renv = {"restore": "skipped" if args.no_renv else "no Rscript"}

    results += run_scripts(work, scripts, args.timeout, logs)

    where = "(in place)" if args.in_place else (str(work) if args.keep else "(deleted)")
    out = {"copy": where, "environment": env_info}
    if renv:
        out["renv"] = renv
    annotate(results)
    if (not args.no_fix and not args.in_place
            and any((r.get("probable_cause") or "").endswith("setwd()") for r in results)):
        # the portability fix, in a second copy: does the analysis run once setwd() is gone?
        tmp2 = Path(tempfile.mkdtemp(prefix="fair-run-fixed-"))
        work2 = tmp2 / src.name
        shutil.copytree(src, work2, ignore=IGNORE, symlinks=True)
        scripts2 = [work2 / s.relative_to(work) for s in scripts]
        removed = remove_setwd(work2, scripts2)
        logs2 = logs.parent / (logs.name + "_fixed") if logs else None
        if logs2:
            logs2.mkdir(parents=True, exist_ok=True)
        if uses_renv and env_info["Rscript"] and not args.no_renv:
            run_one(["Rscript", "-e", "renv::restore(prompt = FALSE)"], work2, args.renv_timeout)
        results2 = run_scripts(work2, scripts2, args.timeout, logs2)
        annotate(results2)
        out["after_removing_setwd"] = {"removed": removed, "logs": str(logs2) if logs2 else None,
                                       "copy": str(work2) if args.keep else "(deleted)", "results": results2}
        if not args.keep:
            shutil.rmtree(tmp2, ignore_errors=True)
    full = json.dumps({**out, "results": results}, indent=1, ensure_ascii=False)
    if args.out:
        dest = Path(args.out).expanduser().resolve()
    elif logs:
        dest = logs / "run_code.json"
    else:
        dest = Path(tempfile.mkstemp(prefix="fair-run-", suffix=".json")[1])
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(full)
    print(full if args.json else short_report(out, results, dest, logs))
    if tmp and not args.keep:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
