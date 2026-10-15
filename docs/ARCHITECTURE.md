# NADI-HD architecture

## Clinical contract

NADI-HD is a clinician-facing simulation and decision-support prototype. It forecasts
intradialytic hypotension, models small-solute clearance, and compares constrained alternative
prescriptions. It never writes settings to a dialysis machine.

## Data flow

```text
Synthetic EHR / historical sessions       Dialysis-machine time series
                  \                         /
                   Data quality + normalization
                                |
                       Patient twin calibration
                       /                      \
        Deterministic physiology          Learned risk residual
        - fluid balance                   - IDH probability
        - urea kinetics                   - warning horizon
        - hemodynamic response            - calibration
                       \                      /
                        Hybrid session forecast
                                  |
                   Constrained counterfactual search
                    /          |             \
              reject       rank frontier     explain
                                  |
                       Clinician review UI
```

## Safety boundaries

- Synthetic/open/anonymized data only.
- Every output carries prototype limitations.
- Counterfactual candidates must pass adequacy and operational constraints.
- Recommendations require clinician review.
- No autonomous machine control.
- Physics and learned components remain separately testable.
- Every API response carries a bounded trace identifier and explicit research status.
- Model status exposes an artifact hash without leaking host filesystem paths.

## Current implementation

- `apps/api/nephron/physics.py`: transparent deterministic twin.
- `apps/api/nephron/risk.py`: interpretable risk layer and explanation rules.
- `apps/api/nephron/counterfactual.py`: candidate generation and safety gates.
- `apps/api/nephron/twin.py`: chronology-safe patient-history calibration and confidence trace.
- `apps/api/nephron/multisystem.py`: measured and modeled longitudinal complication signals.
- `apps/api/nephron/hybrid.py`: bounded physiology/model fusion with disagreement uncertainty.
- `apps/api/nephron/memory.py`: idempotent completed-session memory and recalibration inputs.
- `apps/api/nephron/quality.py`: explicit degraded-operation and output-shutdown rules.
- `apps/api/nephron/ml/temporal.py`: leakage-resistant warning windows and alert-budget evaluation.
- `apps/api/nephron/ml/temporal_training.py`: calibrated temporal baselines and frozen evaluation.
- `apps/api/nephron/synthetic.py`: deterministic synthetic training cohort.
- `apps/api/nephron/main.py`: versioned FastAPI contract.
- `dist/`: interactive clinician cockpit.
