# Checks on code (1f–1g)

## 1f. Does the code run?

Find the run order (README first, then numbered names and the order the scan
summary gives), tell
the researcher you will run their code in a copy and how many scripts there
are, then:

```bash
python3 <skill-dir>/scripts/run_code.py <project-folder> [scripts in order] --timeout 600 --logs <tmp>/logs
```

It copies the project to a temporary directory and runs everything there from
the project root, so nothing reaches the researcher's folder. It prints one
line per script: status, the probable cause of a failure (missing package,
`setwd()`, an absolute path, a missing file), whether it failed after an
earlier script had already failed (then it is probably a consequence: report
the first failure as the cause), files created, and scripts that modify raw
data. The full JSON is in `<tmp>/logs/run_code.json` (with the last lines of
each error); each script's output in `<tmp>/logs/`. Experiment scripts
(PsychoPy's `.py`, files importing psychopy) are "not run": correct.

**Heavy models** (brms, Stan, simulations, bootstraps), as chosen in the triage:

- *Saved fits exist, not re-estimated (default).* If the code already loads
  them (`readRDS()`, `load()`, `brm(..., file = ...)` with the file present),
  just run it. If it fits and then saves, run with `--keep` and, in the
  temporary copy only, replace the fitting call with `fit <- readRDS("...")`;
  run that copy. Report "models not re-estimated, results checked from the
  saved fits `<file>`": this checks everything after the fit, not that the fit
  comes from this code and these data. Compare at least what the fit records
  (`fit$formula`, `nobs(fit)`) with the code and the data.
- *No saved fits.* Run them, with the longer timeout the researcher gave or
  the normal one; a script that reaches it is reported with the results it
  leaves unchecked. Skip them only if the researcher asked.

A script reaching the timeout is stopped with all its processes (`timeout`):
say how far it got and offer a longer `--timeout`.

**Projects with renv** (`renv.lock` and `renv/activate.R`): `run_code.py` runs
`renv::restore()` in the copy first, into the copy's own library, not the
researcher's. Tell the researcher it may take several minutes the first time;
`--no-renv` skips it. Report the outcome (the `renv:` line). Packages the
scripts load but `renv.lock` does not list (`code.packages_not_in_renv_lock`)
will be missing in the copy: a finding (the fix is `renv::snapshot()`), not
something to install.

**Other missing packages: do not install them** (it changes the researcher's
setup). List them and ask; that they were missing is a finding.

If the first failure is a portability problem (`setwd()`, an absolute path, a
path relative to the script's folder), find out whether the analysis works:
run with `--keep`, fix the line in the copy only, rerun
`run_code.py <copy> --logs <tmp>/logs`. Report both: "fails as deposited
because of X; once fixed, it runs" (or "then fails at Y"). This second run is
where substantive problems show up: check whether the problems of 1a survive
the cleaning and reach the analysis. Delete the copy afterwards.

Also report scripts that **modify** `data/raw/` (marked in the output), and
outputs the README promises that no script creates. With no
interpreter (no R, MATLAB, SPSS), say so and check only packages, paths and
files.

**Seeds.** For each script with `randomness` in the scan, report the functions
and whether a seed is fixed (`set.seed()`, `seed =` in `brm()`,
`np.random.seed`, `default_rng(1)`). Without one, MCMC, bootstraps, simulations and
random splits change at every run: the manuscript's numbers are reproducible
only approximately. Suggest the one-line fix, added by the authors or, with
their agreement, in the deposit. A seed does not carry over to the next script
(new R session).

## 1g. Packages

From `code.all_packages`, list what the project needs (the scan also reads
vectors of names loaded in a loop: `pkg <- c(...)` with
`lapply(pkg, library, character.only = TRUE)`, `for`, `ipak()`) and compare it
with what is declared (`renv.lock`,
`requirements.txt`, README). If R is available, get the installed versions for
the README:
`Rscript -e 'cat(sapply(c("pkg1","pkg2"), function(p) as.character(packageVersion(p))))'`.
