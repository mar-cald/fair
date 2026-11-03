# Checks on the manuscript and reported numbers (1i)

Get the text (`.docx`, `.odt`, `.md`, `.qmd`, `.Rmd`, `.Rnw`, `.tex`, `.html`):

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py text <manuscript> --out <tmp>/manuscript.txt
```

For a PDF it uses `pdftotext` if installed; otherwise read the PDF with your
file-reading tool and save its text. In R Markdown, Quarto or Sweave it also
counts numbers written by inline code (`` `r x` ``, `{r} x`, `\Sexpr{x}`): they
come from the code by construction; say so, and check them by rendering the
document if R is available. The script checks only numbers typed by hand.

Against section 11 of the rules:

- **Data availability**: repository and DOI, or "on request"?
- **Participants and exclusions**: does N match `n_participants`, and do the
  exclusions described match what the scripts do?
- **Version**: preprint, accepted manuscript, or the publisher's PDF (journal
  header, page numbers, copyright line)?

A manuscript without code still gets these checks.

For the numbers you need the code's output (`--logs` of 1f, tables the scripts
write; the logs of the fixed copy if the code ran only after a portability fix;
if the code was not run, the outputs already in the folder, said in the report):

```bash
python3 <skill-dir>/scripts/manuscript_numbers.py check <tmp>/manuscript.txt <tmp>/logs [<copy>/output]
```

It lists every statistic with its sentence and whether a value rounding to it
appears in the output. It knows frequentist (M, SD, t, F, chi2, r, b, d, eta2,
R2, p, N, CI) and Bayesian statistics (BF10, BF01, log BF, P(...), pd, R-hat,
ESS, credible intervals, HDIs, WAIC/LOO), thousands separators and decimal
commas. Per match: `context` (the output names the statistic on that line or
just above) and `n_places`. Judge:

- **not found**: computed by hand, in another program, or on data not in the
  folder; say which;
- **coincidence**: frequent for small integers and p-values; look at the line;
- **opposite sign**: usually a different reference level or contrast;
- **another form**: BF01 vs BF10, log BF, 95.8% vs 0.958, ms vs s: reproduced,
  say how;
- **number only** with many `n_places`: weak; find the real line first;
- **close but different** (t = 2.45 reported, 2.61 in output): a discrepancy.

Focus on the main results (abstract, results, tables).
