# NADI-HD pre-session IDH proxy model

## Intended use

Research prototype for clinician-reviewed pre-session risk stratification. It is not a medical
device, must not control a dialysis machine, and must not be used for patient care.

## Source and target

- Source: HEMOBP v3 (`10.6084/m9.figshare.6260654.v3`)
- Target: baseline SBP drop >=20 mmHg and nadir SBP <90 mmHg
- Limitation: BP-only proxy; symptoms and interventions unavailable
- Selected model: `lightgbm`
- Calibration: sigmoid on the patient-disjoint validation partition

## Untouched patient-level test performance

| Metric | Value |
|---|---:|
| Sessions | 20,484 |
| Prevalence | 0.061 |
| AUROC | 0.862 |
| AUPRC | 0.329 |
| Brier score | 0.048 |
| Sensitivity | 0.831 |
| Specificity | 0.739 |
| Precision | 0.171 |
| False alerts / 100 sessions | 24.54 |

The decision threshold (0.0588) was selected using validation data only.

## Known limitations

- Single-centre Taiwanese retrospective cohort; transportability to India is unproven.
- Symptoms and nursing interventions are unavailable, so the outcome is a BP-only proxy.
- Observation timing is irregular and can be influenced by clinical concern.
- The model requires prospective, multicentre, subgroup and workflow validation.
- Performance must not be transcribed into the UI without matching model/data versions.
