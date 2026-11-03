# Checks on code (1f–1g)

## 1f. Does the code run?

Find the run order (README first, then numbered names), then:

```bash
python3 <skill-dir>/scripts/run_code.py <project-folder> [scripts in order] --timeout 600 --logs <tmp>/logs
```

It copies the project to a temporary directory and runs everything there from
the project root, so nothing reaches the researcher's folder. Per script it
reports success or error, the last lines of the error, missing packages, files
created or modified; `--logs` saves what each script printed.

Before running, tell the researcher you will run their code in a copy, and how
many scripts there are.

**Heavy models** (brms, Stan, simulations, bootstraps), as chosen in the triage:

- *Saved fits exist, not re-estimated (default).* If the code already loads
  them (`readRDS()`, `load()`, `brm(..., file = ...)` with the file present),
  just run it. If it fits and then saves, run with `--keep` and, in the
  temporary copy only, replace the fitting call with `fit <- readRDS("...")`;
  run that copy. Report "models not re-estimated, results checked from the
  saved fits `<file>`": this checks everything after the fit, not that the fit
  comes from this code and these data. Compare at least what the fit records
  (formula, number of observations: `fit$formula`, `nobs(fit)`) with the code
  and the data.
- *No saved fits.* Run with the longer timeout the researcher gave, or skip
  them and say which results were not checked.

**Missing packages: do not install them on your own** (it changes the
researcher's setup). List them and ask; that they were missing is a finding.

A script reaching the timeout is stopped with all its processes and reported
as `timeout`: say how far it got and offer a longer `--timeout`. Experiment
scripts (PsychoPy's `.py`, files importing psychopy) are "not run": correct.

When a script fails, later ones often fail only because they read its outputs:
report the first failure as the cause, the others as consequences.

If the first failure is a portability problem (`setwd()`, an absolute path, a
path relative to the script's folder), find out whether the analysis works:
run with `--keep`, fix the line in the copy only, rerun `run_code.py <copy>
--logs <tmp>/logs`. Report both: "fails as deposited because of X; once fixed,
it runs" (or "then fails at Y"). This second run is where substantive problems
show up: check whether the problems of 1a survive the cleaning and reach the
analysis. Delete the copy afterwards.

Also report scripts that **modify** `data/raw/`, and outputs the README promises
that no script creates. With no interpreter (no R, MATLAB, SPSS), say so and
check only packages, paths and files.

**Seeds.** For each script with `randomness`, report the functions and whether
a seed is fixed (`set.seed()`, `seed =` in `brm()`, `np.random.seed`,
`default_rng(1)`). Without one, MCMC, bootstraps, simulations and random splits
change at every run: the manuscript's numbers are reproducible only
approximately. Suggest the one-line fix, added by the authors or, with their
agreement, in the deposit. A seed does not carry over to the next script (new
R session).

## 1g. Packages

From `code.all_packages`, list what the project needs and compare it with what
is declared (`renv.lock`, `requirements.txt`, README). If R is available, get
the installed versions for the README:
`Rscript -e 'cat(sapply(c("pkg1","pkg2"), function(p) as.character(packageVersion(p))))'`.
