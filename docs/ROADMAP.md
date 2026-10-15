# Build roadmap and completion gates

No chunk is considered complete because a screen exists. Every chunk has an explicit evidence gate.

## Chunk 1 — clinical contract and executable foundation

Status: **engineering complete; clinical review pending**

- [x] Define one primary outcome: intradialytic hypotension
- [x] Define intended users: nephrologist and dialysis nurse
- [x] Separate prediction, simulation, and clinician decision
- [x] Define synthetic/open/anonymized data boundary
- [x] Implement deterministic dialysis and hemodynamic engine
- [x] Implement URR, Kt/V, fluid, and IDH outputs
- [x] Implement counterfactual safety and adequacy constraints
- [x] Implement versioned API contract and automated tests
- [x] Connect the cockpit to live API responses with an offline fallback
- [ ] Review definitions, equations, and operational constraints with a renal clinician

**Exit gate:** contracts are stable, invalid inputs fail safely, all automated tests pass, and a
renal clinician has reviewed the assumptions. Until the final item is complete, outputs remain
explicitly marked as prototype simulations.

## Chunk 2 — evidence-grade data pipeline

- [x] Acquire HEMOBP and record source, license, schema, and checksum
- [x] Create a data dictionary with units and missingness rules
- [x] Normalize static EHR and dynamic machine streams into session-level features
- [x] Build patient-level train/validation/test partitions
- [x] Add leakage, range, unit, and identifier checks
- [x] Create reproducible source, quality, split, and validation reports

**Exit gate:** one command rebuilds immutable patient-level splits; leakage and schema tests pass;
every field has provenance, unit, and missing-data behavior.

## Chunk 3 — calibrated forecasting model

- [x] Implement reproducible logistic-regression and LightGBM training pipelines
- [x] Implement sigmoid calibration on a held-out validation partition
- [x] Implement AUROC, AUPRC, sensitivity, specificity, Brier score, and false-alert metrics
- [x] Measure warning lead time and session-level alert burden at a validation-selected threshold
- [x] Evaluate a temporal model and keep it out of clinical alerts after it failed the alert-budget gate
- [x] Add bounded hybrid fusion with disagreement-aware uncertainty and capped learned-model weight
- [x] Export a reproducible model artifact, model card, and frozen evaluation report
- [x] Serve versioned model status and clinician-review prediction endpoints

**Exit gate:** performance is measured on an untouched patient-level test partition, probabilities
are calibrated, failure subgroups are documented, and the UI never displays invented metrics.

## Chunk 4 — patient-specific twin and Parallel Futures

- [x] Estimate patient vulnerability parameters from prior completed sessions
- [x] Record calibration confidence, shrinkage weight, completeness, and source-session count
- [x] Generate constrained alternative prescriptions
- [x] Reject inadequate or operationally invalid futures
- [x] Report uncertainty and expose safe-degradation behavior
- [x] Validate core monotonic and physiological invariants with automated tests

**Exit gate:** every future is reproducible, traceable, constraint-checked, and accompanied by
uncertainty; no path can autonomously alter a dialysis machine.

## Chunk 5 — calm role-based clinical experience

- [x] Research dialysis workflow and established safety-focused interface patterns
- [x] Define separate nephrologist and nurse information priorities
- [x] Add an initial role-based progressive-disclosure mode
- [x] Make the modeled status, review action, and evidence path explicit
- [x] Add light and dark themes with persistent preference
- [x] Add automated contrast, control-label, keyboard-entry, offline-asset, and responsive rules
- [ ] Conduct task-based usability reviews with representative users

**Exit gate:** a new user can identify patient state, urgency, next action, and supporting evidence
without instruction. Advanced data remains available without occupying the primary view.

## Chunk 6 — multisystem and session memory

- [x] Add measured-vs-modeled labels to multisystem longitudinal signals
- [x] Add anemia and CKD-mineral-bone trend models
- [x] Add cardiovascular burden without overstating causality or inferring LVH
- [x] Recalculate patient calibration inputs after each completed synthetic session
- [x] Expose longitudinal prediction-versus-observation session comparisons

**Exit gate:** all displayed trends have provenance and uncertainty, and secondary models never
compete visually with the primary IDH decision.

## Chunk 7 — safety, reliability, and jury delivery

- [x] Exercise missing, delayed, implausible, and contradictory streams
- [x] Add request traces, decision traces, artifact hashes, and model/data provenance
- [x] Provide a reproducible offline demo fixture and deterministic fallback
- [ ] Complete visual browser and representative-user accessibility checks
- [x] Finalize architecture diagram, README, model/data cards, and 20-minute demonstration script
- [ ] Export and visually validate the jury deck when the presentation runtime is available
- [x] Establish originality, provenance, and third-party attribution policy
- [x] Complete the preliminary originality search and direct-dependency licence audit

**Exit gate:** the core demo works end to end without network access, failures are graceful, claims
match evidence, and every submission artifact is reproducible from the repository.
