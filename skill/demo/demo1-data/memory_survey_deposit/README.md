# Autobiographical memory questionnaire (MAQ-10): online survey data

Authors: TODO (names and ORCID)
Contact: TODO

## About the data

Responses of 60 adults to the MAQ-10, a 10-item questionnaire on
autobiographical memory, administered online with Qualtrics between 1 and 28
April 2025. TODO: research question, how participants were recruited, consent.

Each row is one response (one person). Items are answered on a 1–5 scale
(1 = not at all, 5 = very much); items Q3, Q6 and Q9 are reverse-coded. The
total score is the sum of the ten items after reversing Q3, Q6 and Q9
(6 − value).

## Contents

```
README.md                                   this file
LICENSE                                     licenses (see below)
dataset_description.json                    Psych-DS metadata, with the description of every column
data/study-memorysurvey_data.csv            the responses, one row per respondent
dictionaries/study-memorysurvey_dictionary.csv   one row per column of the data file
```

## How to read the data

`data/study-memorysurvey_data.csv` is a comma-separated text file in UTF-8,
with one header row. It opens in any spreadsheet program, in R
(`read.csv()`) or in Python (`pandas.read_csv()`). An empty cell is a
missing value.

Every column is described in `dictionaries/study-memorysurvey_dictionary.csv`
(meaning, type, unit, allowed values, coding, missing values, source) and,
in machine-readable form, in `dataset_description.json` (Psych-DS format).

Respondents were not excluded. Two respondents failed the attention check
(`attention_check` different from 3) and one completed the questionnaire in
61 seconds (`duration_s`; median 579 s): reusers can apply their own exclusion
criteria.

## Changes from the original export

The file comes from the Qualtrics export. Before depositing:

- the columns `IPAddress`, `LocationLatitude`, `LocationLongitude` and
  `RecipientEmail` were removed, because they identify the respondents;
- one response exported twice was removed (61 → 60 rows);
- `Età` was renamed `age` and `Duration (in seconds)` `duration_s`;
- in `age`, "25 anni" and "venticinque" were set to 25, and −99 to missing;
- in `Genere`, two "donna" were set to "Donna";
- one Q4 = 6 and one Q8 = 0, outside the 1–5 scale, were set to missing.

## License

- Data (`data/`, `dictionaries/`, `dataset_description.json`): CC0 1.0 Universal (CC0-1.0)
- This README and the MAQ-10 questionnaire: Creative Commons Attribution 4.0 International (CC BY 4.0)

Full texts in `LICENSE`.

## How to cite

TODO: Authors (2025). Autobiographical memory questionnaire (MAQ-10): online
survey data (Version 1.0) [Data set]. Zenodo. https://doi.org/TODO

## Related materials

Article: TODO (DOI). Preregistration: TODO.
