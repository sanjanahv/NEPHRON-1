# NADI-HD

**Test tomorrow's dialysis, today.**

NADI-HD is a patient-specific hemodialysis rehearsal system that forecasts intradialytic
instability, models clearance and fluid removal, and compares constrained counterfactual
prescriptions before a session.

## What is working

- Interactive Session Cockpit in `dist/`
- Deterministic hemodynamic and urea-clearance twin
- IDH warning horizon and interpretable risk factors
- URR and single-pool Kt/V estimates
- Constrained Parallel Futures engine
- Deterministic synthetic dialysis cohort generator
- Reproducible HEMOBP v3 data pipeline with patient-disjoint splits
- Calibrated LightGBM pre-session IDH screening model and frozen test report
- History-calibrated patient twin with confidence and audit trace
- Measured-vs-modeled anemia, mineral-bone, and cardiovascular burden mapping
- Persistent nurse/nephrologist and light/dark interface modes
- Bounded hybrid risk fusion with explicit model disagreement
- Persistent completed-session memory and prediction-error comparison
- Conservative and unavailable modes for damaged machine streams
- Versioned FastAPI endpoints
- Physics, risk, data, training, counterfactual, and API tests

## Stack

- **Interface:** accessible HTML/CSS/JavaScript clinical cockpit
- **API:** Python 3.11+, FastAPI, Pydantic
- **Modeling:** transparent physiology core plus calibrated LightGBM/scikit-learn risk layer
- **Data:** deterministic synthetic fixtures and licensed, re-pseudonymized open research data
- **Quality:** pytest, Ruff, patient-level validation design
- **Deployment:** Docker Compose or static web + API services

## Development

```powershell
$env:PYTHONPATH = "."
uv sync --extra dev --extra ml
uv run uvicorn apps.api.nephron.main:app --reload
```

In a second terminal:

```powershell
node scripts/preview.mjs
```

Open `http://127.0.0.1:4173`. API documentation is available at `http://127.0.0.1:8000/docs`.

Generate a deterministic synthetic cohort:

```powershell
uv run python -m apps.api.nephron.synthetic
```

Run quality checks:

```powershell
uv run ruff check apps tests
uv run pytest
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data strategy](docs/DATA.md)
- [Roadmap](docs/ROADMAP.md)
- [Product and usability principles](docs/PRODUCT_PRINCIPLES.md)
- [Originality and provenance](docs/ORIGINALITY_AND_PROVENANCE.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)
- [Current model card](reports/MODEL_CARD.md)
- [Temporal warning model card](reports/TEMPORAL_MODEL_CARD.md)
- [Architecture diagram](docs/ARCHITECTURE_DIAGRAM.md)
- [20-minute demonstration](docs/DEMO_SCRIPT.md)
- [Usability validation protocol](docs/USABILITY_PROTOCOL.md)

## Safety status

This is a proof of concept. The interface uses demonstration data; research-model development uses the
licensed HEMOBP dataset with the limitations recorded in the model card. It is not a medical device and
must not be used for patient care, diagnosis, or treatment.
