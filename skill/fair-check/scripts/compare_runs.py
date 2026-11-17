#!/usr/bin/env python3
"""Compare the outputs of two runs of the same code: before and after a
correction (to the data or to a script), made in a copy of the project.

  python3 compare_runs.py <before> <after> [--manuscript <manuscript.txt>] [--out changes.json]

<before> and <after> are folders (the --logs of run_code.py, an output/
folder) or single files. Files are paired by their path inside each folder;
.log .txt .csv .tsv .md .html .json are compared line by line: lines whose
words are the same and whose numbers differ are listed, with the old and the
new numbers. With --manuscript (text from `manuscript_numbers.py text`), the
changed numbers that the manuscript reports, on a line that names the same
statistic, are listed first, with their sentence: these are the results the
correction changes. It prints a short summary; --out saves every change.
"""

import argparse
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from manuscript_numbers import context_rx, find_stats  # noqa: E402

EXT = {".log", ".txt", ".csv", ".tsv", ".md", ".html", ".json", ".out"}
NUMBER = re.compile(r"(?<![\w.])[-−]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?(?![\w.])")
MAX_LINES = 20000


def files_of(p):
    p = Path(p)
    if p.is_file():
        return {p.name: p}
    # run_code.json holds durations and paths of the run, not results
    return {str(f.relative_to(p)): f for f in sorted(p.rglob("*"))
            if f.is_file() and f.suffix.lower() in EXT and f.name != "run_code.json"}


def nums(line):
    out = []
    for m in NUMBER.finditer(line):
        try:
            out.append(float(m.group(0).replace("−", "-")))
        except ValueError:
            pass
    return out


def mask(line):
    return NUMBER.sub("#", line.strip())


def compare_file(a, b):
    la = a.read_text(errors="replace").splitlines()[:MAX_LINES]
    lb = b.read_text(errors="replace").splitlines()[:MAX_LINES]
    ma, mb = [mask(x) for x in la], [mask(x) for x in lb]
    changes, structure = [], 0
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, ma, mb, autojunk=False).get_opcodes():
        if tag == "equal":
            for i, j in zip(range(i1, i2), range(j1, j2)):
                na, nb = nums(la[i]), nums(lb[j])
                if len(na) == len(nb) and any(abs(x - y) > 1e-12 * max(1, abs(x)) for x, y in zip(na, nb)):
                    changes.append({"line_before": i + 1, "line_after": j + 1, "before": la[i].strip()[:200],
                                    "after": lb[j].strip()[:200],
                                    "pairs": [(x, y) for x, y in zip(na, nb) if abs(x - y) > 1e-12 * max(1, abs(x))]})
        else:
            structure += max(i2 - i1, j2 - j1)
    return changes, structure


def reported_hits(changes, fname, stats):
    """Changed numbers the manuscript reports, on a line naming the statistic."""
    hits = []
    for c in changes:
        for s in stats:
            if s.get("op") != "=":
                continue
            ctx = context_rx(s["label"])
            if not ctx or not ctx.search(c["before"]):
                continue
            for x, y in c["pairs"]:
                if abs(x - s["value"]) <= s["tol"]:
                    hits.append({"reported": s["reported"], "sentence": s["sentence"][:200],
                                 "before": x, "after": y, "where": f"{fname}:{c['line_after']}"})
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("before")
    ap.add_argument("after")
    ap.add_argument("--manuscript")
    ap.add_argument("--out")
    a = ap.parse_args()
    fa, fb = files_of(a.before), files_of(a.after)
    stats = find_stats(Path(a.manuscript).read_text(errors="replace"))[0] if a.manuscript else []
    report = {"files_compared": 0, "only_before": sorted(set(fa) - set(fb)), "only_after": sorted(set(fb) - set(fa)),
              "files": {}, "reported_numbers_changed": []}
    for name in sorted(set(fa) & set(fb)):
        changes, structure = compare_file(fa[name], fb[name])
        report["files_compared"] += 1
        if changes or structure:
            report["files"][name] = {"lines_with_changed_numbers": changes, "lines_added_or_removed": structure}
            report["reported_numbers_changed"] += reported_hits(changes, name, stats)
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False))

    changed = {k: v for k, v in report["files"].items() if v["lines_with_changed_numbers"]}
    print(f"compare_runs: {report['files_compared']} files compared, {len(changed)} with changed numbers"
          + (f". Full detail: {a.out}" if a.out else ""))
    if a.manuscript:
        hits = report["reported_numbers_changed"]
        print(f"Numbers reported in the manuscript that change ({len(hits)}):" if hits else
              "No number reported in the manuscript changes (on a line that names the same statistic).")
        for h in hits[:30]:
            print(f"- {h['reported']}: {h['before']:g} → {h['after']:g} ({h['where']}) — \"{h['sentence'][:110]}\"")
    for name, v in changed.items():
        cs = v["lines_with_changed_numbers"]
        print(f"{name}: {len(cs)} lines with changed numbers" +
              (f", {v['lines_added_or_removed']} lines added or removed" if v["lines_added_or_removed"] else ""))
        for c in cs[:5]:
            print(f"  line {c['line_after']}: " + ", ".join(f"{x:g} → {y:g}" for x, y in c["pairs"][:6]) +
                  f"   | {c['after'][:90]}")
        if len(cs) > 5:
            print(f"  … {len(cs) - 5} more lines")
    for name, v in report["files"].items():
        if not v["lines_with_changed_numbers"]:
            print(f"{name}: {v['lines_added_or_removed']} lines added or removed, no number changed on the same lines")
    for k, lab in (("only_before", "only in the first run"), ("only_after", "only in the second run")):
        if report[k]:
            print(f"Files {lab}: " + ", ".join(report[k][:10]))


if __name__ == "__main__":
    main()
