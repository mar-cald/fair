# Checks on data and documentation (1a–1e, 1h)

## 1a. Data

The scanner reports types, ranges and repeated values, and guesses from the
name and the values what each column measures (`role`):

| `role` | What the scanner checks |
|:--|:--|
| age | dates (dates of birth: personal data), years of birth, ages above 110, negative, far below the others, months instead of years |
| gender | numeric codes to explain in the dictionary; the same category written in different ways (`F`, `f`, `Femmina`, `female`) |
| reaction time | unit (seconds or milliseconds, from the median); values in the other unit; negative, 0, faster than 100 ms |
| accuracy | 0/1, proportion or percentage; other values |
| questionnaire item | families of items with the same prefix (`SA_1` ... `SA_8`); values outside the range the other items use (`questionnaire_items`) |
| condition or group | a factor written as numbers |
| education, percentage, proportion | values outside the possible range |

`derived_scores` recomputes, row by row, what can be computed from other
columns: a reversed item must be (max + min) − the item; a total or mean must
be the sum or mean of its items (all of them, every s-th one for a subscale,
or a block), with the reversed versions where they exist. A reversed column
that is not a reverse, a total that differs in some rows, or one that adds a
column on top of its items are facts about the file, and they change every
statistic computed on those scores: compare with the manuscript (the score's
mean or SD in a descriptive table) and, if the numbers differ, report it under
"Results that may be affected". Scores that match are useful too: they tell
the dictionary how each score is computed.

The role is a guess: confirm it with the README, the dictionary or the code,
and drop what does not apply (a column named `rt` in a table of results). A
value outside the range is reported, not corrected: say what it is likely to
be and let the researcher decide. Beyond that, use the column names, the
dictionary and the README to judge, and look for:

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
(initials?); absolute paths with a user name (OpenSesame, E-DataAid); free text;
dates of birth, also in a column with another name (an `Age` column holding
dates).
Also: published instruments, copyrighted stimuli, the publisher's PDF.

Age, gender, education, school, class and similar columns
(`indirect_identifiers`) do not identify anyone alone, and are often needed for
the analysis. Together they can: `unique_combinations` counts the participants
who are the only one with their combination of values. Many unique
combinations matter most when the sample comes from a small, known group (one
school, one class, a department) or the data are sensitive; suggest coarser
values (age in bands, a class without its section) or dropping the columns the
analysis does not use, and leave the decision to the researcher.

A participant ID that is itself personal (`participant_id_column_is_personal`)
must become a study code before sharing. Free text is flagged, not judged: read
a sample (without printing it) and say whether it holds identifying details.

Experiment files (`experiment_files`): are they in the folder, and can they be
shared (own material vs. third-party)?
