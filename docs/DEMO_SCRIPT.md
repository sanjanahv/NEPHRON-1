# NADI-HD 20-minute demonstration

## 0:00–2:00 — the clinical decision

Open the Session Cockpit in nurse view. State the single question: *Can this planned prescription
reach adequacy without creating an avoidable hemodynamic burden for this patient?* Identify the
synthetic patient and the research-only status before discussing results.

## 2:00–5:00 — patient-specific rehearsal

Show the predicted BP trajectory, uncertainty band, modeled Kt/V and URR, and the current fluid-removal
burden. Explain which values are measured, calculated, predicted, and simulated. Do not present the
temporal research model as a clinical alarm.

## 5:00–9:00 — Parallel Futures

Change duration and ultrafiltration rate, run the deterministic alternatives, and compare risk delta,
adequacy delta, nadir, and uncertainty. Open the decision trace. Emphasize that infeasible candidates
are rejected and no machine setting is written.

## 9:00–12:00 — session memory

Record one completed synthetic session through the API, then show its predicted-versus-observed error
and updated calibration inputs. Explain sparse-history shrinkage and why confidence depends on the
number of prior completed sessions.

## 12:00–15:00 — multisystem horizon

Open the multisystem map. Demonstrate hemoglobin and calcium-phosphate trends. Show that cardiovascular
load is labeled modeled and that LV mass is displayed only when measured by echocardiography.

## 15:00–17:00 — failure behavior

Trigger the delayed-stream control. Explain widened uncertainty and conservative mode. Use the stream
assessment endpoint to demonstrate missing BP, contradictory BP, and excess-UF handling.

## 17:00–19:00 — evidence

Open validation. Present the frozen pre-session model result and the temporal model's negative alarm
gate. Lead with the 48-minute median warning, then immediately state 74.9% sensitivity and 46.84 false
alert sessions per 100; explain why alarms remain disabled.

## 19:00–20:00 — close

Return to the selected feasible future. Summarize: NADI-HD rehearses, constrains, explains, remembers,
and fails safely. It supports clinician review; it does not diagnose, prescribe autonomously, or control
a dialysis machine.

## Offline recovery

If the API is unavailable, reload the interface. It consumes `dist/demo-fixture.json`, generated from
the same domain code by `python -m scripts.export_demo`. Continue the deterministic demonstration and
state that model prediction endpoints are offline.
