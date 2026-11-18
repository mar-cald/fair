#!/usr/bin/env python3
"""The first thing fair-check runs: is there personal data in the folder?

  python3 privacy_check.py <project-folder> --tmp <tmp>
  python3 privacy_check.py <project-folder> --tmp <tmp> --copy-without <dest>

It reads every file on this computer and prints ONLY what is safe to send to
the AI service: file names, column names, the kind of problem and counts.
Never a value. The assistant reads this output, and the output is all that
leaves the computer at this point.

It looks for (with the scanner's rules): names, e-mails, phone numbers, tax
codes, addresses, IP addresses, coordinates, dates of birth (also in a column
called age), recruitment-platform IDs (Prolific, MTurk, Gorilla Public ID),
participant IDs made of letters (initials?), absolute paths with a user name,
free text; and how many participants are the only one with their combination
of indirect identifiers (age, gender, school, class...). Data files it cannot
read here (Excel without openpyxl, SPSS without pyreadstat...) are listed:
nothing is known about them.

The last line is the verdict:
  STOP      possible personal data, or data files that could not be checked:
            the assistant must not open the data until the researcher decides
  ASK       only combinations of indirect identifiers: the same, said as a question
  CONTINUE  nothing found (which is not a proof: the rules can miss things)

The whole scan is saved in <tmp>/fair_scan.json and its summary in
<tmp>/fair_scan_summary.md, so step 0 does not scan again. The summary can
show some values (IDs used as examples): read it only after the verdict, or
after the researcher has decided.

--copy-without <dest> writes a copy of the folder without the columns flagged
as direct identifiers, in the delimited text files (.csv, .tsv, .txt) it can
rewrite here; the original is never touched. Files it cannot rewrite are
listed: remove those columns by hand. Then check the copy.
"""

import argparse
import csv
import io
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fair_scan  # noqa: E402
from summary import summarise  # noqa: E402

UNSURE = ("free-text", "initials or names?")  # flags that need a look: still a stop, but said as such


def entries(report):
    """(file, [(column, flags)], extra notes) for every table with something personal."""
    for t in report.get("data", []):
        name = t.get("file_set") or t.get("file", "?")
        cols = []
        for p in t.get("possible_personal_data", []) or []:
            if isinstance(p, dict):
                cols.append((p.get("column", "?"), p.get("flags", [])))
            else:
                cols.append((str(p), ["flagged"]))
        notes = []
        if t.get("participant_id_column_is_personal"):
            notes.append(t["participant_id_column_is_personal"])
        ind = t.get("indirect_identifiers") or {}
        if ind.get("unique_combinations"):
            notes.append(f"indirect identifiers ({', '.join(ind.get('columns', []))}): "
                         f"{ind['unique_combinations']} of {ind.get('participants', '?')} participants are the only "
                         "one with their combination")
        if cols or notes:
            yield name, cols, notes, t


R_READERS = {".xlsx": "readxl", ".xls": "readxl", ".sav": "haven", ".dta": "haven", ".sas7bdat": "haven"}


def convert_with_r(root, tmp, report):
    """Data files Python cannot read here (Excel without openpyxl, SPSS without
    pyreadstat): if R has readxl or haven, convert them to CSV in <tmp>, on this
    computer, and check those. Returns the files converted."""
    import subprocess
    rscript = shutil.which("Rscript")
    left, done = [], []
    for x in report.get("data_not_read") or []:
        rel = x.get("file", "")
        src = root / rel
        pkg = R_READERS.get(src.suffix.lower())
        if not (rscript and pkg and src.exists()):
            left.append(x)
            continue
        outdir = tmp / "converted_for_privacy_check"
        outdir.mkdir(parents=True, exist_ok=True)
        stem = rel.replace("/", "__")
        code = (f'f <- {json_str(str(src))}; o <- {json_str(str(outdir / stem))}; '
                + ('for (s in readxl::excel_sheets(f)) write.csv(readxl::read_excel(f, sheet = s), '
                   'paste0(o, "__", gsub("[^A-Za-z0-9]", "_", s), ".csv"), row.names = FALSE)'
                   if pkg == "readxl" else
                   'write.csv(as.data.frame(lapply(haven::read_dta(f), as.vector)), paste0(o, ".csv"), row.names = FALSE)'
                   if src.suffix.lower() == ".dta" else
                   'write.csv(as.data.frame(lapply(haven::read_sav(f), as.vector)), paste0(o, ".csv"), row.names = FALSE)'))
        r = subprocess.run([rscript, "-e", code], capture_output=True, text=True, timeout=300)
        made = sorted(outdir.glob(stem + "*.csv"))
        if r.returncode != 0 or not made:
            left.append(x)
            continue
        for csvf in made:
            t = fair_scan.scan_table(csvf, outdir)
            sheet = csvf.name[len(stem):].strip("_").removesuffix(".csv") if len(made) > 1 else ""
            t["file"] = rel + (f" [{sheet}]" if sheet else "") + " (read with R)"
            for k in [k for k in t if k.startswith("_")]:
                t.pop(k)
            report.setdefault("data", []).append(t)
        done.append(rel)
    report["data_not_read"] = left
    return done


def json_str(s):
    import json
    return json.dumps(s)


def copy_without(root, dest, report):
    """Copy the folder; drop the flagged columns from the delimited text files."""
    if dest.exists():
        sys.exit(f"{dest} already exists: give a new folder")
    shutil.copytree(root, dest, ignore=shutil.ignore_patterns(".git", ".DS_Store"))
    done, by_hand = [], []
    for name, cols, notes, t in entries(report):
        drop = {c for c, flags in cols if not any(u in " ".join(flags) for u in UNSURE)}
        if not drop:
            continue
        files = t.get("files") or [t.get("file")]
        for f in files:
            rel = f.split(" [")[0]
            target = dest / rel
            if target.suffix.lower() not in (".csv", ".tsv", ".txt") or not target.exists():
                by_hand.append(f"{rel}: {', '.join(sorted(drop))}")
                continue
            text = target.read_text(encoding="utf-8-sig", errors="replace")
            try:
                dialect = csv.Sniffer().sniff(text[:5000], delimiters=",;\t")
            except csv.Error:
                by_hand.append(f"{rel}: {', '.join(sorted(drop))}")
                continue
            rows = list(csv.reader(io.StringIO(text), dialect))
            if not rows:
                continue
            keep = [j for j, h in enumerate(rows[0]) if h.strip() not in drop]
            out = io.StringIO()
            w = csv.writer(out, delimiter=dialect.delimiter, lineterminator="\n")
            for r in rows:
                w.writerow([r[j] if j < len(r) else "" for j in keep])
            target.write_text(out.getvalue(), encoding="utf-8")
            done.append(f"{rel}: removed {', '.join(sorted(drop & set(h.strip() for h in rows[0])))}")
    return done, by_hand


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--tmp", required=True)
    ap.add_argument("--copy-without", help="write a copy without the columns flagged as direct identifiers")
    a = ap.parse_args()
    root = Path(a.folder).expanduser().resolve()
    tmp = Path(a.tmp).expanduser().resolve()
    tmp.mkdir(parents=True, exist_ok=True)
    report = fair_scan.scan(root)
    converted = convert_with_r(root, tmp, report)
    import json
    (tmp / "fair_scan.json").write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str))
    (tmp / "fair_scan_summary.md").write_text(summarise(report, tmp / "fair_scan.json"))

    lines = [f"privacy_check: {report.get('n_files', '?')} files read on this computer. "
             "Only names of files and columns, kinds of problem and counts are shown here: no value."]
    if converted:
        lines.append("Read with R on this computer (Python cannot read them here): " + ", ".join(converted))
    stop = ask = False
    found = list(entries(report))
    if found:
        lines.append("\nPossible personal data:")
        for name, cols, notes, _ in found:
            lines.append(f"- `{name}`")
            for c, flags in cols:
                lines.append(f"  - column `{c}`: {'; '.join(flags)[:200]}")
                stop = True
            for n in notes:
                lines.append(f"  - {n[:220]}")
                if n.startswith("indirect identifiers"):
                    ask = True
                else:
                    stop = True
    not_read = report.get("data_not_read") or []
    if not_read:
        stop = True
        lines.append("\nData files not checked, because they cannot be read here (nothing is known about them):")
        for x in not_read:
            lines.append(f"- `{x.get('file')}`: {str(x.get('reason', ''))[:140]}")

    if a.copy_without:
        dest = Path(a.copy_without).expanduser().resolve()
        done, by_hand = copy_without(root, dest, report)
        lines.append(f"\nCopy written to {dest} (the original is unchanged):")
        lines += [f"- {x}" for x in done] or ["- no column removed"]
        if by_hand:
            lines.append("To remove by hand in the copy (files this script cannot rewrite):")
            lines += [f"- {x}" for x in by_hand]
        lines.append("Run privacy_check.py on the copy before going on.")

    if stop:
        what = []
        if found:
            what.append("remove those columns (or work on a copy without them: --copy-without)")
        if not_read:
            what.append("check the unread files by hand, or export them to CSV")
        lines.append("\nVERDICT: STOP. Do not open, list or summarise the data files, and do not run other "
                     "checks, until the researcher decides: " + "; ".join(what) +
                     "; or confirm that sharing these data with the AI service is allowed; or stop here.")
    elif ask:
        lines.append("\nVERDICT: ASK. No direct identifier, but combinations of indirect identifiers that "
                     "single people out. Do not open the data until the researcher says whether these can go "
                     "to the AI service (or makes them coarser: age in bands, no class section).")
    else:
        lines.append("\nVERDICT: CONTINUE. No personal data found by these rules (not a proof). "
                     f"Step 0: read the summary in {tmp / 'fair_scan_summary.md'}.")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
