# Checks on data and documentation (1a–1e, 1h)

## 1a. Data

The scanner reports types, ranges and repeated values; it cannot tell whether
a value makes sense. Use the column names, the dictionary and the README to
judge, and look for:

- values outside a plausible range (negative reaction times, age 250, a Likert
  item scored 8 on a 1–7 scale, a total above the questionnaire's maximum);
- the same variable coded differently in different files (`F`/`M` in one,
  `1`/`2` in another): the scanner compares only columns with the same coding,
  so check by hand, participant by participant;
- `n_participants` against what the README or the manuscript says;
- what a row is: experiment software often writes one row per event or screen,
  not per trial (Gorilla, jsPsych, PsychoPy); check which rows the analysis
  keeps, and the units of time columns (PsychoPy rt in seconds, others in ms;
  E-Prime RT 0 = no response). See `software-exports.md`;
- the rows an export adds around the data (`export_structure`): not errors in
  a raw file, but the README must mention them and the scripts handle them;
- proprietary files (`.xlsx`, `.sav`) with no open copy: if R is available,
  read them (`readxl::read_excel`, `haven::read_sav`) to check them like the
  others, and to compare them with an open file next to them.

Look at summaries (a few rows, counts of unique values), never at whole files:
they can be large and hold personal data. Never print the values of columns
flagged in `possible_personal_data`; report the column name and why.

## 1b. Structure, names, formats

From `naming`, `formats` and `structure`, against sections 1–3 of the rules.
Note what does not belong in a deposit (section 9): old scripts, empty folders,
system files, duplicates, test runs (`quickrun.csv`). A proprietary file with
an open copy (`open_copy_exists`) is fine; `open_copy_check` says whether they
hold the same table.

Every open format (`.csv`, `.tsv`, `.txt`, `.json`) is fine for FAIR: a `.tsv`
is not a problem. Conversion to `.csv` belongs to Psych-DS: mention it only if
the researcher chose Psych-DS, as part of step 3, not as a finding. UTF-16 files
(E-Prime, Qualtrics TSV) are open but awkward: note it.

## 1c. README

Read it in full. `readme.sections` says which booklet sections appear,
`readme.files_not_mentioned` which files are never named; only reading tells
whether a stranger would understand what a row of each file is, when and how
data were collected, and in which order the scripts run.

## 1d. Data dictionary

From `dictionaries.coverage`: files without a dictionary, columns not
described, names that do not match, values outside `allowed_values`, codes not
in `coding`. A dictionary in `.docx` or `.pdf` is present but not
machine-readable.

## 1e. License

Decide which license covers each component (data, code, manuscript, own and
third-party materials) from the LICENSE file(s), the README and metadata files
(`CITATION.cff`, `DESCRIPTION`), against section 6 of the rules. Typical
problems: no license; one license for everything; Creative Commons on code; a
software license (MIT, GPL) on data; CC BY-NC or CC BY-ND on data; a LICENSE
naming a license without its text; third-party instruments or the publisher's
PDF in the folder.

## 1h. Personal data and third-party material

From `possible_personal_data` and the materials, against section 8 of the
rules. The scan flags columns by name, label (Qualtrics question text) and
values: names, e-mails, phone numbers, tax codes; IP addresses, coordinates;
recruitment-platform IDs (Prolific, MTurk, Gorilla Public ID); letter-only IDs
(initials?); absolute paths with a user name (OpenSesame, E-DataAid); free text.
Also: published instruments, copyrighted stimuli, the publisher's PDF.

A participant ID that is itself personal (`participant_id_column_is_personal`)
must become a study code before sharing. Free text is flagged, not judged: read
a sample (without printing it) and say whether it holds identifying details.

Experiment files (`experiment_files`): are they in the folder, and can they be
shared (own material vs. third-party)?
