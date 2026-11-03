"""Short summary of a fair_scan report, for the model to read first.

The full JSON can be 100,000+ characters on a real project (every column of
every table, every participant of every file). The summary keeps the findings
only, grouped by the areas of the report, each with its file or column and a
label:

  [certain]   a fact the scan established (a missing file, a date of birth,
              an LFS placeholder, setwd()): report it, after a glance
  [to check]  a rule that fired and may not apply (a value beyond the range of
              the other items, two files coding a column differently): verify
              in the data, the README or the code before reporting it

"Small things" are listed in one line each. The full JSON stays on disk: open
it only for the detail of one point (the key to look at is given in brackets).

It also opens with what this environment can and cannot do (R, pdftotext,
openpyxl, pyreadstat ...), so that what could not be checked here is not
mistaken for a problem of the folder.
"""

import importlib.util
import json
import re
import shutil
from collections import Counter
import subprocess
from pathlib import Path

MAX_PER_AREA = 60
MAX_PER_TABLE = 6
SMALL_ISSUES = ("missing values coded in more than one way", "values with leading/trailing spaces",
                "constant column", "column is entirely empty")


def small_kind(issue):
    return next((s for s in SMALL_ISSUES if s in issue), None)
CERTAIN_TABLE_ISSUES = ("rows with a different number of fields", "exact duplicate rows")
# personal-data flags that need a look before reporting; the others (a column named
# like an e-mail or a date of birth, values that look like one) are reported as they are
UNSURE_PERSONAL = ("free-text", "initials or names?")


def environment():
    """What the tools can use here, and what that means for the checks."""
    env, limits = {}, []
    r = shutil.which("Rscript")
    if r:
        try:
            v = subprocess.run([r, "-e", "cat(R.version$major, R.version$minor, sep = '.')"],
                               capture_output=True, text=True, timeout=30).stdout.strip()
        except Exception:  # noqa: BLE001
            v = "?"
        env["R"] = v or "?"
    else:
        limits.append("no R: R scripts cannot be run here (check packages, paths and files only; "
                      "say the code was not run, not that it fails)")
    pdf = next((t for t in ("pdftotext", "gs") if shutil.which(t)), None) or (
        "pypdf" if importlib.util.find_spec("pypdf") else None)
    env["PDF text"] = pdf or False
    if not pdf:
        limits.append("nothing reads PDF text here (pdftotext, Ghostscript, pypdf): read a PDF manuscript with "
                      "your file reader, or ask the researcher for its text")
    for tool, why in (("quarto", "Quarto documents (.qmd) cannot be rendered here"),
                      ("jupyter", "notebooks (.ipynb) cannot be run here")):
        if shutil.which(tool) or tool == "quarto" and Path(
                "/Applications/RStudio.app/Contents/Resources/app/quarto/bin/quarto").exists():
            env[tool] = True
        else:
            env[tool] = False
            limits.append(f"no {tool}: {why}")
    for mod, why in (("openpyxl", "Excel files (.xlsx) are not read: their content is not checked"),
                     ("pyreadstat", "SPSS, Stata and SAS files (.sav, .dta, .sas7bdat) are not read")):
        env[mod] = importlib.util.find_spec(mod) is not None
        if not env[mod]:
            limits.append(f"no {mod} (Python): {why}")
    return env, limits


def _short(x, n=160):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    return s if len(s) <= n else s[:n - 1] + "…"


class Area:
    def __init__(self, title):
        self.title, self.lines, self.small, self.extra = title, [], [], 0
        self.table, self.per_table, self.hidden = None, {}, {}

    def end_table(self, index):
        n = self.hidden.get(self.table, 0)
        if n:
            self.info(f"  … {n} more for this table (data[{index}])")
        self.table = None

    def add(self, label, where, what):
        if self.table is not None:
            self.per_table[self.table] = self.per_table.get(self.table, 0) + 1
            if self.per_table[self.table] > MAX_PER_TABLE:
                self.hidden[self.table] = self.hidden.get(self.table, 0) + 1
                return
        if len(self.lines) >= MAX_PER_AREA:
            self.extra += 1
            return
        self.lines.append(f"- [{label}] {where}: {_short(what, 220)}" if where else f"- [{label}] {_short(what, 220)}")

    def info(self, text):
        if len(self.lines) < MAX_PER_AREA:
            self.lines.append(f"- {_short(text, 300)}")

    def render(self):
        out = [f"## {self.title}"]
        out += self.lines or ["- nothing found by the scan"]
        if self.extra:
            out.append(f"- … {self.extra} more findings in the full JSON")
        if self.small:
            out.append("- small things (mention in one sentence each):")
            groups = {}
            for kind, where in self.small:
                groups.setdefault(kind, []).append(where)
            for kind, wheres in groups.items():
                out.append(f"  - {kind}: {len(wheres)} columns, e.g. " + "; ".join(wheres[:4]))
        return "\n".join(out)


def _tables(report):
    """Tables and file sets, with an index into report['data']."""
    for i, t in enumerate(report.get("data", [])):
        yield i, t.get("file_set") or t.get("file", "?"), t


def summarise(report, json_path=None):
    env, limits = environment()
    mp = report.get("materials_present", {})
    head = [f"# fair_scan summary — {report.get('project', '?')}",
            "",
            f"{report.get('n_files', '?')} files, {report.get('n_dirs', '?')} folders, "
            f"{report.get('total_size_mb', '?')} MB. Material found: " +
            (", ".join(k for k, v in mp.items() if v) or "none") + ".",
            "Labels: [certain] = established by the scan; [to check] = verify before reporting."]
    if json_path:
        head.append(f"Full detail: `{json_path}` (open only for one point; the key is given in brackets).")
    head += ["", "## What this environment can do"]
    head.append("- available: " + (", ".join(f"R {v}" if k == "R" else f"PDF text ({v})" if k == "PDF text" else k
                                          for k, v in env.items() if v) or "Python only"))
    head += [f"- {x}" for x in limits] or ["- every tool the skill uses is available"]
    for x in report.get("data_not_read", []):
        head.append(f"- not read: {x.get('file')}: {_short(x.get('reason', ''), 140)}")

    data = Area("1. Data files and consistency")
    struct = Area("2. Folder structure and names")
    fmts = Area("3. Formats")
    readme = Area("4. README")
    dic = Area("5. Data dictionary")
    lic = Area("6. License")
    code = Area("7. Code and packages")
    man = Area("8. Manuscript")
    pers = Area("9. Personal data and third-party material")

    # --- data
    # folder-wide findings first: the per-table lines can be many
    for col, xs in (report.get("cross_file_type_inconsistencies") or {}).items():
        if not col.strip():
            continue
        data.add("to check", f"column '{col}' across files", "different types: " + ", ".join(xs[:4]))
    for c in (report.get("same_name_different_values") or {}).get("columns", []):
        data.add("to check", f"column '{c['name']}' in {len(c.get('files', []))} files",
                 "; ".join(c.get("why", []))[:160])
    cfp = report.get("cross_file_participants") or []
    shown = 0
    for p in cfp:
        bits = []
        if p.get("only_in_first"):
            bits.append(f"{len(p['only_in_first'])} IDs only in the first ({', '.join(p['only_in_first'][:3])})")
        if p.get("only_in_second"):
            bits.append(f"{len(p['only_in_second'])} only in the second ({', '.join(p['only_in_second'][:3])})")
        for v in p.get("values_disagree", []):
            bits.append(f"{'/'.join(dict.fromkeys(v['columns']))} differs for {v.get('n_participants')} "
                        f"participants (e.g. {', '.join(v.get('examples', [])[:2])})")
        if bits and shown < 6:
            data.add("to check", " vs ".join(f"`{f}`" for f in p["files"]), "; ".join(bits))
            shown += 1
    if len(cfp) > shown and shown:
        data.info(f"… {len(cfp) - shown} more file pairs compared (cross_file_participants)")
    for g in (report.get("identical_files") or {}).get("groups", []):
        data.add("certain", "identical files", ", ".join(f"`{x}`" for x in g))
    lfs = report.get("lfs_pointers")
    if lfs:
        data.add("certain", "Git LFS placeholders, not data, in this copy",
                 ", ".join(f"`{x['file']}`" for x in lfs["files"][:8]) +
                 " — ask whether the researcher's copy has the real files")
    if report.get("archives"):
        data.add("certain", "archives not checked", ", ".join(report["archives"]["files"][:6]) +
                 " — extract them and scan again")

    for i, name, t in _tables(report):
        desc = f"`{name}`: {t.get('n_rows', t.get('n_rows_total', '?'))} rows"
        if t.get("n_cols"):
            desc += f" × {t['n_cols']} columns"
        if t.get("n_files"):
            desc += f", {t['n_files']} files"
        if t.get("software"):
            desc += f", {t['software']}"
        if t.get("n_participants"):
            desc += f", {t['n_participants']} participants ({t.get('participant_id_column')})"
        roles = [f"{c['name']}={c['role']}" for c in t.get("columns", []) if c.get("role")
                 and not c["role"].startswith("questionnaire item")]
        if roles:
            desc += "; recognised: " + ", ".join(roles[:8]) + (" …" if len(roles) > 8 else "")
        data.info(desc)
        data.table = name
        if t.get("error"):
            data.add("certain", f"`{name}`", t["error"])
        hi = t.get("header_issues", [])
        named = [x for x in hi if x.startswith("'") and "': " in x]
        no_name = [x for x in hi if x.endswith("has no name")]
        for x in hi:
            if (x not in named or len(named) <= 3) and (x not in no_name or len(no_name) <= 2):
                data.add("certain", f"`{name}` header", x)
        if len(no_name) > 2:
            data.add("certain", f"`{name}` header", f"{len(no_name)} columns have no name (" +
                     ", ".join(x.split(" has")[0] for x in no_name[:6]) + (" …" if len(no_name) > 6 else "") + ")")
        if len(named) > 3:
            kinds = Counter(p.strip() for x in named for p in x.rsplit("': ", 1)[1].split(","))
            examples = [x[1:].rsplit("': ", 1)[0] for x in named[:3]]
            data.add("certain", f"`{name}` header", f"{len(named)} column names with problems (" +
                     ", ".join(f"{k} x{n}" for k, n in kinds.most_common()) + "), e.g. " +
                     ", ".join(f"'{_short(e, 40)}'" for e in examples))
        for x in t.get("issues", []):
            data.add("certain" if x.split(" ", 1)[-1].startswith(CERTAIN_TABLE_ISSUES) or "duplicate" in x
                     else "to check", f"`{name}`", x)
        for c in t.get("columns", []):
            for x in c.get("issues", []):
                if small_kind(x):
                    data.small.append((small_kind(x), f"{Path(name).name} {_short(c['name'], 30)}"))
                else:
                    data.add("certain" if "values are dates" in x else "to check", f"`{name}` · {c['name']}", x)
        # in a set of files with the same columns, the same finding in many files is one line
        same = {}
        for f, xs in (t.get("issues_by_file") or {}).items():
            for x in xs:
                if small_kind(x):
                    data.small.append((small_kind(x), f"{Path(f).name} {_short(x.split(':')[0], 30)}"))
                else:
                    same.setdefault(re.sub(r"^([^:]+: )\d+ (\w+?)s? ", r"\1some \2s ", x), []).append((f, x))
        for key, hits in same.items():
            if len(hits) == 1:
                data.add("to check", f"`{hits[0][0]}`", hits[0][1])
            else:
                files = [Path(f).name for f, _ in hits]
                data.add("to check", f"{len(hits)} files of the set ({', '.join(files[:3])}{' …' if len(files) > 3 else ''})", key)
        ds = t.get("derived_scores") or {}
        for rv in ds.get("reversed_items", []):
            if rv.get("not_a_reverse"):
                data.add("certain", f"`{name}` · {rv['item']}", rv["note"])
            else:
                data.add("certain", f"`{name}` · {rv['item']}",
                         f"not the reverse of {rv['of']} in {rv['rows_not_reversed']} of {rv['of_rows']} rows "
                         f"({', '.join(rv['examples'])}); {rv['rule']}")
        ok_scores = []
        for sc in ds.get("scores", []):
            miss = (f"; present in {sc['rows_with_missing_items']} rows where some items are missing "
                    f"({', '.join(sc['examples_missing_items'])}): computed on fewer items?") \
                if sc.get("rows_with_missing_items") else ""
            if sc["status"] == "matches":
                ok_scores.append(f"{sc['column']} = {sc['rule']}")
                if miss:
                    data.add("to check", f"`{name}` · {sc['column']}", miss[2:])
            elif sc["status"] == "differs in some rows":
                data.add("certain", f"`{name}` · {sc['column']}",
                         f"is the {sc['rule']} except in {sc['rows_differing']} of {sc['rows']} rows "
                         f"({', '.join(sc['examples'])}){miss}")
            else:
                data.add("certain" if sc["status"] == "sum plus one column" else "to check",
                         f"`{name}` · {sc['column']}", sc["note"])
        if ok_scores:
            data.info(f"  scores recomputed from their items and matching: " + "; ".join(ok_scores[:8]) +
                      (" …" if len(ok_scores) > 8 else ""))
        for c in t.get("columns", []):
            for x in c.get("to_check", []):
                if not x.startswith("values outside"):  # already in the questionnaire_items line
                    data.add("to check", f"`{name}` · {c['name']}", x)
        for x in t.get("within_participant_inconsistencies", []) or []:
            data.add("to check", f"`{name}` same participant, different values", x)
        for fam in t.get("questionnaire_items", []) or []:
            odd = fam.get("values_beyond_most_items") or fam.get("values_outside_range")
            if odd:
                rng = fam.get("observed_range_of_most_items") or fam.get("range")
                data.add("to check", f"`{name}` items {fam.get('family')}_ (most use {rng})",
                         ", ".join(odd[:6]) + " — compare with the documented response scale")
        if t.get("broken_accents"):
            data.add("certain", f"`{name}`", f"broken accents (wrong encoding): {_short(t['broken_accents'], 120)}")
        data.end_table(i)
    # --- structure and names
    by_problem = {}
    for n in (report.get("naming") or {}).get("problems", []):
        for p in n["problems"]:
            by_problem.setdefault(p, []).append(n["path"])
    for p, paths in by_problem.items():
        struct.add("certain", p, ", ".join(f"`{x}`" for x in paths[:6]) + (f" … ({len(paths)})" if len(paths) > 6 else ""))
    for n in (report.get("naming") or {}).get("numbering", []):
        struct.add("certain", f"`{n['folder']}/`", n["problem"])
    st = report.get("structure", {})
    if st:
        found = "; ".join(f"{k.replace('_dir', '')}: {', '.join(v)}" for k, v in st.items() if k.endswith("_dir") and v)
        struct.info("folders found: " + (found or "none (everything in the root)") +
                    f"; files in the root: {len(st.get('files_in_root', []))}; depth {st.get('max_depth')}")
        if st.get("empty_dirs"):
            struct.add("certain", "empty folders", ", ".join(st["empty_dirs"][:8]))
    if report.get("nested_readmes"):
        struct.info(f"other README files: {_short(report['nested_readmes'], 160)}")
    ps = report.get("psychds") or {}
    if ps.get("problems"):
        struct.info("Psych-DS (only if chosen): " + "; ".join(ps["problems"][:4]))

    # --- formats
    f = report.get("formats", {})
    for x in f.get("proprietary_data", []):
        if x.get("lfs_pointer"):
            continue
        if x.get("open_copy_exists"):
            fmts.info(f"`{x['file']}` ({x['format']}) has an open copy" +
                      (f": {_short(x.get('open_copy_check'), 100)}" if x.get("open_copy_check") else ""))
        elif x["format"].startswith("R "):
            fmts.add("to check", f"`{x['file']}`", f"{x['format']} with no open copy (fine for a fitted model "
                                                  "or an R object; data need an open copy)")
        else:
            fmts.add("certain", f"`{x['file']}`", f"{x['format']} with no open copy")
    for x in f.get("proprietary_docs", []):
        fmts.add("certain", f"`{x['file'] if isinstance(x, dict) else x}`",
                 f"{x.get('format', 'proprietary document') if isinstance(x, dict) else 'proprietary document'}")
    fmts.info(f"{len(f.get('open_tabular', []))} open tabular files")

    # --- README
    rd = report.get("readme")
    if not rd:
        readme.add("certain", "", "no README")
    else:
        missing = [k for k, v in rd.get("sections", {}).items() if not v]
        readme.info(f"`{rd.get('file')}`: {rd.get('n_words')} words; booklet sections found: " +
                    ", ".join(k for k, v in rd.get("sections", {}).items() if v))
        if missing:
            readme.add("certain", "sections not found", ", ".join(missing) + " (keyword search: read the README)")
        if rd.get("placeholders"):
            readme.add("certain", "placeholders", ", ".join(rd["placeholders"][:6]))
        nm = rd.get("files_not_mentioned", [])
        if nm:
            readme.add("to check", f"{len(nm)} files never named", ", ".join(nm[:8]) + (" …" if len(nm) > 8 else ""))

    # --- dictionaries
    d = report.get("dictionaries", {})
    if d.get("dictionary_files"):
        dic.info("dictionaries: " + ", ".join(d["dictionary_files"][:8]))
    for x in d.get("non_csv_dictionaries", []):
        dic.add("certain", f"`{x}`", "dictionary present but not machine-readable (not CSV)")
    without = [c["data"] for c in d.get("coverage", []) if not c.get("dictionary")]
    if without:
        dic.add("certain", f"{len(without)} data files without a dictionary",
                ", ".join(f"`{x}`" for x in without[:8]) + (" …" if len(without) > 8 else ""))
    for c in d.get("coverage", []):
        if c.get("dictionary"):
            for k, v in c.items():
                if k not in ("data", "dictionary", "n_variables_described") and v:
                    dic.add("certain", f"`{c['data']}` vs `{c['dictionary']}`", f"{k}: {_short(v, 150)}")

    # --- license
    li = report.get("licenses", {})
    found = [f"{x.get('file')}: {', '.join(x.get('detected', [])) or 'not recognised'}" for x in li.get("files", [])]
    if found or li.get("readme_detected"):
        lic.info("; ".join(found + ([f"README mentions {', '.join(li['readme_detected'])}"] if li.get("readme_detected") else [])))
    else:
        lic.add("certain", "", "no license file and no license in the README")

    # --- code
    c = report.get("code", {})
    for x in c.get("files", []):
        where = f"`{x['file']}`"
        for i in x.get("issues", []):
            code.add("certain", where, i)
        if x.get("referenced_files_not_found"):
            code.add("certain", where, "reads files not in the folder: " + ", ".join(x["referenced_files_not_found"][:5]))
        for i in x.get("functions_without_their_package", []) or []:
            code.add("to check", where, i)
        if x.get("uses_current_date"):
            code.add("to check", where, f"uses today's date ({', '.join(x['uses_current_date'].get('calls', []))}) "
                                        f"at lines {x['uses_current_date'].get('lines')}")
    dep = c.get("dependencies", {})
    for x in dep.get("numbered_before_what_they_need", []):
        code.add("certain", "run order", x)
    if dep.get("circular"):
        code.add("certain", "circular dependency", ", ".join(dep["circular"].get("scripts", [])))
    lfs_files = {x["file"] for x in (report.get("lfs_pointers") or {}).get("files", [])}
    for x in dep.get("inputs_written_by_no_script", []):
        if x["file"] in lfs_files:
            continue  # already reported as an LFS placeholder
        code.add("certain", f"`{x['file']}`", f"read by {', '.join(x.get('read_by', []))} but written by no script "
                                             "and not in the folder's raw data: where does it come from?")
    if c.get("files"):
        code.info(f"{len(c['files'])} scripts; packages: {', '.join(c.get('all_packages', [])) or 'none'}")
        code.info("environment files: " + (", ".join(c.get("environment", {})) or "none (packages declared nowhere)"))
        if dep.get("run_order_from_files"):
            code.info("order from file names and inputs: " + " → ".join(dep["run_order_from_files"][:12]) +
                      (" …" if len(dep["run_order_from_files"]) > 12 else ""))
    if c.get("packages_not_in_renv_lock"):
        code.add("certain", "renv.lock", "packages used but not in renv.lock: " + ", ".join(c["packages_not_in_renv_lock"]))
    exp = report.get("experiment_files") or []
    if exp:
        code.info(f"experiment files (material, never run): {', '.join(e.get('file', '?') for e in exp[:6])}")

    # --- manuscript
    for m in report.get("manuscripts", []):
        man.info(f"`{m['file']}` ({m.get('format')}, {m.get('size_kb')} KB)")

    # --- personal data
    for i, name, t in _tables(report):
        for p in t.get("possible_personal_data", []) or []:
            if isinstance(p, str):
                pers.add("to check", f"`{name}`", p)
                continue
            fl = "; ".join(p.get("flags", []))
            pers.add("to check" if any(k in fl for k in UNSURE_PERSONAL) else "certain",
                     f"`{name}` · {p.get('column')}", fl)
        if t.get("participant_id_column_is_personal"):
            pers.add("certain", f"`{name}`", t["participant_id_column_is_personal"])
        ind = t.get("indirect_identifiers")
        if ind and ind.get("unique_combinations"):
            pers.add("to check", f"`{name}` indirect identifiers ({', '.join(ind['columns'])})",
                     f"{ind['unique_combinations']} of {ind['participants']} participants are the only one "
                     "with their combination")

    if not mp.get("code"):
        code.info("no code in the folder")
    for x in (report.get("other_documents") or {}).get("files", []):
        man.add("to check", f"`{x}`", "a document not recognised by its name: open it, it may be the manuscript")
    if not mp.get("manuscript") and not report.get("other_documents"):
        man.info("no manuscript in the folder")
    areas = [data, struct, fmts, readme, dic, lic, code, man, pers]
    return "\n".join(head) + "\n\n" + "\n\n".join(a.render() for a in areas) + "\n"
