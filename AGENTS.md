# NADI-HD agent starting point

**Read this file before changing the repository.** It is the operational handoff for every
developer or coding agent. Begin by reading `README.md`, `docs/ARCHITECTURE.md`, and
`docs/ROADMAP.md`; then inspect the implementation and tests related to the task. Do not infer
clinical validity from a working user interface.

## Mission

NADI-HD is a patient-specific hemodialysis rehearsal prototype. It combines a transparent
physiology model with a bounded learned-risk layer to forecast intradialytic hypotension (IDH),
estimate dialysis adequacy, and compare constraint-checked prescription scenarios before a
session. It is clinician-facing research software—not a medical device—and must never control a
dialysis machine or present a simulated result as clinical fact.

## Current state

The end-to-end prototype, offline demo, API, deterministic twin, calibrated pre-session model,
patient-history calibration, multisystem view, and automated test suite are implemented. The most
important unfinished work is **external validation**, not adding more dashboard tiles.

Before starting, run:

```powershell
$env:PYTHONPATH = "."
uv sync --extra dev --extra ml
uv run ruff check apps tests
uv run pytest
node --check dist/app.js
```

If dependencies are already installed, skip `uv sync`. Keep the application usable without a
network connection and preserve the deterministic offline fixture.

## Work next, in this order

### P0 — establish defensible clinical validity

1. Arrange renal-clinician review of the equations, feature definitions, units, constraints, and
   IDH label. Record every decision and resulting code change in versioned documentation.
2. Run the task-based nurse/nephrologist study in `docs/USABILITY_PROTOCOL.md`. Convert observed
   errors—not preferences alone—into prioritized interface changes.
3. Validate on a second, legally usable patient-level dataset from a different centre. Freeze the
   current model first; report calibration, discrimination, warning lead time, false-alert burden,
   missingness, and subgroup results without tuning on the final test set.
4. Add explicit unit and terminology tests against the clinician-approved data dictionary.

### P1 — make the twin scientifically stronger

1. Add uncertainty intervals to clearance, blood-pressure trajectory, and counterfactual outcomes;
   separate parameter uncertainty from stream-quality uncertainty.
2. Fit patient parameters only from chronologically prior sessions, compare against population
   priors, and add calibration-ablation tests proving whether personalization helps.
3. Upgrade urea kinetics from the current transparent approximation to a reviewed two-compartment
   model, including rebound, residual kidney function, access recirculation, and time-varying
   ultrafiltration where supported by data.
4. Treat cardiovascular, anemia, and mineral-bone outputs as longitudinal context. Do not infer
   LVH or causal organ damage from proxy values. Add real measured outcomes before strengthening
   those claims.
5. Add sensitivity and identifiability analysis so poorly constrained parameters are visibly
   down-weighted rather than displayed with false precision.

### P1 — improve safety and reliability

1. Add contract tests for missing, delayed, duplicated, out-of-order, unit-mismatched, and
   physiologically impossible streams.
2. Introduce a prospective silent/shadow mode: predictions are logged for evaluation but never
   shown as treatment recommendations.
3. Version every model, equation set, constraint set, dataset schema, and threshold in the audit
   record. Make replays bit-for-bit reproducible where practical.
4. Add authentication, role-based authorization, encrypted persistence, retention rules, and a
   threat model before handling any real health data. Never commit secrets or patient-level data.
5. Add CI for linting, tests, dependency/license checks, secret scanning, and offline-demo smoke
   tests on every pull request.

### P2 — refine the clinical experience

1. Keep the primary screen calm: patient identity/status, current risk, reason, next review action,
   and data confidence. Put detailed curves and multisystem context behind progressive disclosure.
2. Make nurse and nephrologist modes task-specific rather than cosmetic. Validate both with timed
   scenarios and comprehension/error measures.
3. Add an accessible comparison view for at most three candidate futures, emphasizing trade-offs,
   rejected constraints, uncertainty, and what changed from the baseline.
4. Complete keyboard, screen-reader, contrast, zoom, responsive-layout, print, and browser testing.
5. Add a guided jury-demo mode that uses the same product paths and calculations as normal mode;
   never hard-code favorable outcomes solely for presentation.

### P2 — deployment and observability

1. Add production configuration, health/readiness probes, structured logs, metrics, and trace
   correlation without exposing patient information.
2. Separate immutable model artifacts from application images and verify artifacts by checksum at
   startup.
3. Add performance budgets for API latency, simulation runtime, frontend load, and memory use.
4. Document backup, rollback, incident response, model rollback, and degraded/offline operation.

## Non-negotiable engineering rules

- Preserve the boundary between measured values, modeled values, forecasts, and clinician actions.
- Use synthetic, licensed open, or properly governed de-identified data only.
- Split evaluation data by patient and chronology. Never allow future-session or post-outcome
  leakage into features, calibration, thresholds, or patient parameters.
- Keep physics, learned risk, hybrid fusion, and UI explanations separately testable.
- Counterfactuals must pass adequacy and operational constraints and must remain review-only.
- Prefer calibrated, interpretable performance over a more complex model with a better headline
  score. No metric may appear in the UI unless it comes from a reproducible evaluation artifact.
- New clinical claims require evidence, provenance, limitations, and clinician review.
- Avoid visual clutter. A new card or chart needs a named user, decision, and usability rationale.
- Do not commit `.env` files, credentials, raw/processed patient-level data, generated model
  binaries, caches, or private deployment identifiers.
- Preserve API compatibility or version the contract explicitly.

## Repository map

- `apps/api/nephron/physics.py` — deterministic hemodynamic and clearance simulation
- `apps/api/nephron/risk.py` — interpretable risk logic
- `apps/api/nephron/hybrid.py` — bounded physics/ML fusion and disagreement handling
- `apps/api/nephron/counterfactual.py` — candidate futures and constraint gates
- `apps/api/nephron/twin.py` — patient-history calibration
- `apps/api/nephron/multisystem.py` — longitudinal secondary-organ context
- `apps/api/nephron/quality.py` — degraded stream behavior
- `apps/api/nephron/memory.py` — completed-session memory
- `apps/api/nephron/ml/` — training and temporal-model evaluation
- `apps/api/nephron/main.py` — versioned FastAPI surface
- `dist/` — dependency-light clinician cockpit and offline fallback
- `tests/` — executable behavior and safety invariants
- `reports/` — frozen evaluation evidence and model cards
- `docs/` — architecture, data, usability, provenance, and demonstration guidance

## Definition of done for every change

A change is complete only when its user/clinical purpose is stated, safety impact is considered,
tests cover normal and failure behavior, lint and the full test suite pass, documentation and API
examples are updated, no sensitive/generated files are staged, and the offline demonstration still
works. For model changes, also regenerate the evaluation report and model card and compare
calibration and alert burden—not just AUROC.

At handoff, summarize what changed, evidence produced, limitations that remain, exact validation
commands run, and the single highest-value next action. Keep `docs/ROADMAP.md` aligned with proven
status; never mark clinical or usability review complete without recorded external evidence.
