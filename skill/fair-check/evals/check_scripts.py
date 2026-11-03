#!/usr/bin/env python3
"""Quick check of the skill's Python scripts on the test folders in evals/*/files.

  python3 evals/check_scripts.py

No model, a few seconds: run it after changing anything in scripts/. Each line
is one thing the scanner (or a deposit helper) must find, or must not invent.
The cases themselves (prompt.md, graders/) test the whole skill with Claude.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import fair_scan  # noqa: E402

# GitHub refuses a Git LFS pointer without its file, so the fake one is written here
POINTER = HERE / "lfs-placeholder-only-where-true/files/sleep_models/data/processed/trials.rds"
POINTER.write_text("version https://git-lfs.github.com/spec/v1\n"
                   "oid sha256:4d7a2146c0bd2e1b0f6ad3ab2e9f0c1e5b6a7d8c9e0f1a2b3c4d5e6f7a8b9c0d\nsize 75219\n")

results = []


def check(label, ok):
    results.append(bool(ok))
    print(("ok    " if ok else "FAIL  ") + label)


def table(scan, name):
    return next(t for t in scan["data"] if t.get("file", "").endswith(name))


def col(t, name):
    return next(c for c in t["columns"] if c["name"] == name)


# 1. data only: scales, codings, accents, dates, copies, personal data
s = fair_scan.scan(HERE / "data-only-consistency/files/studio_diari")
q = table(s, "questionario.csv")
check("sleepiness 8 is not an issue (scale not documented)",
      not any("outside" in i for i in col(q, "sonnolenza").get("issues", [])))
check("item value 7 is 'to check', not an issue",
      col(q, "AN_4").get("to_check") and not any("outside" in i for i in col(q, "AN_4").get("issues", [])))
same = {c["name"] for c in s.get("same_name_different_values", {}).get("columns", [])}
check("gruppo coded ctrl/exp vs A/B", "gruppo" in same)
check("broken accents in diario.csv", col(table(s, "diario.csv"), "note").get("broken_accents"))
check("ambiguous day/month in diario.csv",
      any("day and month" in i for i in col(table(s, "diario.csv"), "data").get("issues", [])))
check("identical files found", any(len(g) == 2 for g in s.get("identical_files", {}).get("groups", [])))
check("dates of birth flagged as personal data",
      any("nascita" in json.dumps(p) for p in table(s, "partecipanti.csv").get("possible_personal_data", [])))

# 2. LFS: only the real pointer
s = fair_scan.scan(HERE / "lfs-placeholder-only-where-true/files/sleep_models")
lfs = [f["file"] for f in s.get("lfs_pointers", {}).get("files", [])]
check("trials.rds is an LFS pointer", lfs == ["data/processed/trials.rds"])
check("fit_sleep.rds is not", "models/fit_sleep.rds" not in lfs)

# 3. code order, packages, seeds, today's date
s = fair_scan.scan(HERE / "code-order-without-r/files/gonogo")
dep = s["code"].get("dependencies", {})
check("00_prep.R numbered before what it needs", any("ids_model.csv" in x for x in dep.get("numbered_before_what_they_need", [])))
check("circular dependency", set(dep.get("circular", {}).get("scripts", [])) == {"scripts/00_prep.R", "scripts/01_model.R"})
check("groups.csv written by no script", [x["file"] for x in dep.get("inputs_written_by_no_script", [])] == ["output/groups.csv"])
files = {c["file"]: c for c in s["code"]["files"]}
check("kable() without its package", any("kable" in x for x in files["scripts/00_prep.R"].get("functions_without_their_package", [])))
check("stan() without a seed", files["scripts/01_model.R"].get("randomness", {}).get("seed") is None)
check("Sys.Date() found", bool(files["scripts/00_prep.R"].get("uses_current_date")))
check("no false 'function without package' in 01_model.R", not files["scripts/01_model.R"].get("functions_without_their_package"))

# 4. manuscript numbers: long trial tables skipped
case = HERE / "manuscript-numbers-not-figures/files/attention_study"
with tempfile.TemporaryDirectory() as tmp:
    txt = Path(tmp) / "m.txt"
    subprocess.run([sys.executable, SCRIPTS / "manuscript_numbers.py", "text", case / "manuscript.md", "--out", txt],
                   check=True, capture_output=True)
    out = json.loads(subprocess.run([sys.executable, SCRIPTS / "manuscript_numbers.py", "check", txt, case],
                                    check=True, capture_output=True, text=True).stdout)
st = {(r["label"], r["reported"]): r["status"] for r in out["results"]}
check("t(39) = 2.45 found", any(k[0] == "t" and v == "found" for k, v in st.items()))
check("M = 0.87 not found", any("0.87" in k[1] and v == "not found" for k, v in st.items()))
check("trial-level table skipped", any("trials.csv" in f for f in out.get("tables_skipped", {}).get("files", [])))
check("the manuscript is not searched as an output", any("manuscript.md" in f for f in out.get("tables_skipped", {}).get("files", [])))

# deposit helpers: zip refuses pointers, copies verified, CITATION.cff
import build_deposit  # noqa: E402
with tempfile.TemporaryDirectory() as tmp:
    src = HERE / "lfs-placeholder-only-where-true/files/sleep_models"
    plan = {"files": [{"from": "data/sleep.csv", "to": "data/study-sleep_data.csv"},
                      {"from": "data/processed/trials.rds", "to": "data/trials.rds"},
                      {"from": "models/fit_sleep.rds", "to": "output/fit_sleep.rds"}]}
    out = Path(tmp) / "sleep_models_deposit"
    rep = build_deposit.build_deposit(src, plan, out)
    check("copies verified identical", rep.get("verified_identical_to_original") == 3)
    try:
        build_deposit.zip_deposit(out)
        check("zip refuses an LFS pointer", False)
    except ValueError:
        check("zip refuses an LFS pointer", True)
    t = build_deposit.write_citation(out, "Sleep models", ["Rossi, Anna, 0000-0002-1825-0097"], licenses=["CC0-1.0"])
    check("CITATION.cff written", "orcid.org/0000-0002-1825-0097" in t.read_text())
    target, n = build_deposit.write_checksums(out)
    check("checksums file lists every file", n == 4 and target.exists())
    (out / "data" / "trials.rds").unlink()
    z = subprocess.run([sys.executable, SCRIPTS / "build_deposit.py", "zip", out], capture_output=True, text=True)
    check("zip prints its MD5 for the Zenodo comparison", z.returncode == 0 and "MD5" in z.stdout)

print(f"\n{sum(results)}/{len(results)} passed")
sys.exit(0 if all(results) else 1)
