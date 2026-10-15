# Product principles

## Calm before comprehensive

The primary screen is not a monitoring wall. It answers four questions in order:

1. Is the patient currently stable?
2. What is likely to happen, and when?
3. What requires clinician attention?
4. What evidence supports that conclusion?

Everything else uses progressive disclosure.

## Role-aware, not role-exclusive

### Dialysis nurse

- Current session state and data quality
- Immediate risk horizon
- Observable contributing signals
- Escalation cue and clinician-approved plan
- Minimal interaction during active care

### Nephrologist

- Forecast confidence and historical calibration
- Prescription comparison and adequacy trade-offs
- Counterfactual evidence
- Longitudinal patterns and model limitations
- Explicit approval or rejection of a proposed plan

## Accuracy presentation

- Never display fabricated validation numbers.
- Distinguish measured, calculated, predicted, and simulated values visually and in text.
- Show uncertainty near the affected result, not in a remote disclaimer.
- Prefer calibrated absolute probability plus warning horizon over a vague risk score.
- Surface missingness and distribution shift before presenting a confident result.
- Keep clinical definitions and model versions inspectable.

## Visual direction

- Neutral clinical typography, restrained colour, and generous whitespace.
- Colour communicates state but never carries meaning alone.
- No chat-first interface, robot imagery, glassmorphism, decorative anatomy, or unexplained gauges.
- Light and dark themes are first-class and must preserve hierarchy and contrast.
- Dense analysis belongs in an evidence view, not the nurse's primary workflow.

## Safety language

Use “forecast,” “simulation,” “candidate,” and “requires review.” Avoid “diagnosis,” “guaranteed,”
“optimal treatment,” or language implying autonomous prescription.
