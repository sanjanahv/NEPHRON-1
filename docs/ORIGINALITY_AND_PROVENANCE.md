# Originality and provenance

This document records what NADI-HD borrows from public knowledge, what it implements independently,
and how the team avoids accidental plagiarism. It is part of the prototype evidence trail, not a
marketing claim that clinical equations or standard workflows were invented here.

## Original contribution

The following elements are original to this repository unless a file header says otherwise:

- the product framing of a pre-session dialysis rehearsal with constrained "Parallel Futures";
- the separation of measured, calculated, predicted, and simulated information in one clinical flow;
- the patient-twin calibration, uncertainty, adequacy, and operational-safety orchestration;
- the Session Cockpit information architecture, interaction design, visual system, and copy;
- the implementation of the API, deterministic simulator, feature pipeline, model training, tests,
  synthetic fixtures, and decision traces;
- the planned role-specific nurse and nephrologist views and progressive-disclosure behavior.

These combinations are our design and engineering work. Individual clinical concepts—Kt/V, URR,
intradialytic hypotension, ultrafiltration, blood-pressure trends, and CKD complications—are established
medical knowledge and are not presented as novel inventions.

## Research boundary

Research is used to understand clinical workflows, accepted equations, safety constraints, validation
practice, and interaction patterns. It may influence a requirement or design principle, but it is not a
source of screens, brand language, code, model artifacts, or feature names to reproduce.

For every external reference we use, we apply this rule:

1. Extract the underlying need or evidence.
2. Record the source and licence where applicable.
3. Design an implementation for NADI-HD from first principles.
4. Use our own structure, wording, visuals, code, and tests.
5. Reject any element whose provenance or reuse permission is unclear.

Competitive products and prior hackathon projects may be reviewed only for category-level gaps such as
poor alert prioritization or unclear uncertainty. Their distinctive layouts, claims, names, assets,
workflows, and implementations are not copied.

## Evidence and public inputs

| Input | How it is used | Ownership / licence | Repository evidence |
| --- | --- | --- | --- |
| HEMOBP v3 | Development of a pre-session IDH screening model and reproducible validation pipeline | Dataset authors; CC BY 4.0 | `docs/data/HEMOBP.md`, `configs/data/hemobp.v3.json` |
| Published dialysis equations | Independently coded, testable prototype calculations for clearance and adequacy | Public clinical/scientific knowledge; publications must be cited in technical claims | `apps/api/nephron/physics.py`, `tests/test_physics.py` |
| General clinical UI research | Principles such as prioritization, progressive disclosure, accessibility, and explicit uncertainty | Inspiration only; no third-party visual assets or screen reproduction | `docs/PRODUCT_PRINCIPLES.md` |
| Open-source Python packages | Runtime, modeling, validation, and testing infrastructure | Respective package licences | `pyproject.toml`, `uv.lock` |

## Data and model provenance

- Raw HEMOBP data is downloaded from its recorded DOI and verified using the publisher-supplied file
  sizes and MD5 values.
- Raw and processed clinical data is ignored by Git. Only schemas, manifests, code, aggregate reports,
  and documentation belong in the repository.
- Patient identifiers are re-pseudonymized before derived datasets are written.
- Partitions are patient-disjoint. Features are restricted to information available at prediction time.
- The current IDH target is a blood-pressure-only proxy, not the complete symptomatic clinical
  definition. This limitation must remain visible in the model card and product language.
- The model artifact is produced by repository code; no third-party trained weights are included.

## Design provenance rules

- Do not import screenshots, icons, illustrations, fonts, logos, or copy without a compatible licence
  and an entry in `THIRD_PARTY_NOTICES.md`.
- Do not trace or closely reproduce another product's screen or interaction sequence.
- Use standard clinical conventions only where they improve safety or comprehension; document the
  rationale rather than claiming novelty.
- Keep dated sketches, decision notes, model reports, and commits so the evolution of the work can be
  demonstrated.
- Any generated asset must be reviewed, substantially directed by the team, licensed for the intended
  use, and recorded before inclusion.

## Pre-submission originality review

- [ ] Every externally sourced factual claim has a citation.
- [ ] Every dataset, font, icon set, package, and media asset has a recorded licence.
- [ ] No copied screenshots, diagrams, prose, prompts, code, or trained weights are present.
- [ ] Product names and feature labels were checked for confusing similarity.
- [ ] The team can explain each architecture, modeling, and interface decision in its own words.
- [ ] Claims in the demo match the frozen evaluation report and model card.
- [ ] A clean checkout can reproduce tests, reports, and the offline demo.

## Change policy

Update this file and `THIRD_PARTY_NOTICES.md` whenever a new external dataset, equation source, asset,
model, or substantial design reference enters the project. If provenance cannot be established, remove
the material before submission.

## Naming record

The working name `NEPHRON-1` was retired on 15 October 2026 after an exact-name search found an active
wearable-hemodialysis venture using `Nephron 1`. The independently selected name `NADI-HD` combines
*nadi* (pulse/flow) with the standard abbreviation for hemodialysis. Exact searches for `NADI-HD` in
dialysis and healthcare did not identify a competing product at the time of selection. This is a
preliminary collision check, not a legal trademark clearance.
