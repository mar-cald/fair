# FAIR check — memory_survey

The folder contains **data only**:
- a questionnaire exported from Qualtrics, as Excel (`Dati questionario finale.xlsx`) and as CSV
  (`dati_questionario.csv`);
- a codebook in Word.

There is no code and no manuscript, so the checks done are: data, structure,
formats, README, data dictionary, license, personal data. **As it is, the folder
cannot be shared:** both data files contain the respondents' IP addresses,
GPS coordinates and e-mail addresses. Even with those removed, a stranger
would not know what the study is, what a row is, or which answers are valid.

## Summary
| Area | Status | In one line |
|:--|:--:|:--|
| Data files and consistency | ❌ | Age written as text, out-of-scale answers, a duplicated response, `Donna`/`donna` |
| Folder structure and names | ⚠️ | Three files in the root, no folders; spaces and "finale" in the Excel name |
| Formats | ⚠️ | The CSV exists, but it has fewer columns than the Excel export; the codebook is a `.docx` |
| README | ❌ | None |
| Data dictionary | ❌ | Only a 6-line Word codebook; 8 of 18 columns not described |
| License | ❌ | None: all rights reserved, nobody can reuse the data |
| Personal data and third-party material | ❌ | IP address, latitude/longitude, e-mail in both files |

## 1. Data files and consistency

**`dati_questionario.csv`** (61 rows; semicolon-separated, decimal comma)
- **Duplicated response:** 61 rows but 60 distinct `ResponseId`s. One response is
  exported twice (an exact duplicate row).
- **`Età` is text:** three values are not numbers: `25 anni`, `venticinque`
  and `-99`. Software reads the whole column as text; −99 is probably a
  missing-value code.
- **`Genere`:** `Donna` and `donna` (2 rows) would be counted as two categories.
- **Values outside the 1–5 scale:** the codebook says items Q1–Q10 go from 1 to
  5, but one Q4 is 6 and one Q8 is 0.
- **`attention_check`:** 2 respondents answered 1, while the codebook says the
  correct answer is 3. Nothing says whether they were excluded.

**`Dati questionario finale.xlsx`** (the Qualtrics export, 61 rows)
- **Extra columns:** it has `StartDate` and `Duration (in seconds)`, which the CSV
  dropped. One response took 61 seconds for a 10-item questionnaire plus
  demographics, while the median is 579 s. Without `Duration` a reuser cannot
  see this.

## 2. Folder structure and names → [rules](https://mar-cald.github.io/fair/struttura-1.html#struttura)
- **No folders:** three files sit in the root. The original export and the open
  version are not kept apart.
- **`Dati questionario finale.xlsx`** has spaces and "finale" in the name.
- **Column names** `Età` (accented letter) and `Duration (in seconds)` (spaces
  and parentheses) break in many programs.

## 3. Formats → [rules](https://mar-cald.github.io/fair/struttura-1.html#in-che-formato-salvarli)
- **The CSV is not a full copy of the Excel export:** two columns are missing,
  so the Excel file can't simply be dropped.
- **The codebook is a `.docx`:** it can't be read by software, and opening it
  needs Word or a compatible program.

## 4. README → [rules](https://mar-cald.github.io/fair/struttura-1.html#readme)

There is no README. Nothing in the folder says:
- who collected the data, when, where and with which sample;
- what the MAQ-10 measures;
- what one row is (one respondent);
- how to cite the data, or under which license.

## 5. Data dictionary → [rules](https://mar-cald.github.io/fair/struttura-1.html#data-dictionary)

`codebook.docx` describes Q1–Q10 (1–5 scale; Q3, Q6, Q9 reverse-coded),
`Genere` and `attention_check`. Missing:
- `ResponseId`, `Età`, `StartDate` and `Duration` are not described;
- there are no labels for the single items;
- nothing says how missing values are written.

## 6. License → [rules](https://mar-cald.github.io/fair/licenze.html)

There is no license. Recommended:
- **CC0 1.0** for the data and the dictionary;
- **CC BY 4.0** for the README and the questionnaire. This applies only if
  the MAQ-10 was written by the authors; check whether it is a published
  instrument.

## 7. Personal data and third-party material → [checklist](https://mar-cald.github.io/fair/risorse.html#checklist-prima-di-depositare)
- **Identifying columns:** `IPAddress`, `LocationLatitude`, `LocationLongitude`
  (4 decimals, about 10 m) and `RecipientEmail`, in both files. Qualtrics adds
  them by default. They must be removed from anything deposited.
- **The Excel export cannot go into the deposit as it is**, not even in
  `data/raw/`.

## What to fix first
1. **Remove the four identifying columns** from the data to deposit.
2. **Deposit the full export as CSV** (with `StartDate` and `Duration`), not the
   reduced CSV, and keep the original Excel file out of the deposit.
3. **Correct or document:**
   - the duplicated response;
   - `Età` (text and −99);
   - `donna` → `Donna`;
   - Q4 = 6 and Q8 = 0;
   - say how the attention-check failures and the 61-second response should
     be treated.
4. **Write a data dictionary in CSV** for all columns, from the codebook.
5. **Write a README and add the licenses.**

## The deposit version

The deposit (`memory_survey_deposit/`) will contain:
- `data/` with one Psych-DS file, `study-memorysurvey_data.csv`;
- its dictionary in `dictionaries/`;
- `dataset_description.json`, README, LICENSE (CC0 + CC BY 4.0), and the zip.

Decisions needed from you:
- **Identifying columns:** remove all four?
- **Data corrections:** which to apply (point 3)?
- **Column names:** rename `Età` → `age` and `Duration (in seconds)` →
  `duration_s`?
- **The MAQ-10:** is it your own questionnaire?
- **Authors, ORCID, dates of collection.**
