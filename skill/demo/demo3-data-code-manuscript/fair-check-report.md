# FAIR check — stroop_mindfulness

The folder contains **data, code and a preprint** from a Stroop study comparing
a mindfulness group with a control group:
- one PsychoPy file per participant (40 files);
- a participants table and the cleaned trial data;
- 2 R scripts and an RStudio project;
- a figure, the preprint (PDF) and a short README in Italian.

All checks were done, including the comparison between the preprint and the
code's output.

**The code is in good shape:** it runs as deposited, from the raw files to
the figure. But the folder has no license or dictionary. The preprint reports
a group comparison that the code does not produce (t = 1.86, p = .071 against
t = 0.86, p = .393), and trial exclusion limits different from the ones the
code applies.

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ✅ | 40 raw files with the same structure; IDs consistent; the 2 participants missing from the clean data are the 2 excluded |
| Folder structure and names | ⚠️ | Good layout; `Rplots.pdf` in the root, "final" in the preprint name |
| Formats | ✅ | All CSV |
| README | ⚠️ | File list present; missing how to read the data, how to reproduce, license, citation |
| Data dictionary | ❌ | None, for any of the three kinds of file |
| License | ❌ | None |
| Code runs | ✅ | Both scripts run from a clean copy; paths with `here()` |
| Declared packages | ⚠️ | tidyverse and here, not declared in the README |
| Manuscript and reported numbers | ❌ | The group t-test doesn't match; trial exclusion limits differ; data "on request" |
| Personal data and third-party material | ✅ | Nothing identifying |

## 1. Data files and consistency
- **`data/raw/psychopy/`:** 40 files, one per participant (96 trials each),
  all with the same 11 columns. Reaction times are in seconds (`key_resp.rt`).
- **`data/participants.csv`** has 40 participants, 20 per group, with the same
  IDs as the raw files.
- **`data/stroop_clean.csv`** (produced by `01_preprocessing.R`) has 38
  participants. The two missing, p13 and p28, are the ones the script
  excludes for accuracy below 80%, as its output states.

No inconsistencies found.

## 2. Folder structure and names → [rules](https://mar-cald.github.io/fair/struttura-1.html#struttura)
- **`Rplots.pdf`** in the root is a by-product. `02_analysis.R` prints a plot
  without a graphics device open, and R then writes it to this file.
- **`manuscript/preprint_v3_final.pdf`:** "v3_final" in the name; the version
  belongs in the repository's version number.
- **Folder names** `analysis/` and `figures/` will become `scripts/` and
  `output/figures/` in the deposit.

## 4. README → [rules](https://mar-cald.github.io/fair/struttura-1.html#readme)

The README has the title, the reference to the preprint, the folder list and
a contact. It is missing:
- the authors' ORCID;
- when the data were collected;
- what a row is in each file;
- the unit of `key_resp.rt` (seconds);
- the order of the scripts and the packages;
- the license and the citation.

## 5. Data dictionary → [rules](https://mar-cald.github.io/fair/struttura-1.html#data-dictionary)

There is none. The PsychoPy columns (`key_resp.corr`, `key_resp.rt`,
`trials.thisN`, `frameRate`) and the MAAS score (range, direction) are not
described anywhere.

## 6. License → [rules](https://mar-cald.github.io/fair/licenze.html)

There is none. Recommended:
- CC0 1.0 for the data;
- GPL-3.0 for the code;
- CC BY 4.0 for the preprint, the README and the figure.

The preprint is the authors' version ("not peer reviewed"), so it can be
deposited.

## 7. Code

Run in a temporary copy, with R 4.4.2.

| Script | Result | Notes |
|:--|:--|:--|
| `analysis/01_preprocessing.R` | ✅ runs | Reads the 40 raw files, excludes trials outside 150–2500 ms and participants below 80% accuracy (p13, p28); regenerates `data/stroop_clean.csv` |
| `analysis/02_analysis.R` | ✅ runs | Descriptives, t-test, Cohen's d, correlation; writes `figures/fig1_interference.png` (and `Rplots.pdf`) |

**Packages:** tidyverse 2.0.0, here 1.0.1.

## 8. Manuscript and reported numbers

**Statistics, preprint vs code output** (`02_analysis.R`):

| Statistic | In the preprint | Reported | Code output | Status |
|:--|:--|:--|:--|:--:|
| Interference, control | Results | M = 86.7 ms, SD = 49.7 | 86.7, 49.7 | ✅ |
| Interference, mindfulness | Results | M = 73.7 ms, SD = 42.5 | 73.7, 42.5 | ✅ |
| Group difference | Abstract, Results | **t(36) = 1.86, p = .071** | **t = 0.864, df = 36, p = .393** | ❌ |
| Effect size | Abstract, Results | d = 0.28 | 0.28 | ✅ |
| Interference × MAAS | Abstract, Results | r(36) = −.47, p = .003 | r = −0.466, df = 36, p = .0032 | ✅ |
| 95% CI of r | Results | [−0.68, −0.17] | [−0.684, −0.172] | ✅ |
| Sample | Participants | 38 (19 per group) after excluding 2 | 38; 19 + 19; p13, p28 excluded | ✅ |
| Age | Participants | M = 23.8, SD = 2.4; 22 women | not printed by any script | ⚠️ |

- **The group t-test doesn't match.** The code gives t = 0.86, p = .393; the
  preprint says t = 1.86, p = .071, in the abstract and in the results. The
  effect size (d = 0.28) matches the code, and d = 0.28 with 19 per group
  corresponds to t ≈ 0.86, so the reported t and p are probably the error.
  The conclusion ("not significant") does not change, but "did not reach
  significance" with p = .071 reads as a near effect that the data do not
  show.
- **Trial exclusion limits:** the preprint says reaction times below 200 ms or
  above 2000 ms were excluded; `01_preprocessing.R` uses 150 ms and 2500 ms.
  One of the two must be corrected, and the results checked again if it is
  the code.
- **Age and sex:** they are correct (computed from `participants.csv` on the 38
  analysed), but no script produces them. A reader can't trace them; one line
  in `02_analysis.R` would do it.
- **Data availability** says "available from the corresponding author upon
  reasonable request". Once the deposit has a DOI, the statement should point
  to it.

## What to fix first
1. **Correct the t-test in the preprint** (abstract and results) and **align the
   exclusion limits** between the methods and the code.
2. **Change the Data availability statement** to the DOI of the deposit.
3. **Write the dictionaries**, especially for the PsychoPy columns and the MAAS.
4. **Add the licenses and complete the README.**
5. **Optional:** compute age and sex in `02_analysis.R`.

## The deposit version

What goes where in `stroop_mindfulness_deposit/`:

| From | To |
|:--|:--|
| `data/raw/psychopy/*.csv` (40) | `data/raw/psychopy/` |
| `data/participants.csv` | `data/study-stroopmindfulness_description-participants_data.csv` |
| `data/stroop_clean.csv` | `data/study-stroopmindfulness_description-trials_data.csv` (regenerated by the script) |
| `analysis/01_preprocessing.R`, `02_analysis.R` | `scripts/` (paths updated) |
| `figures/fig1_interference.png` | `output/figures/` (regenerated) |
| `manuscript/preprint_v3_final.pdf` | `docs/preprint.pdf` |
| `stroop_mindfulness.Rproj` | root |
| `README.md` | rewritten (in Italian, like the original) |
| `Rplots.pdf` | left out: by-product of R |

The PsychoPy files stay in `data/raw/`, which the Psych-DS validator ignores.
They are described by their own dictionary.

Decisions needed from you:
- **The preprint:** correct it before depositing? The deposit includes it as it
  is now.
- **Which exclusion limits are right**, 150–2500 ms or 200–2000 ms?
- **Licenses:** CC0, GPL-3.0, CC BY 4.0?
- **ORCID, collection dates, DOI of the preprint.**
