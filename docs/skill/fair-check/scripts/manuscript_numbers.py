#!/usr/bin/env python3
"""Compare the statistics reported in a manuscript with what the code prints.

  python3 manuscript_numbers.py text <manuscript> --out <manuscript.txt>
  python3 manuscript_numbers.py check <manuscript.txt> <output> [<output> ...]

`text` extracts plain text from .docx, .odt, .md, .qmd, .Rmd, .Rnw, .tex,
.txt, .html. For a PDF it uses `pdftotext` if installed; otherwise it stops
and says so (read the PDF with your file reader and save its text to a .txt
instead). For R Markdown, Quarto and Sweave it also counts the numbers written
by inline code (`r x`, {r} x, \\Sexpr{x}): those come from code by construction,
and are checked by rendering the document, not by this script.

`check` finds the statistics in the text and looks for each number in the
outputs: run_code.py logs, and tables or text files produced by the scripts
(folders are searched recursively for .log .txt .csv .tsv .md .html .json).

Statistics recognised:
  frequentist  M, SD, SE, Mdn, IQR, t, F, z, r, rho, tau, chi2, b, B, beta, OR,
               RR, HR, d, g, eta2 (partial), omega2, epsilon2, R2, W, U, H, V,
               alpha, omega, ICC, AIC, BIC, RMSEA, CFI, TLI, SRMR, N, n, p, df
  Bayesian     BF10, BF01, BF+0, BF-0, BFincl, log(BF), posterior probability
               P(...), pd (probability of direction), R-hat, ESS, WAIC, LOOIC,
               elpd
  intervals    95% CI, CrI, HDI, HPD, ETI [a, b] or "a to b"; also a bracket
               right after a statistic: "b = 0.32 [0.12, 0.52]"
  prose        "mean age was 23.8", "accuracy was 95.8%"

A number matches when the output contains a value that rounds to it at the
reported precision (2.45 matches 2.4471). Numbers are read in the manuscript's
convention: thousands separators (1,234.5) and decimal commas (23,5 in an
Italian text) are handled. Besides the same value, the script looks for the
same number written another way, and says which:
  - opposite sign (a different reference level or contrast);
  - a Bayes factor as its reciprocal (BF01 = 1/BF10), or as log(BF);
  - a percentage as a proportion (95.8% vs 0.958), ms as s (512 ms vs 0.512).
For every match it says whether the output names the statistic on that line
or in the three lines above it (where R prints a table's header), and in how
many places the number appears. Inequalities (p < .001,
BF10 > 100) are listed for a check by hand.

A match is evidence, not proof: small integers, p-values and numbers that
appear in many places can match by coincidence. Look at the location before
calling a number reproduced.
"""

import argparse
import html
import json
import math
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

NUM = (r"[-−–]?\s?(?:\d{1,3}(?:[,.  ]\d{3})+(?:[.,]\d+)?|\d*[.,]?\d+)"
       r"(?:\s*[×x·]\s*10\s*\^?\s*\(?[-−]?\d+\)?|[eE][-+−]?\d+)?")

# longer alternatives first
LABELS = "|".join([
    r"BF\s*_?\{?\s*(?:10|01|\+0|-0|0\+|0-|₁₀|₀₁|₊₀|₋₀|incl(?:usion)?|excl(?:usion)?)\s*\}?",
    r"(?:2\s*)?(?:log|ln|log10)\s*\(?\s*BF[\w₀₁₊₋+\-]*\s*\)?",
    r"BF",
    r"R̂|R-hat|Rhat|\\hat\{R\}",
    r"(?:bulk|tail)[_ -]ESS|ESS",
    r"P\s*\((?:[^()=]{1,40})\)",
    r"pd|p_d",
    r"Mdn|IQR|ICC|AIC|BIC|WAIC|LOOIC|LOO-IC|elpd(?:_loo)?|ELPD|RMSEA|CFI|TLI|SRMR",
    r"η2p|η²p|ηp2|ηp²|η\s*2|η²|partial eta2|eta2|ω2|ω²|ε2|ε²",
    r"R2adj|adj\.?\s*R2|adj\.?\s*R²|ΔR2|ΔR²|R2|R²|r2",
    r"χ2|χ²|chi2|chi-square|X2",
    r"Cohen's d|Hedges' g",
    r"SD|SE|OR|RR|HR|df",
    r"M|t|F|z|Z|r|ρ|τ|κ|α|ω|b|B|β|beta|d|g|N|n|p|W|U|H|V",
])
STAT = re.compile(
    rf"(?<![A-Za-z0-9_])(?P<label>{LABELS})\s*(?P<df>\([^()]{{0,40}}\))?\s*(?P<op>=|<|>|≤|≥|≈)\s*(?P<val>{NUM})"
    rf"\s*(?P<unit>%|ms\b|s\b)?")
# "mean age = 23.8", "Mean interference was 86.7 ms", "accuracy was 95.8%"
PROSE = re.compile(rf"(?i)(?P<label>(?:mean|average|median|total|overall)\s+[a-z]+(?:\s+[a-z]+)?)\s*(?:=|was|were|of|:)\s*"
                   rf"(?P<val>{NUM})\s*(?P<unit>ms|s|%|years|hours|points)?")
UNIT = re.compile(r"(?<![\w.=])(?P<val>\d+[.,]\d+)\s*(?P<unit>ms|%|years|hours)\b")
INTERVAL_KIND = r"CI|CrI|HDI|HPD|HDPI|ETI|credible interval|confidence interval|highest density interval"
INTERVAL = re.compile(
    rf"(?P<pct>\d{{1,2}}(?:[.,]\d)?\s*%\s*)?(?P<kind>{INTERVAL_KIND})\s*[:=]?\s*"
    rf"(?:[\[(]\s*(?P<a>{NUM})\s*(?:,|;|to|–|—)\s*(?P<b>{NUM})\s*[\])]|(?P<a2>{NUM})\s*(?:to|–|—)\s*(?P<b2>{NUM}))")
AFTER_STAT_INTERVAL = re.compile(rf"^\s*,?\s*(?:\d{{1,2}}\s*%\s*(?:{INTERVAL_KIND})\s*)?\[\s*(?P<a>{NUM})\s*[,;]\s*(?P<b>{NUM})\s*\]")
NUMBER = re.compile(r"(?<![\w.])[-−]?\d*\.?\d+(?:[eE][-+]?\d+)?")
OUTPUT_EXT = {".log", ".txt", ".csv", ".tsv", ".md", ".html", ".out", ".rout", ".json"}
INLINE_CODE = re.compile(r"`r\s+[^`]+`|`\{r\}\s*[^`]+`|`\{python\}\s*[^`]+`|\\Sexpr\{[^}]+\}")

# words that, on an output line, show it is about the same statistic
CONTEXT = [
    (r"^BF|BF$|^BF", r"(?i)bayes|\bBF|bf\d|evid|ratio"),
    (r"(?i)log|ln", r"(?i)bayes|\bBF|log"),
    (r"R̂|R-hat|Rhat|hat", r"(?i)r.?hat"),
    (r"ESS", r"(?i)ess"),
    (r"^P\s*\(", r"(?i)prob|post|p\("),
    (r"^(pd|p_d)$", r"(?i)\bpd\b|direction"),
    (r"^t$", r"(?i)\bt\b|t.value|t-value|t\(|statistic"),
    (r"^F$", r"(?i)\bF\b|F.value|Df|anova"),
    (r"^(z|Z)$", r"(?i)\bz\b|z.value"),
    (r"^p$", r"(?i)p.?val|Pr\(|\bp\b"),
    (r"^(r|ρ|τ)$", r"(?i)cor|\br\b|pearson|spearman|kendall|rho|tau"),
    (r"χ|chi|X2", r"(?i)chi|χ|X-squared"),
    (r"^(b|B|β|beta)$", r"(?i)estimate|coef|\bb\b|beta|β|Est\."),
    (r"^(M|Mdn)$", r"(?i)mean|\bM\b|avg|median"),
    (r"^SD$", r"(?i)\bsd\b|std"),
    (r"^SE$", r"(?i)\bse\b|std\.?\s*err|Est\.Error"),
    (r"η|eta|ω|ε", r"(?i)eta|η|omega|ω|epsilon|ε|effect"),
    (r"R2|R²|r2", r"(?i)R2|R\^2|R-sq|r.squared|R²"),
    (r"^(d|g|Cohen|Hedges)", r"(?i)cohen|hedges|\bd\b|\bg\b|effsize|smd"),
    (r"^(N|n)$", r"(?i)\bn\b|nrow|count|obs|participants|subjects|length"),
    (r"^(OR|RR|HR)$", r"(?i)odds|ratio|\bOR\b|\bRR\b|\bHR\b|exp\("),
    (r"interval|CI|CrI|HDI|HPD|ETI", r"(?i)\bCI\b|lower|upper|l-\d\d|u-\d\d|2\.5\s*%|97\.5\s*%|hdi|hpd|eti|interval|conf"),
    (r"AIC|BIC|WAIC|LOO|elpd|ELPD", r"(?i)aic|bic|waic|loo|elpd"),
]


def to_float(raw, decimal_comma=False):
    """'1,234.5' -> 1234.5; '23,5' -> 23.5 in a decimal-comma text; '1.2 × 10^5'."""
    s = raw.replace("−", "-").replace("–", "-").replace(" ", "").replace(" ", "").replace(" ", "")
    exp = 0
    m = re.search(r"[×x·]10\^?\(?(-?\d+)\)?$", s)
    if m:
        exp, s = int(m.group(1)), s[:m.start()]
    if decimal_comma:
        s = s.replace(".", "").replace(",", ".")
    elif re.match(r"^-?\d{1,3}(,\d{3})+(\.\d+)?([eE][-+]?\d+)?$", s):
        s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    return float(s) * 10 ** exp


def precision(raw, decimal_comma=False):
    """Half a unit of the last reported digit: '2.45' -> 0.005, '1.2e5' -> 5000."""
    s = raw.replace("−", "-").replace("–", "-").replace(" ", "")
    exp = 0
    m = re.search(r"[×x·]10\^?\(?(-?\d+)\)?$", s) or re.search(r"[eE]([-+]?\d+)$", s)
    if m:
        exp, s = int(m.group(1)), s[:m.start()]
    sep = "," if decimal_comma else "."
    if not decimal_comma and not re.match(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$", s):
        s = s.replace(",", ".")
    dec = len(s.rsplit(sep, 1)[1]) if sep in s and not re.match(r"^-?\d{1,3}(" + re.escape(sep) + r"\d{3})+$", s) else 0
    return 0.5 * 10 ** (exp - dec) + 1e-12, dec


def decimal_convention(text):
    """True when the text writes decimals with a comma (statistics after '=')."""
    vals = re.findall(r"[=<>]\s*[-−]?\d*([.,])\d+", text)
    comma = sum(1 for v in vals if v == ",")
    return comma > len(vals) - comma


def extract_text(path):
    ext = path.suffix.lower()
    if ext in (".docx", ".odt"):
        with zipfile.ZipFile(path) as z:
            names = ["word/document.xml", "word/footnotes.xml"] if ext == ".docx" else ["content.xml"]
            xml = "\n".join(z.read(n).decode("utf8") for n in names if n in z.namelist())
        xml = re.sub(r"</w:p>|</text:p>|<w:br/>|</w:tc>|</table:table-cell>", "\n", xml)
        xml = re.sub(r"<w:tab/>", "\t", xml)
        text = re.sub(r"<[^>]+>", "", xml)
    elif ext == ".pdf":
        if not shutil.which("pdftotext"):
            sys.exit("pdftotext is not installed: read the PDF with your file reader and save its text to a .txt")
        text = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    elif ext in (".html", ".htm"):
        text = re.sub(r"<sub>|</sub>|<sup>|</sup>", "", path.read_text(errors="replace"))
        text = re.sub(r"<[^>]+>", " ", text)
    else:
        text = path.read_text(errors="replace")
    text = html.unescape(text)
    # ligatures and typographic minus from PDFs and Word
    return text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("−", "-")


def sentence_around(text, start, end):
    a = max(text.rfind(". ", 0, start), text.rfind("\n\n", 0, start))
    b_candidates = [i for i in (text.find(". ", end), text.find("\n\n", end)) if i != -1]
    b = min(b_candidates) if b_candidates else len(text)
    return re.sub(r"\s+", " ", text[a + 1: b + 1]).strip()[:300]


def find_stats(text):
    dc = decimal_convention(text)
    stats, seen = [], set()

    def add(label, raw, reported, start, end, op="=", df="", unit=None):
        try:
            value = to_float(raw, dc)
        except ValueError:
            return
        tol, dec = precision(raw, dc)
        if start in seen:  # the same number, already taken by another pattern
            return
        seen.add(start)
        stats.append({"label": label, "df": df, "op": op, "reported": reported, "value": value, "tol": tol,
                      "decimals": dec, "unit": unit, "_pos": start,
                      "sentence": sentence_around(text, start, end)})

    for m in STAT.finditer(text):
        label = re.sub(r"\s+", "", m.group("label"))
        if label == "df":
            continue
        op = {"≈": "="}.get(m.group("op"), m.group("op"))
        add(label, m.group("val"), m.group(0).strip(), m.start(), m.end(), op, (m.group("df") or "").strip("() "), m.group("unit"))
        after = AFTER_STAT_INTERVAL.match(text[m.end():m.end() + 80])
        if after:
            kind = re.search(rf"\d{{1,2}}\s*%\s*(?:{INTERVAL_KIND})", after.group(0))
            kind = kind.group(0) if kind else "interval"
            for k, side in (("a", "lower"), ("b", "upper")):
                add(f"{kind} of {label} ({side})", after.group(k), after.group(0).strip(" ,"),
                    m.end() + after.start(k), m.end() + after.end(k))
    for m in INTERVAL.finditer(text):
        kind = f"{(m.group('pct') or '').strip()} {m.group('kind')}".strip()
        for k, side in (("a", "lower"), ("b", "upper")):
            g = k if m.group(k) else k + "2"
            add(f"{kind} ({side})", m.group(g), m.group(0).strip(), m.start(g), m.end())
    taken = {(st["sentence"], round(st["value"], 9)) for st in stats}
    for rx in (PROSE, UNIT):
        for m in rx.finditer(text):
            try:
                v = to_float(m.group("val"), dc)
            except ValueError:
                continue
            sent = sentence_around(text, m.start(), m.end())
            if (sent, round(v, 9)) in taken:
                continue
            taken.add((sent, round(v, 9)))
            add(m.groupdict().get("label") or "value", m.group("val"), m.group(0).strip(), m.start(), m.end(),
                unit=m.groupdict().get("unit"))
    stats.sort(key=lambda s: s.pop("_pos"))
    return stats, dc


def load_outputs(paths):
    lines = []
    for p in paths:
        p = Path(p)
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in OUTPUT_EXT]
        for f in files:
            all_lines = f.read_text(errors="replace").splitlines()
            for i, line in enumerate(all_lines, 1):
                nums = []
                semicolon = ";" in line
                for m in NUMBER.finditer(line):
                    try:
                        nums.append(float(m.group(0).replace("−", "-")))
                    except ValueError:
                        pass
                if semicolon:  # write.csv2 output: 0,958
                    nums += [float(x.replace(",", ".")) for x in re.findall(r"(?<![\w.,])-?\d+,\d+(?![\d,])", line)]
                if nums:
                    around = "\n".join(all_lines[max(0, i - 4):i])
                    lines.append((str(f), i, line.strip()[:160], nums, around))
    return lines


def transforms(stat):
    """Other ways the same number may be printed by the code: (description, f(x))."""
    label, unit = stat["label"], stat.get("unit")
    out = [("same", lambda x: x)]
    if stat["value"] != 0:
        out.append(("opposite sign", lambda x: -x))
    if re.match(r"BF", label):
        out += [("as its reciprocal (BF01 = 1/BF10)", lambda x: 1 / x if x else None),
                ("from log(BF) in the output", lambda x: math.exp(x) if x < 700 else None),
                ("from log10(BF) in the output", lambda x: 10 ** x if x < 300 else None)]
    if re.match(r"(?i)(2\s*)?(log|ln)", label):
        out += [("as log of the BF in the output", lambda x: math.log(x) if x > 0 else None),
                ("as log10 of the BF in the output", lambda x: math.log10(x) if x > 0 else None)]
    if unit == "%" or label in ("pd", "p_d"):
        out += [("as a proportion in the output (0.958 for 95.8%)", lambda x: x * 100)]
    elif stat["value"] <= 1 and re.match(r"^(pd|p_d|P\()", label):
        out += [("as a percentage in the output", lambda x: x / 100)]
    if unit == "ms":
        out += [("in seconds in the output", lambda x: x * 1000)]
    if unit == "s":
        out += [("in milliseconds in the output", lambda x: x / 1000)]
    return out


def context_rx(label):
    for lab_pat, ctx in CONTEXT:
        if re.search(lab_pat, label):
            return re.compile(ctx)
    return None


def check(args):
    text = Path(args.text).read_text(errors="replace")
    stats, dc = find_stats(text)
    outputs = load_outputs(args.outputs)
    results = []
    for s in stats:
        r = {k: s[k] for k in ("label", "df", "reported", "sentence") if s.get(k) not in (None, "")}
        if s["op"] != "=":
            r["status"] = "inequality: check by hand"
            results.append(r)
            continue
        v, tol = s["value"], s["tol"]
        ctx = context_rx(s["label"])
        hits = {}
        for name, f in transforms(s):
            for fname, i, line, nums, around in outputs:
                ok = False
                for x in nums:
                    try:
                        t = f(x)
                    except (OverflowError, ZeroDivisionError, ValueError):
                        t = None
                    if t is not None and abs(t - v) <= tol:
                        ok = True
                        break
                if ok:
                    hits.setdefault(name, []).append((bool(ctx and ctx.search(around)), f"{Path(fname).name}:{i}: {line}"))
            if name == "same" and hits.get("same"):
                break
        if not hits:
            r["status"] = "not found"
        else:
            name = "same" if "same" in hits else next(iter(hits))
            where = sorted(hits[name], key=lambda h: not h[0])
            r["status"] = {"same": "found", "opposite sign": "found with opposite sign"}.get(name, f"found {name}")
            r["where"] = [w for _, w in where[:3]]
            r["n_places"] = len(where)
            r["context"] = "the statistic is named on that line or just above it" if where[0][0] else "number only"
            if not where[0][0] and len(where) >= 4:
                r["caution"] = f"a common number: it appears in {len(where)} places and none names the statistic"
        if s["decimals"] == 0 and abs(v) < 100 or s["label"] == "p":
            r["caution"] = (r.get("caution", "") + "; " if r.get("caution") else "") + \
                "small integer or p-value: a match can be a coincidence"
        results.append(r)
    keys = ["found", "found with opposite sign", "not found", "inequality: check by hand"]
    summary = {k: sum(1 for r in results if r["status"] == k) for k in keys}
    summary["found in another form"] = sum(1 for r in results if r["status"].startswith("found ") and r["status"] not in keys)
    print(json.dumps({"n_statistics": len(results), "decimal_comma": dc, "summary": summary, "results": results},
                     indent=1, ensure_ascii=False))


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
        path = Path(args.manuscript)
        text = extract_text(path)
        Path(args.out).write_text(text)
        print(f"Wrote {args.out}")
        if path.suffix.lower() in (".rmd", ".qmd", ".rnw", ".rtex", ".md"):
            n = len(INLINE_CODE.findall(text))
            if n:
                print(f"Note: {n} numbers are written by inline code (`r ...`, {{r}}, \\Sexpr): they come from the code "
                      "by construction. Render the document to check them; this script checks only the numbers typed by hand.")
    else:
        check(args)


if __name__ == "__main__":
    main()
