#!/usr/bin/env python3
"""Compare the statistics reported in a manuscript with what the code prints.

  python3 manuscript_numbers.py text <manuscript> --out <manuscript.txt>
  python3 manuscript_numbers.py check <manuscript.txt> <output> [<output> ...]
  python3 manuscript_numbers.py internal <manuscript.txt>

`internal` needs no code or data: it checks the text against itself (does
the participant flow add up, do group sizes add up to N, do percentages match
their counts, do degrees of freedom fit N) and lists the response scales the
text declares, to compare with the ranges in the data.

`text` extracts plain text from .docx, .odt, .md, .qmd, .Rmd, .Rnw, .tex,
.txt, .html. For a PDF it uses pdftotext, Ghostscript or pypdf, the first one
available; with none it stops and says so. For R Markdown, Quarto and Sweave it also counts the numbers written
by inline code (`r x`, {r} x, \\Sexpr{x}): those come from code by construction,
and are checked by rendering the document, not by this script.

`check` finds the statistics in the text and looks for each number in the
outputs: run_code.py logs, and tables or text files produced by the scripts
(folders are searched recursively for .log .txt .csv .tsv .md .html .json;
.csv/.tsv longer than --max-table-lines, default 2000, are skipped there:
trial-level data match reported numbers by chance). Only numbers: figures
are not compared.

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
from collections import Counter
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
        text = pdf_text(path)
    elif ext in (".html", ".htm"):
        text = re.sub(r"<sub>|</sub>|<sup>|</sup>", "", path.read_text(errors="replace"))
        text = re.sub(r"<[^>]+>", " ", text)
    else:
        text = path.read_text(errors="replace")
    text = html.unescape(text)
    # ligatures and typographic minus from PDFs and Word
    return text.replace("ﬁ", "fi").replace("ﬂ", "fl").replace("−", "-")


def pdf_text(path):
    """Text of a PDF with the first tool available: pdftotext (poppler),
    Ghostscript, or the Python package pypdf."""
    if shutil.which("pdftotext"):
        return subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True).stdout
    if shutil.which("gs"):
        out = subprocess.run(["gs", "-q", "-dNOPAUSE", "-dBATCH", "-dSAFER", "-sDEVICE=txtwrite",
                              "-sOutputFile=-", str(path)], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout
    try:
        import pypdf  # noqa: PLC0415
        return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(str(path)).pages)
    except ImportError:
        pass
    sys.exit("No tool to read the PDF here (pdftotext, Ghostscript or pypdf): read it with your file "
             "reader and save its text to a .txt, or ask the researcher for the text (.docx, .txt)")


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


WRITTEN_BY_PEOPLE = re.compile(r"(?i)^(readme|leggimi|manuscript|manoscritto|paper|preprint|article|articolo|"
                               r"draft|bozza|submission|thesis|tesi|cover|letter|response)")


def load_outputs(paths, max_table_lines=2000, manuscript_text="", manuscript_file=None):
    """Lines with numbers from the outputs. In folders, data tables longer than
    max_table_lines (trial-level data, not results) are skipped: their thousands
    of values match reported numbers by chance; so are texts written by people
    (README, the manuscript itself), which would match the manuscript's numbers
    with themselves. Files named explicitly are read. Lines copied verbatim from
    the manuscript are never counted."""
    lines, skipped = [], []
    copied = {ln.strip() for ln in manuscript_text.splitlines() if len(ln.strip()) > 30}
    for p in paths:
        p = Path(p)
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file() and f.suffix.lower() in OUTPUT_EXT]
        for f in files:
            if manuscript_file and f.resolve() == Path(manuscript_file).resolve():
                continue
            if not p.is_file() and WRITTEN_BY_PEOPLE.search(f.name):
                skipped.append(f"{f} (written by people, not by the code)")
                continue
            all_lines = f.read_text(errors="replace").splitlines()
            if not p.is_file() and f.suffix.lower() in (".csv", ".tsv") and len(all_lines) > max_table_lines:
                skipped.append(f"{f} ({len(all_lines)} lines)")
                continue
            for i, line in enumerate(all_lines, 1):
                if line.strip() in copied:
                    continue
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
    return lines, skipped


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
    outputs, skipped = load_outputs(args.outputs, args.max_table_lines, text, args.text)
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
    out = {"n_statistics": len(results), "decimal_comma": dc, "summary": summary, "results": results}
    if skipped:
        out["tables_skipped"] = {"files": skipped, "note": "not searched in the folders given: long data tables "
                                 "(chance matches) and texts written by people (README, the manuscript). Name a file "
                                 "explicitly, or raise --max-table-lines, to search it"}
    print(json.dumps(out, indent=1, ensure_ascii=False))


# ---------------------------------------------------------------- internal arithmetic

PEOPLE = r"(?:participants?|students?|adults?|children|adolescents|people|subjects|respondents|individuals|" \
         r"pupils|patients|volunteers|women|men|females|males|partecipanti|studenti|soggetti|persone|bambini)"
START_W = r"(?:recruit\w*|enrol\w*|took part|participated|(?:were|was) tested|initially|invited|contacted|signed up|" \
          r"completed the|started|reclutat\w*|hanno partecipato|inizialmente)"
EXCL_W = r"(?:exclu\w*|remov\w*|discard\w*|dropp\w*|did not complete|incomplete|withdr\w*|outliers?|esclus\w*|rimoss\w*)"
FINAL_W = r"(?:final sample|final N|analy[sz]ed|retained|remaining|were included|sample consisted|consisted of|" \
          r"campione finale|analizzat\w*)"
NUM = r"(?<![\d.,])(\d{1,3}(?:,\d{3})+|\d+)(?![\d.,]\d)"


def _num(s):
    return int(s.replace(",", ""))


def _sentences(text):
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.;!?])\s+(?=[A-Z(])", flat) if s.strip()]


def _near(sentence, words, span=60):
    """Numbers within `span` characters of one of `words` in the sentence."""
    out = []
    for m in re.finditer(words, sentence, re.I):
        lo, hi = max(0, m.start() - span), m.end() + span
        for n in re.finditer(NUM, sentence[lo:hi]):
            v = _num(n.group(1))
            if 1 < v < 100000 and not re.match(r"(19|20)\d\d$", n.group(1)):
                out.append(v)
    return out


def internal(args):
    """Checks that need only the manuscript: does the participant flow add up,
    do group sizes add up to N, do percentages match their counts, do degrees of
    freedom fit N, which response scales the text declares."""
    text = Path(args.text).read_text(errors="replace")
    sents = _sentences(text)
    findings = []
    # sample sizes the text states
    ns = Counter()
    for s in sents:
        for m in re.finditer(r"\b[Nn]\s*=\s*" + NUM, s):
            ns[_num(m.group(1))] += 1
        for m in re.finditer(NUM + r"\s+(?:\w+\s+){0,2}?" + PEOPLE + r"\b", s, re.I):
            ns[_num(m.group(1))] += 1
    main_n = [n for n, _ in ns.most_common(6)]

    # participant flow, in windows of three sentences
    seen = set()
    for i in range(len(sents)):
        win = " ".join(sents[i:i + 3])
        final = _near(win, FINAL_W, 40)
        # excluded: "excluded 13 (of them)", "13 participants were excluded" — not any number nearby,
        # and not a range ("incomplete 18 to 60 years")
        not_range = r"(?!\s*(?:to|-|–|and)\s*\d|\s*years)"
        ex_m = [(m.start(), _num(m.group(1))) for m in re.finditer(
                    EXCL_W + r"\s+(?:\w+\s+){0,2}?" + NUM + not_range, win, re.I)] + \
               [(m.start(), _num(m.group(1))) for m in re.finditer(
                    NUM + r"\s+(?:\w+\s+){0,3}?(?:were|was|have been|had to be)\s+" + EXCL_W, win, re.I)]
        excl = [v for _, v in ex_m]
        # the starting number is the last one before the first exclusion ("a second sample of 90 ...")
        first_ex = min((p for p, _ in ex_m), default=len(win))
        start = [v for p, v in sorted((m.start(), _num(n.group(1)))
                                      for m in re.finditer(START_W, win, re.I)
                                      for n in re.finditer(NUM, win[max(0, m.start() - 40):m.end() + 40])
                                      if 1 < _num(n.group(1)) < 100000) if p <= first_ex]
        start = start[-1:] if start else []
        start = [x for x in start if x not in excl]
        if not start or not excl:
            continue
        a = start[0]
        excl = sorted({x for x in excl if x < a})
        if not excl:
            continue
        targets = sorted(set(final) | set(main_n))
        options = {a - max(excl)} | ({a - sum(excl)} if sum(excl) < a else set())
        # a breakdown "13 of them: 5 for ..., 5 for ..., 3 for ..." must add up to the total
        parts = [_num(x) for x in re.findall(NUM + r"\s+(?:for|because|due to|per|perché)\b", win)]
        if len(parts) >= 2 and max(excl) not in parts:
            findings.append({"check": "exclusion breakdown",
                             "status": "adds up" if sum(parts) == max(excl) else "does not add up",
                             "numbers": f"{' + '.join(map(str, parts))} = {sum(parts)}; total excluded {max(excl)}",
                             "sentence": win[:400]})
        key = (a, tuple(excl))
        if key in seen:
            continue
        seen.add(key)
        ok = sorted(options & set(targets))
        findings.append({
            "check": "participant flow", "status": "adds up" if ok else "does not add up",
            "numbers": f"{a} - {max(excl)} = {a - max(excl)}" + (f" ({a} - all excluded numbers = {a - sum(excl)})"
                                                               if len(excl) > 1 and sum(excl) < a else "") +
                       f"; N stated in the text: {', '.join(map(str, targets)) or 'none'}",
            "computed": sorted(options), "sentence": win[:400]})

    # group sizes that should add up to N: "147 women and 87 men"
    for s in sents:
        m = re.findall(NUM + r"\s*(?:\(\s*[\d.,]+\s*%\s*\)\s*)?(?:were\s+)?(women|men|females|males|girls|boys|"
                       r"donne|uomini|femmine|maschi)\b", s, re.I)
        if len(m) >= 2 and main_n:
            total = sum(_num(x) for x, _ in m)
            findings.append({
                "check": "group sizes", "status": "add up to a stated N" if total in ns else "do not add up to a stated N",
                "numbers": " + ".join(f"{x} {w}" for x, w in m) + f" = {total}; N stated: {', '.join(map(str, main_n))}",
                "sentence": s[:300]})

    # percentages next to counts: "147 (62.8%)"
    for s in sents:
        for m in re.finditer(NUM + r"\s*\(\s*(\d{1,3}(?:[.,]\d+)?)\s*%\s*\)", s):
            k, pct = _num(m.group(1)), float(m.group(2).replace(",", "."))
            dec = len(m.group(2).replace(",", ".").split(".")[1]) if re.search(r"[.,]", m.group(2)) else 0
            fits = [n for n in main_n if n >= k and abs(round(100 * k / n, dec) - pct) <= 0.5 * 10 ** -dec + 1e-9]
            if main_n and not fits:
                findings.append({"check": "percentage", "status": "matches no stated N",
                                 "numbers": f"{k} ({pct}%): {k} of {', '.join(map(str, main_n))} gives " +
                                            ", ".join(f"{100 * k / n:.{max(dec, 1)}f}%" for n in main_n if n >= k),
                                 "sentence": s[:300]})

    # degrees of freedom: r(df) -> N = df + 2; t(df) -> N = df + 1 or + 2
    for s in sents:
        for m in re.finditer(r"\b(r|t)\s*\(\s*(\d+)\s*\)\s*=", s):
            df = int(m.group(2))
            implied = {df + 2} if m.group(1) == "r" else {df + 1, df + 2}
            if main_n and not implied & set(ns) and df > 10:
                findings.append({"check": "degrees of freedom", "status": "fit no stated N",
                                 "numbers": f"{m.group(0).rstrip('= ')} implies N = {' or '.join(map(str, sorted(implied)))}; "
                                            f"N stated: {', '.join(map(str, main_n))} (a subgroup or missing data?)",
                                 "sentence": s[:300]})

    # response scales the text declares
    scales = []
    for s in sents:
        for m in re.finditer(r"(\d)\s*-\s*point|(?:from|ranging from|da)\s+(\d{1,2})\s*(?:\([^)]{0,40}\))?\s*"
                             r"(?:to|a)\s+(\d{1,2})\b|\b(\d)\s*[–-]\s*(\d{1,2})\s+(?:Likert|scale|scala)", s, re.I):
            g = [x for x in m.groups() if x]
            if not m.group(1) and (int(g[0]) > 1 or int(g[1]) > 11):
                continue  # "from 16 to 19" is an age, not a response scale
            rng = f"{g[0]}-point" if m.group(1) else f"{g[0]}-{g[1]}"
            scales.append({"scale": rng, "sentence": s[:250]})
    ages = []
    for s in sents:
        for m in re.finditer(r"(?:aged|age range|ages?|from|between|tra|da)\s+(?:of\s+)?(\d{1,2})\s*(?:to|and|-|–|e|a)\s*"
                             r"(\d{1,2})\s*(?:years|yrs|anni)?", s, re.I):
            lo, hi = int(m.group(1)), int(m.group(2))
            if 3 <= lo < hi <= 99 and re.search(r"(?i)years|yrs|anni|aged|age", s[max(0, m.start() - 40):m.end() + 20]):
                ages.append({"range": f"{lo}-{hi}", "sentence": s[:250]})
    uniq = []
    for f in findings:
        if (f["check"], f["numbers"]) not in {(u["check"], u["numbers"]) for u in uniq}:
            uniq.append(f)
    findings = uniq
    out = {"n_stated": dict(ns.most_common(8)), "findings": findings, "scales_declared": scales[:20],
           "age_ranges_declared": ages[:10],
           "note": "pattern matching on the text: read each sentence before reporting; 'does not add up' "
                   "is worth a sentence in the report only after you checked it"}
    print(json.dumps(out, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("text")
    t.add_argument("manuscript")
    t.add_argument("--out", required=True)
    i = sub.add_parser("internal")
    i.add_argument("text")
    c = sub.add_parser("check")
    c.add_argument("text")
    c.add_argument("outputs", nargs="+")
    c.add_argument("--max-table-lines", type=int, default=2000,
                   help="in folders, skip .csv/.tsv longer than this (trial-level data); default 2000")
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
    elif args.cmd == "internal":
        internal(args)
    else:
        check(args)


if __name__ == "__main__":
    main()
