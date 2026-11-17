#!/usr/bin/env python3
"""Recompute a statistic from a data file in the ways that most often explain
a discrepancy, and say which one gives the value the manuscript reports.

  python3 recompute.py r    <data> <x> <y> --reported 0.34 [--where "excluded == 0"] [--by group]
  python3 recompute.py desc <data> <col>   --mean 23.8 --sd 4.1 --n 180 [--where ...] [--by group]
  python3 recompute.py n    <data>         --n 180 [--where ...] [--id participant]

For a correlation (`r`) it tries Pearson, Spearman and Kendall; for every
statistic it also tries:
  - with and without the --where filters (the exclusions the scripts or the
    manuscript describe: "rt > 200", "excluded == 0", "group != pilot");
  - missing-value codes (-999, -99, -9, 99, 999, 9999) kept as numbers or
    treated as missing, when the columns contain them;
  - complete cases on every column given with --complete (listwise) or only on
    the columns of the statistic (pairwise);
  - for `desc`, the SD with n - 1 and with n.
A variant "matches" when it rounds to the reported value at the reported
precision. It prints one line per variant, matches first. The data are read
with the scanner's readers (CSV, TSV, Excel, SPSS when the libraries are
there); nothing is written.

This is a first check on the raw file: what the scripts do (which file, which
rows, which transformation) still decides what the manuscript reports.
"""

import argparse
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fair_scan import load_any, split_export, to_number  # noqa: E402

MISSING_CODES = {-999.0, -99.0, -9.0, 99.0, 999.0, 9999.0}
OPS = {"==": lambda a, b: a == b, "!=": lambda a, b: a != b, ">=": lambda a, b: a >= b,
       "<=": lambda a, b: a <= b, ">": lambda a, b: a > b, "<": lambda a, b: a < b}


def load(path, sheet=None):
    tables = load_any(Path(path))
    if not tables:
        sys.exit(f"not a data file: {path}")
    for name, rows, info in tables:
        if sheet and name != sheet:
            continue
        if rows is None:
            sys.exit(f"cannot read {path}: {info.get('not_read')}")
        header, body, _, _ = split_export(rows)
        header = [h.strip() for h in header]
        return header, [dict(zip(header, r)) for r in body]
    sys.exit(f"sheet {sheet} not found in {path}")


def num(v):
    x = to_number(v) if v is not None else None
    if x is None and isinstance(v, str):
        x = to_number(v.replace(",", "."))
    return x


def parse_where(expr):
    m = re.match(r"^\s*(.+?)\s*(==|!=|>=|<=|>|<)\s*(.+?)\s*$", expr)
    if not m:
        sys.exit(f"cannot read the filter {expr!r}: write it as 'column op value'")
    col, op, val = m.group(1).strip("`'\" "), m.group(2), m.group(3).strip("'\" ")
    return col, op, val


def keep(row, filters):
    for col, op, val in filters:
        a, b = row.get(col, ""), val
        na, nb = num(a), num(b)
        if na is not None and nb is not None:
            a, b = na, nb
        elif op not in ("==", "!="):
            return False
        if not OPS[op](a, b):
            return False
    return True


def tol_of(raw):
    s = str(raw).replace(",", ".")
    dec = len(s.split(".")[1]) if "." in s else 0
    return 0.5 * 10 ** -dec + 1e-9, float(s)


def rank(xs):
    order = sorted(range(len(xs)), key=lambda i: xs[i])
    r = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[order[j + 1]] == xs[order[i]]:
            j += 1
        for k in range(i, j + 1):
            r[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return r


def pearson(x, y):
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx and syy else None


def kendall(x, y):
    n = len(x)
    if n < 3 or n > 5000:
        return None
    c = d = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            a, b = x[i] - x[j], y[i] - y[j]
            if a == 0 and b == 0:
                continue
            if a == 0:
                tx += 1
            elif b == 0:
                ty += 1
            elif (a > 0) == (b > 0):
                c += 1
            else:
                d += 1
    den = math.sqrt((c + d + tx) * (c + d + ty))
    return (c - d) / den if den else None


def values(rows, cols, codes_missing, complete):
    """Numeric tuples for `cols`, rows with a missing value in `complete` dropped."""
    out = []
    for r in rows:
        tup = []
        for c in complete:
            x = num(r.get(c, ""))
            if x is None or (codes_missing and x in MISSING_CODES):
                tup = None
                break
        if tup is None:
            continue
        for c in cols:
            x = num(r.get(c, ""))
            if x is None or (codes_missing and x in MISSING_CODES):
                tup = None
                break
            tup.append(x)
        if tup is not None:
            out.append(tup)
    return out


def has_codes(rows, cols):
    return any(num(r.get(c, "")) in MISSING_CODES for r in rows for c in cols)


def variants(rows, cols, filters, complete):
    """(description, rows, codes_missing, complete columns) for every combination that applies."""
    sets = [("filters as given", [r for r in rows if keep(r, filters)])] if filters else []
    sets.append(("no filter" if filters else "all rows", rows))
    codes = [False, True] if has_codes(rows, cols) else [False]
    comp = [list(cols)] + ([sorted(set(complete) | set(cols))] if complete else [])
    for sdesc, rs in sets:
        for cm in codes:
            for cc in comp:
                d = [sdesc]
                if len(codes) > 1:
                    d.append("missing codes as missing" if cm else "missing codes kept as numbers")
                if complete:
                    d.append("complete cases on " + ", ".join(cc) if len(cc) > len(cols) else "pairwise")
                yield "; ".join(d), rs, cm, cc


def groups(rows, by):
    if not by:
        return [("", rows)]
    levels = sorted({r.get(by, "") for r in rows})
    return [(f"{by} = {lv}: ", [r for r in rows if r.get(by, "") == lv]) for lv in levels]


def show(results):
    results.sort(key=lambda r: (not r[0], r[1]))
    n_match = sum(1 for r in results if r[0])
    lines = [("MATCH  " if ok else "       ") + text for ok, _, text in results]
    head = (f"{n_match} of {len(results)} variants give the reported value(s)" if n_match else
            f"no variant gives the reported value(s) ({len(results)} tried)")
    print(head)
    print("\n".join(lines))


def cmd_r(a):
    header, rows = load(a.data, a.sheet)
    for c in (a.x, a.y):
        if c not in header:
            sys.exit(f"column {c!r} not in {a.data}: {', '.join(header[:30])}")
    tol, rep = tol_of(a.reported)
    out = []
    for gname, grows in groups(rows, a.by):
        for desc, rs, cm, cc in variants(grows, [a.x, a.y], [parse_where(w) for w in a.where], a.complete):
            vals = values(rs, [a.x, a.y], cm, cc)
            x, y = [v[0] for v in vals], [v[1] for v in vals]
            for meth, f in (("Pearson", pearson), ("Spearman", lambda p, q: pearson(rank(p), rank(q))),
                            ("Kendall", kendall)):
                v = f(x, y)
                if v is None:
                    continue
                ok = abs(v - rep) <= tol or abs(-v - rep) <= tol
                sign = " (opposite sign)" if ok and abs(v - rep) > tol else ""
                out.append((ok, abs(abs(v) - abs(rep)), f"{gname}{meth}, {desc}: r = {v:.4f}, n = {len(x)}{sign}"))
    show(out)


def cmd_desc(a):
    header, rows = load(a.data, a.sheet)
    if a.col not in header:
        sys.exit(f"column {a.col!r} not in {a.data}: {', '.join(header[:30])}")
    want = [(k, tol_of(v)) for k, v in (("mean", a.mean), ("sd", a.sd), ("n", a.n)) if v is not None]
    if not want:
        sys.exit("give at least one of --mean, --sd, --n")
    out = []
    for gname, grows in groups(rows, a.by):
        for desc, rs, cm, cc in variants(grows, [a.col], [parse_where(w) for w in a.where], a.complete):
            xs = [v[0] for v in values(rs, [a.col], cm, cc)]
            n = len(xs)
            if n < 2:
                continue
            m = sum(xs) / n
            ss = sum((x - m) ** 2 for x in xs)
            for sdn, sd in (("SD with n - 1", math.sqrt(ss / (n - 1))), ("SD with n", math.sqrt(ss / n))):
                if sdn == "SD with n" and not a.sd:
                    continue
                got = {"mean": m, "sd": sd, "n": n}
                ok = all(abs(got[k] - rep) <= tol for k, (tol, rep) in want)
                dist = sum(abs(got[k] - rep) / (abs(rep) or 1) for k, (tol, rep) in want)
                out.append((ok, dist, f"{gname}{desc}; {sdn}: M = {m:.4f}, SD = {sd:.4f}, n = {n}"))
    show(out)


def cmd_n(a):
    header, rows = load(a.data, a.sheet)
    tol, rep = tol_of(a.n)
    out = []
    for desc, rs in ([("filters as given", [r for r in rows if keep(r, [parse_where(w) for w in a.where])])]
                     if a.where else []) + [("no filter" if a.where else "all rows", rows)]:
        n_rows = len(rs)
        out.append((abs(n_rows - rep) <= tol, abs(n_rows - rep), f"{desc}: {n_rows} rows"))
        if a.id:
            n_ids = len({r.get(a.id, "") for r in rs if r.get(a.id, "").strip()})
            out.append((abs(n_ids - rep) <= tol, abs(n_ids - rep), f"{desc}: {n_ids} distinct {a.id}"))
    show(out)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--where", action="append", default=[], help="a filter, 'column op value' (repeatable)")
    common.add_argument("--sheet")
    r = sub.add_parser("r", parents=[common])
    r.add_argument("data"); r.add_argument("x"); r.add_argument("y")
    r.add_argument("--reported", required=True)
    r.add_argument("--by"); r.add_argument("--complete", nargs="*", default=[])
    d = sub.add_parser("desc", parents=[common])
    d.add_argument("data"); d.add_argument("col")
    d.add_argument("--mean"); d.add_argument("--sd"); d.add_argument("--n")
    d.add_argument("--by"); d.add_argument("--complete", nargs="*", default=[])
    n = sub.add_parser("n", parents=[common])
    n.add_argument("data"); n.add_argument("--n", required=True); n.add_argument("--id")
    a = ap.parse_args()
    {"r": cmd_r, "desc": cmd_desc, "n": cmd_n}[a.cmd](a)


if __name__ == "__main__":
    main()
