# NADI-HD temporal IDH warning model

## Decision

**Research baseline only — disruptive clinical alarms are disabled.** The frozen patient-level test
result does not meet the prototype's alert-burden gate.

## Protocol

- Source: HEMOBP v3 (`10.6084/m9.figshare.6260654.v3`)
- Target: first qualifying BP-proxy event 15–60 minutes ahead
- Leakage control: features stop strictly before the first qualifying event
- Selected model: `temporal-lightgbm`
- Threshold: 0.008131, selected using validation sessions only

## Untouched patient-level test performance

| Metric | Value |
|---|---:|
| Event sessions | 1,136 |
| Non-event sessions | 19,239 |
| Row AUROC | 0.913 |
| Row AUPRC | 0.110 |
| Row Brier score | 0.007 |
| Session sensitivity | 0.749 |
| Median timely warning | 48.0 min |
| False-alert sessions / 100 | 46.84 |
| Premature-alert event sessions | 844 |
| Late-alert event sessions | 477 |

Validation sensitivity was 0.801; test sensitivity fell to
0.749. The false-alert burden increased from
38.84 to 46.84 per
100 sessions. This result is not suitable for a nurse-facing alarm.

## Limitations

- BP-only proxy outcome; symptoms and interventions are unavailable.
- Observation timing is irregular and may reflect clinical concern.
- Single-centre Taiwanese retrospective cohort; external transportability is unknown.
- Repeated within-session measurements are correlated.
- Prospective workflow and alarm-fatigue evaluation is required.
