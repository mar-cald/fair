#!/usr/bin/env python3
"""The checks of step 1 that run programs, in one call, after the scan and the
triage:

  python3 check_all.py <project-folder> --tmp <tmp> [--areas code,manuscript]
                       [--scripts s1.R s2.R ...] [--timeout 600] [--manuscript <file>]

- code: runs the scripts in a copy (run_code.py, with the setwd() rerun), logs
  in <tmp>/logs (and <tmp>/logs_fixed when setwd() had to be removed);
- manuscript: extracts the text (<tmp>/manuscript.txt), checks it against
  itself (participant flow, group sizes, percentages, degrees of freedom,
  declared scales), and looks for its statistics in the output of the code:
  the logs of the run that worked, or the outputs already in the folder when
  the code was not run.

It prints one short summary per area, the same each program prints alone, and
saves the details in <tmp> (run_code.json, manuscript_internal.json,
numbers.json). The manuscript is the one the scan found (<tmp>/fair_scan.json),
unless --manuscript names another. Areas not given are not checked.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUTPUT_DIRS = ("output", "outputs", "results", "risultati", "tables", "tabelle")


def run(args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


def short_internal(o):
    lines = []
    for f in o.get("findings", []):
        lines.append(f"- {f['check']}: {f['status']}: {f.get('numbers', '')} — \"{f.get('sentence', '')[:110]}\"")
    if o.get("scales_declared"):
        lines.append("- response scales declared: " + "; ".join(
            f"{s['scale']} (\"{s['sentence'][:60]}\")" for s in o["scales_declared"][:6]))
    if o.get("age_ranges_declared"):
        lines.append("- age ranges declared: " + "; ".join(
            str(a.get("range", a)) for a in o["age_ranges_declared"][:4]))
    if o.get("n_stated"):
        lines.append("- N stated in the text: " + ", ".join(f"{k} ({v}×)" for k, v in o["n_stated"].items()))
    return "\n".join(lines) or "- nothing found by the text checks"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--tmp", required=True)
    ap.add_argument("--areas", default="code,manuscript")
    ap.add_argument("--scripts", nargs="*", default=[])
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--manuscript")
    a = ap.parse_args()
    root, tmp = Path(a.folder).expanduser().resolve(), Path(a.tmp).expanduser().resolve()
    tmp.mkdir(parents=True, exist_ok=True)
    areas = {x.strip() for x in a.areas.split(",") if x.strip()}
    scan = {}
    sp = tmp / "fair_scan.json"
    if sp.exists():
        scan = json.loads(sp.read_text())
    out = []

    logs_used = None
    if "code" in areas:
        if scan and not (scan.get("materials_present") or {}).get("code"):
            out.append("## Code\n- no code in the folder")
        else:
            logs = tmp / "logs"
            r = run([HERE / "run_code.py", root, *a.scripts, "--timeout", a.timeout, "--logs", logs,
                     "--out", logs / "run_code.json"])
            out.append("## Code\n" + (r.stdout.strip() or r.stderr.strip()[-800:]))
            try:
                rc = json.loads((logs / "run_code.json").read_text())
                ok = sum(1 for x in rc["results"] if x["status"] == "ok")
                fx = rc.get("after_removing_setwd")
                ok2 = sum(1 for x in fx["results"] if x["status"] == "ok") if fx else -1
                logs_used = Path(fx["logs"]) if fx and fx.get("logs") and ok2 > ok else logs
            except (OSError, ValueError, KeyError):
                logs_used = logs

    if "manuscript" in areas:
        ms = Path(a.manuscript) if a.manuscript else None
        if not ms and scan.get("manuscripts"):
            ms = root / scan["manuscripts"][0]["file"]
        guessed = ""
        if not ms:
            # a manuscript the scan did not recognise by its name ('mauscript.pdf'): if there is
            # exactly one document of a manuscript type, use it, and say so
            docs = [d for d in (scan.get("other_documents") or {}).get("files", [])
                    if Path(d).suffix.lower() in (".pdf", ".docx", ".odt", ".md", ".qmd", ".rmd", ".tex", ".html")]
            if len(docs) == 1:
                ms, guessed = root / docs[0], " (not recognised by its name: check it is the manuscript)"
        if not ms or not ms.exists():
            out.append("## Manuscript\n- no manuscript found: give one with --manuscript")
        else:
            txt = tmp / "manuscript.txt"
            r = run([HERE / "manuscript_numbers.py", "text", ms, "--out", txt])
            if not txt.exists():
                out.append(f"## Manuscript\n- text not extracted from {ms.name}: {r.stderr.strip()[-300:]} "
                           "(read it with your own tool, save it as manuscript.txt, rerun with --areas manuscript)")
            else:
                ri = run([HERE / "manuscript_numbers.py", "internal", txt])
                (tmp / "manuscript_internal.json").write_text(ri.stdout)
                try:
                    internal = short_internal(json.loads(ri.stdout))
                except ValueError:
                    internal = ri.stderr.strip()[-300:]
                outputs = [p for p in ([logs_used] if logs_used and logs_used.exists() else []) +
                           [root / d for d in OUTPUT_DIRS if (root / d).is_dir()]]
                if outputs:
                    rcheck = run([HERE / "manuscript_numbers.py", "check", txt, *outputs,
                                  "--out", tmp / "numbers.json"])
                    where = ", ".join(str(p) for p in outputs)
                    check = f"(searched in: {where})\n" + (rcheck.stdout.strip() or rcheck.stderr.strip()[-400:])
                else:
                    check = ("no output to search: the code was not run here and the folder has no output "
                             "folder. Recompute from the data what can be recomputed (recompute.py)")
                out.append(f"## Manuscript ({ms.name}{guessed})\nText checked against itself:\n{internal}\n\n"
                           f"Numbers against the output: {check}")

    print("\n\n".join(out) if out else "nothing to do: give --areas code and/or manuscript")


if __name__ == "__main__":
    main()
