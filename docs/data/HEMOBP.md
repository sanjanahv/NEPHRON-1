# HEMOBP source record

## Identity

- Dataset: **HEMOBP**, version 3
- DOI: `10.6084/m9.figshare.6260654.v3`
- Publisher record: <https://figshare.com/articles/dataset/Hemrec_VIP_csv/6260654/3>
- Licence: CC BY 4.0
- Published release date: 14 May 2019
- Citation: chien, chih yi (2018). HEMOBP. figshare. Dataset.

## Contents

| File | Purpose | Bytes | MD5 |
|---|---|---:|---|
| `idp.csv` | De-identified patient demographics | 35,151 | `31d269f59bf4acc719f392ad9164d08a` |
| `d1.csv` | Session-level weights, times, dry weight, and temperature | 11,130,894 | `7db3b48bae2c73e3ecd731dbcd452233` |
| `vip.csv` | Longitudinal BP and dialysis-machine observations | 262,851,369 | `ff1589610cf7aa3b3e01ba979b6bdc44` |

The associated Scientific Data paper reports 1,075 adult outpatients, 165,986 sessions,
and 4,366,298 machine/BP records collected between June 2013 and July 2018. The data are
de-identified. BP was generally recorded at 30-minute intervals and additionally when clinically
necessary, so observation timing is irregular and potentially informative.

The released `idp.csv` contains 1,072 patient rows. The pipeline reports release-file counts and
paper-reported counts separately rather than silently forcing them to agree.

## Important modeling limitations

- This is a single-centre Taiwanese cohort, not an Indian deployment cohort.
- Observation density can increase after symptoms or setting changes, creating informative sampling.
- Monthly laboratory data are not included.
- Symptoms and nursing interventions needed for the full KDOQI definition are not available in the
  published three-table schema.
- A model trained from these data must use a measurable proxy label and state that limitation.
- Random row splitting is forbidden because it would leak patient and session information.

## Reproduction

```powershell
.venv\Scripts\python.exe scripts\data\download_hemobp.py
.venv\Scripts\python.exe -m scripts.data.prepare_hemobp
```

The downloader verifies declared size and MD5 before atomically accepting each raw file. Raw files
remain excluded from version control.
