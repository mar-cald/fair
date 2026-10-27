# Files from experiment and survey software

Read this when the scan reports a `software` for a data file, or lists
`experiment_files`. For each program: what its files are, what the scanner
does with them, what to check, and where each file goes in the deposit.

## Contents

0. What the scanner does with any export
1. Qualtrics
2. PsychoPy (and Pavlovia)
3. jsPsych (and JATOS, Pavlovia, cognition.run)
4. Gorilla
5. OpenSesame (and OSWeb)
6. E-Prime
7. Other programs

---

## 0. What the scanner does with any export

Exports often add rows around the data, or store it in formats that are not
plain CSV. The scanner sets these aside before checking the data, and says so
in `export_structure` (per file) so the report can describe them:

| Key | What it is | Example |
|:--|:--|:--|
| `preamble_lines` | lines above the header | E-DataAid writes the path of the `.edat` file |
| `label_rows` | rows under the header that describe the columns | Qualtrics question text and ImportId |
| `footer_rows` | rows after the data | "END OF FILE" in Gorilla downloads |
| `empty_last_column` | an unnamed, empty last column | every PsychoPy row ends with a comma |

These are not errors in a raw export: the program wrote them. They matter in
three places:
- **README and dictionary**: say that the raw file has them.
- **Scripts**: check that they handle them (`skip = 1`, `[-c(1, 2), ]`,
  `qualtRics::read_survey()`).
- **Deposit**: the files in `data/` (the Psych-DS ones) should not have them.

Other things the scanner reports:

- **`encoding`: utf-16**. E-Prime logs and exports, and Qualtrics TSV
  exports, are UTF-16. Many tools expect UTF-8. The deposit's CSV copies are
  UTF-8.
- **`format`**: "JSON records", "E-Prime log", "Excel" (read with openpyxl),
  SPSS (read with pyreadstat, if installed). `data_not_read` lists data files
  it could not open, and why.
- **file sets**: one file per participant or session, with (nearly) the same
  columns, is reported once. `columns_not_in_every_file` lists the columns
  some files lack, often a component that never ran for that participant.
- **cells holding lists or JSON objects**: several key presses in one cell
  (`['f', 'j']`), survey answers as `{"Q0": "..."}`. The dictionary must say
  what is inside (`json_keys` lists the keys), or a script should unpack them.
- **`participant_id_column_is_personal`**: the only column that identifies
  participants holds personal data, usually a Prolific ID. It has to be
  replaced by study codes. The key linking codes to IDs stays with the
  researcher, never in the deposit.
- **IDs that are letters only**: initials or names typed at the start of a
  session (PsychoPy, OpenSesame). Check the IDs and the file names.
- **`experiment_files`**: the instrument (`.psyexp`, `.osexp`, `.es3`, jsPsych
  HTML/JS, `.qsf`). It goes in `materials/`. `run_code.py` does not run it.

---

## 1. Qualtrics

**Files.** Data exports:
- CSV (UTF-8 with BOM);
- TSV (often UTF-16);
- Excel;
- SPSS `.sav`.

Each export is either "numeric values" or "choice text": say which in the
README. The survey itself can be exported as `.qsf`, the survey definition in
JSON; that is material, not data.

**Structure.** Three header rows:
1. variable names;
2. question text;
3. `{"ImportId": ...}`.

The legacy export has two: `V1, V2 ...` and then names with question text.
The scanner treats rows 2–3 as `label_rows`. `draft_dictionary.py` takes the
question text as the `label` (marked "to check").

**Columns written by Qualtrics.**
- `StartDate`, `EndDate`, `RecordedDate`.
- `Status`: 0 is a normal response; other values mark previews, tests,
  imports, spam and offline responses.
- `Progress` (%), `Duration (in seconds)`, `Finished` (1/0).
- `ResponseId`, `DistributionChannel`, `UserLanguage`.
- Timing questions: `Qx_First Click`, `_Last Click`, `_Page Submit` (seconds),
  `_Click Count`.

**What to check.**
- Do the scripts exclude previews and tests (`Status`, or
  `DistributionChannel == "preview"`) and unfinished responses (`Finished`)?
  Is the exclusion described?
- Do the N in the manuscript and in the data agree after those exclusions?
- Answer scales: are they numeric or text? Are reverse-scored items recoded
  in a script?

**Personal data.** These must not be in the deposit:
- `IPAddress`;
- `LocationLatitude`, `LocationLongitude` (estimated from the IP);
- `RecipientLastName`, `RecipientFirstName`, `RecipientEmail` (contact lists);
- `ExternalReference` (often a student or panel ID);
- free-text answers (`_TEXT` columns): read them.

**Deposit.**
- The raw export goes in `data/raw/`, with those columns dropped (`"data"`
  entry with `drop`). Keep its format (`"normalise": false`) if the scripts
  read it.
- The cleaned data produced by the scripts goes in `data/`.
- In a data-only project, a `csv_copies` entry writes the Psych-DS file
  without the label rows.
- The `.qsf` goes in `materials/`, if the questions are the authors' own.
  Published questionnaires are third-party material (rules, section 8).

## 2. PsychoPy (and Pavlovia)

**Files.**
- One CSV per session, named `<participant>_<expName>_<date>.csv`, one row
  per trial (and per non-loop routine). This is the data.
- `.log`: a time-stamped event log. Not needed for the analysis; it can stay
  in `data/raw/` or be left out.
- `.psydat`: a Python pickle that opens only with Python and PsychoPy. Not an
  open format; the CSV is its open version.
- Pavlovia writes the same CSVs.

The experiment is made of:
- the `.psyexp` (Builder, XML);
- the conditions files (`.xlsx`/`.csv`);
- the stimuli;
- the generated `<name>.py` and `<name>_lastrun.py`;
- for online studies, the PsychoJS `.js`.

**Columns written by PsychoPy.**
- `<component>.rt`: in **seconds**, from the start of the component.
- `<component>.keys`, `.corr` (1/0), `.duration`, `.started`, `.stopped`.
- `<loop>.thisRepN`, `.thisTrialN`, `.thisN`, `.thisIndex`: counted from 0.
- From the start dialog and the session: `participant`, `session`, `date`,
  `expName`, `psychopyVersion`, `frameRate` (Hz), `expStart`.

**Quirks.**
- Every row ends with a comma, so there is an empty unnamed last column.
- `None` marks missing values.
- Several key presses give lists in one cell (`['f', 'j']`), with matching
  lists of rts.
- Rows for instruction routines have empty trial columns.
- Files of different participants can have different columns.

**What to check.**
- Are rt in seconds converted to ms in the scripts, consistently with the
  manuscript?
- Which rows does the analysis keep (practice vs. main loop)?
- Is `participant` typed consistently (`01`, `1`, `P01`)? The scanner compares
  IDs across files.

**Personal data.** `participant` is typed by hand and is sometimes initials
or a name, which then appear in the file name too. Rename both in the deposit
(file names in the plan; values in a script or in the deposit's copy, listed
in the README).

**Deposit.**
- The per-session CSVs go in `data/raw/psychopy/`, or in `data/` as
  `study-<name>_subject-<id>_data.csv`.
- `.psydat` and `.log` only if the authors want them, next to the CSVs in
  `data/raw/`.
- The `.psyexp`, conditions files and own stimuli go in `materials/`.
- One dictionary for the whole file set.

## 3. jsPsych (and JATOS, Pavlovia, cognition.run)

**Files.** The data is saved one of these ways:
- with `jsPsych.data.get().csv()` or `.json()`;
- by a server script;
- by JATOS, whose result files are text with one JSON array per component
  or session, often downloaded as `.txt` or inside a zip;
- by Pavlovia or cognition.run, as CSV.

The experiment is HTML + JavaScript, with the jsPsych library, plugins and
stimuli.

**Columns written by jsPsych.**
- `rt`: **milliseconds**, from stimulus onset.
- `trial_type`: the plugin.
- `trial_index`: from 0.
- `time_elapsed`: ms since the start, at the end of the trial.
- `internal_node_id`.
- `stimulus`: often HTML.
- `response`: a key or button for response plugins; a JSON object of answers
  for survey plugins.
- `view_history`: the instructions plugin.
- jsPsych 6 used `key_press` (JavaScript key codes), `button_pressed` and
  `responses` (a JSON string).

**Quirks.**
- One row per trial of every plugin (instructions, fixation, surveys). The
  analysis filters by `trial_type` or by a custom column.
- `null` written as text in the CSV.
- JSON objects inside cells.
- HTML with commas and quotes inside cells.

**What to check.**
- Which rows the analysis keeps.
- That survey answers are unpacked from `response` by a script.
- That the CSV and the JSON (if both exist) hold the same trials.

**Personal data.**
- `PROLIFIC_PID` (and often `subject` when it is set from the URL).
- `STUDY_ID` and `SESSION_ID` link to the Prolific account.
- Free-text survey answers inside `response`.
- Browser details, if the experiment records them.

**Deposit.**
- The raw files go in `data/raw/`, without Prolific IDs. Replace them with
  codes in a script, and keep the key elsewhere.
- A `csv_copies` entry makes the Psych-DS CSV from the JSON.
- The experiment (HTML, JS, own stimuli) goes in `materials/`. It is how
  others can rerun the procedure. The jsPsych library is MIT-licensed: it can
  be included with its license notice.

## 4. Gorilla

**Files.** Downloads have:
- one file per experiment-tree node, named
  `data_exp_<id>-v<version>_task-<key>.csv` or `_questionnaire-<key>.csv`;
- CSV (comma, semicolon or tab separated) or Excel.

Task data is long: one row per event or screen. Questionnaires are long or
short. The short form can have a second header row with the question text.
Classic downloads end with an "END OF FILE" row.

**Columns written by Gorilla.**
- `Event Index`.
- `UTC Timestamp` (ms since 1970), `Local Timezone`.
- `Experiment ID`, `Experiment Version`, `Tree Node Key`, `Repeat Key`,
  `Schedule ID`.
- `Participant Public ID`, `Participant Private ID`.
- Device, OS, browser, monitor and viewport columns.
- `Task Name`, `Trial Number`, `Screen`.
- `Zone Name`/`Zone Type` (Task Builder 1); `Component Name`/`Object Name`
  (Task Builder 2).
- `Response Type` (Questionnaire Builder 2).
- `Response`, `Reaction Time` (ms), `Correct` (1/0), `Timed Out`.
- `Store: <field>`.
- The columns of the task's spreadsheet.

**Quirks.**
- Spaces in column names (R turns them into dots: `Reaction.Time`).
- Many rows per trial: the analysis must filter the response rows, by
  `Zone Type`, `Response Type` or `Component Name`.
- Decimal separators follow the download settings.

**Personal data.**
- `Participant Public ID` is the recruitment ID (e.g. Prolific). It is
  included when the data are downloaded "unblinded". Keep
  `Participant Private ID`, Gorilla's anonymous ID, and drop the Public ID.
- `Participant External Session ID` and `Participant Completion Code` link
  back to the platform.
- Device and browser columns are indirect identifiers: keep them only if they
  are used.

**Deposit.**
- The downloads go in `data/raw/`, Public ID dropped.
- One processed CSV per task in `data/`, produced by the scripts or via
  `csv_copies`.
- In the README, say which node key is which task.
- If the authors published the experiment on Gorilla Open Materials, link
  it.

## 5. OpenSesame (and OSWeb)

**Files.**
- `subject-<nr>.csv`, one per session, written by logger items.
- `quickrun.csv` and `defaultlog.csv` come from test runs: leave them out.
- OSWeb studies run on JATOS write JSON results (see jsPsych for the format).
- The experiment is a `.osexp`: a text script, or a compressed archive with
  the file pool.

**Columns written by OpenSesame.**
- Columns are sorted alphabetically, often more than a hundred.
- `subject_nr`, `subject_parity`.
- `response`, `response_time` (**ms**), `correct` (1/0), `correct_response`
  (the expected response).
- Per item: `response_<item>`, `response_time_<item>`, `correct_<item>`;
  `time_<item>` (ms from the start of the experiment); `count_<item>`
  (from 0).
- Running feedback variables: `acc` (% correct so far), `avg_rt`,
  `total_correct`, `total_responses`.
- `datetime`, `opensesame_version`, display size and backend settings.

**Quirks.**
- `NA` or `None` for missing values.
- Running aggregates (`acc`, `avg_rt`) are not trial measures.
- Rows for practice trials, unless the logger is disabled there.

**Personal data.** `logfile` and `experiment_path` hold absolute paths of the
lab computer, with the user name (e.g. `C:\Users\<name>\...`). Drop them
from the deposit's copies, or blank them in a script.

**Deposit.**
- Logs go in `data/raw/opensesame/`, or in `data/` as
  `study-<name>_subject-<nr>_data.csv`.
- Draft one dictionary for the file set. Describe in full the columns the
  analysis uses. The software settings can share one generic row in `notes`,
  if the authors agree, but every column must still be listed (Psych-DS).
- The `.osexp` goes in `materials/`.

## 6. E-Prime

**Files.**
- `.edat2`/`.edat3`: binary; opens only in E-DataAid. Not open.
- `.emrg2`/`.emrg3`: merged files, same problem.
- `.txt` written during the session: the same data as a UTF-16 text log of
  key-value "LogFrames". It is an open, if awkward, copy.
- Exports from E-DataAid: tab-separated text, often UTF-16. The first line
  can be the path of the `.edat` file.
- The experiment: `.es2`/`.es3` (E-Studio only). The generated `.ebs2`/`.ebs3`
  script is text.

**What the scanner does.** It turns a `.txt` log into a table, as E-DataAid
would:
- rows are the most frequent level, usually trials (`rows_are` names it);
- the values of the enclosing levels (block, session) and of the header
  (Subject, Session, start-up info) are attached to each row;
- an attribute present at two levels gets the level in brackets, as
  E-DataAid writes it: `Procedure[Block]`.

**Columns written by E-Prime.**
- `Subject`, `Session`, `ExperimentName`, `SessionDate`, `SessionTime`,
  `RandomSeed`, `Display.RefreshRate`, `Clock.Information` (XML).
- `Procedure`, `Running`, `<List>.Cycle`, `<List>.Sample`.
- Per object: `.RT` (**ms**), `.ACC` (1/0), `.RESP`, `.CRESP`.
- Clock times (ms, E-Prime's clock): `.OnsetTime`, `.RTTime`, `.OffsetTime`.
- Timing errors (ms): `.OnsetDelay`, `.DurationError`.

**What to check.**
- **No response is RT = 0 and ACC = 0**, not a missing value. Check that the
  scripts exclude these before averaging RTs, and that the dictionary says it.
- `OnsetDelay` and `DurationError` summarise timing accuracy: worth a line in
  the README.

**Personal data.**
- Start-up info in the header (Age, Gender, Handedness) is fine as data, but
  belongs in the dictionary.
- The path in the first line of exports contains the lab computer's user
  name: `csv_copies` and `remove_export_rows` drop it.

**Deposit.**
- `.edat3` (if the authors want it) and the `.txt` logs go in `data/raw/`.
- Open CSVs go in `data/`, via `csv_copies` from the logs or from the
  E-DataAid export.
- The experiment (`.es3`, plus the `.ebs3` text script) goes in `materials/`.
  Say in the README that it opens only with E-Prime.

## 7. Other programs

Inquisit (`.iqdat`, tab-separated text), lab.js, LimeSurvey, PsyToolkit,
Psychtoolbox (`.mat`), SPSS and Excel files are not recognised by name. The
general checks apply as they are:
- delimited text in any encoding;
- label rows and footers;
- lists and JSON in cells;
- personal-data patterns;
- `.mat` and `.sav` without an open copy.

For a `.mat`, ask how the data were produced. An open copy needs MATLAB or
Python (`scipy.io.loadmat`): propose it, do not install anything.
