# Data strategy

## Prototype data layers

1. **Historical/static:** demographics, comorbidities, dry weight, laboratory values, prior IDH frequency, and prior-session nadir BP.
2. **Dynamic:** blood pressure, blood flow, dialysate flow, ultrafiltration, elapsed time, dialysate temperature, and cumulative fluid removal.
3. **Derived:** mean arterial pressure, plasma-volume change, estimated cardiac output, clearance, URR, Kt/V, IDH horizon, and uncertainty.

## Selected primary public source

- HEMOBP v3 for linked dialysis-machine and blood-pressure time series. See
  [the source record](data/HEMOBP.md) and immutable manifest in
  `configs/data/hemobp.v3.json`.

## Candidate supplementary sources

- Synthea for synthetic longitudinal EHR scaffolding.
- Public CKD cohorts for aggregate distribution checks where permitted.

No external dataset is committed until its license, provenance, patient-level split strategy, and documentation are reviewed.

## Leakage prevention

- Split train/validation/test partitions by patient identifier.
- Keep every session for a patient in one partition.
- Fit preprocessing only on the training partition.
- Report AUROC, AUPRC, sensitivity, false alerts per session, Brier score, and warning lead time.
- Maintain an untouched temporal or external validation cohort.

## Reproducible preparation

```powershell
.venv\Scripts\python.exe scripts\data\download_hemobp.py
.venv\Scripts\python.exe -m scripts.data.prepare_hemobp
.venv\Scripts\python.exe scripts\data\validate_hemobp.py
.venv\Scripts\python.exe -m scripts.data.prepare_temporal_hemobp
.venv\Scripts\python.exe -m scripts.data.validate_temporal_hemobp
```

The prepared data pseudonymize the already de-identified source identifier again and use a stable
patient-level 70/15/15 split. The current measurable target is a BP-only proxy: baseline SBP drop
of at least 20 mmHg with nadir SBP below 90 mmHg. It is not presented as the full symptom-based
clinical definition.

Pre-session models use the earliest recorded BP and machine settings. Session-wide means are
retained for audit and descriptive analysis only; they are excluded from pre-session training
because post-symptom setting changes could leak the outcome.

Historical features are calculated chronologically within each patient and use only sessions that
occurred before the prediction session. The first session for a patient receives missing history,
which is handled explicitly by the model pipeline.

## Temporal warning windows

The temporal builder performs a disk-backed sort of the unsorted machine stream and creates
prediction-time rows strictly before the first qualifying BP-proxy event. A positive row means the
first event is 15–60 minutes ahead. Features use only the current and earlier observations.

Derived temporal files remain ignored by Git. Their validation receipt records SHA-256 hashes,
counts, patient-disjointness, positive-window validation, and a no-post-event assertion.
