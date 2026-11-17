# Checks on the manuscript and reported numbers (1i)

`check_all.py` (see SKILL.md) runs the three commands below in one call, on
the output of the run that worked: use it, and run them one by one only for a
second manuscript, or after you saved the text of a PDF yourself.

Get the text (`.docx`, `.odt`, `.md`, `.qmd`, `.Rmd`, `.Rnw`, `.tex`, `.html`,
`.pdf`):

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py text <manuscript> --out <tmp>/manuscript.txt
```

For a PDF it uses `pdftotext`, Ghostscript or `pypdf`, the first one available
(the scan summary says which); with none, read the PDF with your file-reading
tool and save its text. In R Markdown, Quarto or Sweave it also counts numbers
written by inline code (`` `r x` ``, `{r} x`, `\Sexpr{x}`): they come from the
code by construction; say so, and check them by rendering the document if R is
available. The script checks only numbers typed by hand.

Against section 11 of the rules:

- **Data availability**: repository and DOI, or "on request"?
- **Participants and exclusions**: does N match `n_participants`, and do the
  exclusions described match what the scripts do?
- **Version**: preprint, accepted manuscript, or the publisher's PDF (journal
  header, page numbers, copyright line)?

Then check the text against itself, which needs neither code nor data:

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py internal <tmp>/manuscript.txt
```

It reports whether the participant flow adds up (recruited − excluded = N,
and the reasons for exclusion add up to the total), whether group sizes add up
to N, whether percentages match their counts, whether degrees of freedom fit N
(r(178) needs N = 180), whether they are far larger than N (trials of the
same people treated as independent observations: a methods note for section
8, with the alternative, a test on participant means or a mixed model), and
lists the response scales and age ranges the text
declares. Compare these with the data: a scale "from 1 to 6" explains a 6 the
scan flagged; an age range "16 to 19" with a minimum of 15.5 in the data is a
finding. It is pattern matching on text (two-column PDFs mix lines): read the
sentence before reporting, and put what holds, after "Before the report",
under "Results that may be affected".

A manuscript without code still gets these checks. With no code and no
outputs, recompute what can be computed from the data alone (N, counts, means,
SDs, correlations of a descriptive table): `recompute.py` for N, means, SDs
and correlations (see SKILL.md), a short script in the temporary directory
for the rest. Compare, and label the column "recomputed from the data"; models
and tests stay "not verifiable without the code".

For the numbers you need the code's output (the `--logs` of 1f, tables the
scripts write; the logs of the fixed copy if the code ran only after a
portability fix; if the code was not run, the outputs already in the folder,
said in the report):

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py check <tmp>/manuscript.txt <tmp>/logs [<copy>/output] --out <tmp>/numbers.json
```

It knows frequentist (M, SD, t, F, chi2, r, b, d, eta2, R2, p, N, CI) and
Bayesian statistics (BF10, BF01, log BF, P(...), pd, R-hat, ESS, credible
intervals, HDIs, WAIC/LOO), thousands separators and decimal commas. It prints
what was not found, what was found in another form (opposite sign,
BF01 for BF10, log BF, percent for proportion, s for ms: reproduced, say how),
and weak matches (the number alone, without the statistic named nearby); the
statistics found with their name on the line are only counted. Judge:

- **not found**: computed by hand, in another program, or on data not in the
  folder; say which, after the explanations of "Before the report";
- **coincidence**: frequent for small integers and p-values; look at the line;
- **opposite sign**: usually a different reference level or contrast;
- **another form**: reproduced; say how (BF01 vs BF10, 95.8% vs 0.958, ms vs s);
- **number only**, in many places: weak; find the real line first;
- **close but different** (t = 2.45 reported, 2.61 in output): a discrepancy
  to explain.

Focus on the main results (abstract, results, tables).
