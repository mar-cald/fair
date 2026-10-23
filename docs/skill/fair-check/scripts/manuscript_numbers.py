#!/usr/bin/env python3
"""Compare the statistics reported in a manuscript with what the code prints.

  python3 manuscript_numbers.py text <manuscript> --out <manuscript.txt>
  python3 manuscript_numbers.py check <manuscript.txt> <output> [<output> ...]

`text` extracts plain text from .docx, .odt, .md, .qmd, .Rmd, .tex, .txt,
.html. For a PDF it uses `pdftotext` if installed; otherwise it stops and says
so (read the PDF with your file reader and save its text to a .txt instead).

`check` finds the statistics in the text (M, SD, t, F, chi2, r, z, b, beta,
SE, d, eta2, p, N, n, OR, R2, 95% CI) and looks for each number in the
outputs: run_code.py logs, and tables or text files produced by the scripts
(folders are searched recursively for .log .txt .csv .tsv .md .html). A number
matches when the output contains a value that rounds to it at the reported
precision (2.45 matches 2.4471). Prints JSON with, per statistic: the reported
text, the sentence it is in, and where it was found, found with the opposite
sign, or not found. Inequalities (p < .001) are listed for a check by hand.

A match is evidence, not proof: small integers and common p-values can match
by coincidence. Look at the location before calling a number reproduced.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

LABELS = (r"M|SD|SE|t|F|z|r|b|B|β|beta|d|g|OR|N|n|p|"
          r"R2|R²|r2|η2|ηp2|η²p|η²|ηp²|eta2|partial eta2|χ2|χ²|chi2|chi-square|X2|df")
STAT = re.compile(
    rf"(?<![A-Za-z])(?P<label>{LABELS})\s*(?P<df>\(\s*[\d.,\s]+\))?\s*(?P<op>=|<|>|≤|≥)\s*(?P<val>[-−–]?\s?\d*[.,]?\d+)")
# "mean age = 23.8", "Mean interference was 86.7 ms", "accuracy was 95.8%"
PROSE = re.compile(r"(?i)(?P<label>(?:mean|average|median|total|overall)\s+[a-z]+(?:\s+[a-z]+)?)\s*(?:=|was|were|of|:)\s*"
                   r"(?P<val>[-−–]?\d*[.,]?\d+)\s*(?P<unit>ms|s|%|years|hours|points)?")
UNIT = re.compile(r"(?<![\w.=])(?P<val>\d+\.\d+)\s*(?P<unit>ms|%|years|hours)\b")
CI = re.compile(r"(?:95\s*%\s*)?CI\s*[=:]?\s*\[\s*(?P<a>[-−–]?\d*[.,]?\d+)\s*[,;]\s*(?P<b>[-−–]?\d*[.,]?\d+)\s*\]")
NUMBER = re.compile(r"(?<![\w.])[-−]?\d*\.?\d+(?:[eE][-+]?\d+)?")
OUTPUT_EXT = {".log", ".txt", ".csv", ".tsv", ".md", ".html", ".out", ".rout"}


def to_float(s):
    s = s.replace("−", "-").replace("–", "-").replace(" ", "").replace(",", ".")
    return float(s)


def decimals(s):
    s = s.replace(",", ".")
    return len(s.split(".")[1]) if "." in s else 0


def extract_text(path):
    ext = path.suffix.lower()
    if ext in (".docx", ".odt"):
        with zipfile.ZipFile(path) as z:
            xml = z.read("word/document.xml" if ext == ".docx" else "content.xml").decode("utf8")
        xml = re.sub(r"</w:p>|</text:p>|<w:br/>", "\n", xml)
        xml = re.sub(r"<w:tab/>", "\t", xml)
        text = re.sub(r"<[^>]+>", "", xml)
    elif ext == ".pdf":
        if not shutil.which("pdftotext"):
            sys.exit("pdftotext is not installed: read the PDF with your file reader and save its text to a .txt")
        text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    elif ext in (".html", ".htm"):
        text = re.sub(r"<[^>]+>", " ", path.read_text(errors="replace"))
    else:
        text = path.read_text(errors="replace")
    import html
    return html.unescape(text)


def sentence_around(text, start, end):
    a = max(text.rfind(". ", 0, start), text.rfind("\n\n", 0, start))
    b_candidates = [i for i in (text.find(". ", end), text.find("\n\n", end)) if i != -1]
    b = min(b_candidates) if b_candidates else len(text)
    return re.sub(r"\s+", " ", text[a + 1: b + 1]).strip()[:300]


def find_stats(text):
    stats = []
    for m in STAT.finditer(text):
        label = m.group("label")
        if label == "df" or (label in ("n", "N", "d", "g", "b", "B", "r", "t", "z", "F", "p") and
                             re.match(r"[A-Za-z]", text[m.start() - 1: m.start()] or " ")):
            continue
        raw = m.group("val")
        stats.append({"label": label, "df": (m.group("df") or "").strip("() "), "op": m.group("op"),
                      "reported": m.group(0).strip(), "value": to_float(raw), "decimals": decimals(raw),
                      "sentence": sentence_around(text, m.start(), m.end())})
    taken = {(st["sentence"], st["value"]) for st in stats}
    for rx in (PROSE, UNIT):
        for m in rx.finditer(text):
            raw = m.group("val")
            sent = sentence_around(text, m.start(), m.end())
            if (sent, to_float(raw)) in taken:
                continue
            taken.add((sent, to_float(raw)))
            label = m.groupdict().get("label") or "value"
            stats.append({"label": label, "df": "", "op": "=", "reported": m.group(0).strip(),
                          "value": to_float(raw), "decimals": decimals(raw), "sentence": sent})
    for m in CI.finditer(text):
        for k in ("a", "b"):
            raw = m.group(k)
            stats.append({"label": "CI bound", "df": "", "op": "=", "reported": m.group(0).strip(),
                          "value": to_float(raw), "decimals": decimals(raw),
                          "sentence": sentence_around(text, m.start(), m.end())})
    return stats


def load_outputs(paths):
    lines = []
    for p in paths:
        p = Path(p)
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in OUTPUT_EXT]
        for f in files:
            for i, line in enumerate(f.read_text(errors="replace").splitlines(), 1):
                nums = []
                for m in NUMBER.finditer(line):
                    try:
                        nums.append(float(m.group(0).replace("−", "-")))
                    except ValueError:
                        pass
                if nums:
                    lines.append((str(f), i, line.strip()[:160], nums))
    return lines


def check(args):
    text = Path(args.text).read_text(errors="replace")
    stats = find_stats(text)
    outputs = load_outputs(args.outputs)
    results = []
    for s in stats:
        r = {k: s[k] for k in ("label", "df", "reported", "sentence")}
        if s["op"] != "=":
            r["status"] = "inequality: check by hand"
            results.append(r)
            continue
        tol = 0.5 * 10 ** (-s["decimals"]) + 1e-9
        v = s["value"]
        same, flipped = [], []
        for f, i, line, nums in outputs:
            if any(abs(x - v) <= tol for x in nums):
                same.append(f"{Path(f).name}:{i}: {line}")
            elif v != 0 and any(abs(-x - v) <= tol for x in nums):
                flipped.append(f"{Path(f).name}:{i}: {line}")
        if same:
            r["status"] = "found"
            r["where"] = same[:3]
        elif flipped:
            r["status"] = "found with opposite sign"
            r["where"] = flipped[:3]
        else:
            r["status"] = "not found"
        if s["decimals"] == 0 and abs(v) < 100 or s["label"] == "p":
            r["caution"] = "small integer or p-value: a match can be a coincidence"
        results.append(r)
    summary = {k: sum(1 for r in results if r["status"] == k)
               for k in ("found", "found with opposite sign", "not found", "inequality: check by hand")}
    print(json.dumps({"n_statistics": len(results), "summary": summary, "results": results}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("text")
    t.add_argument("manuscript")
    t.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("text")
    c.add_argument("outputs", nargs="+")
    args = ap.parse_args()
    if args.cmd == "text":
        Path(args.out).write_text(extract_text(Path(args.manuscript)))
        print(f"Wrote {args.out}")
    else:
        check(args)


if __name__ == "__main__":
    main()
