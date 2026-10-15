# NADI-HD task-based usability protocol

This protocol is ready for representative dialysis nurses and nephrologists. It does not claim that
human validation has occurred.

## Participants

- At least three dialysis nurses with recent in-centre hemodialysis experience.
- At least two nephrologists who review or prescribe hemodialysis treatments.
- No real patient information; use the deterministic synthetic fixture only.

## Core tasks

1. Identify the patient, session status, modeled urgency, and next review action without instruction.
2. Determine whether the planned prescription meets the displayed adequacy constraint.
3. Compare baseline with one feasible Parallel Future and explain the risk/adequacy trade-off.
4. Find the evidence and uncertainty behind the selected future.
5. Respond to a delayed BP stream and state which outputs remain trustworthy.
6. Distinguish measured, calculated, predicted, and simulated multisystem signals.

## Measures

- Task completion and critical-error rate.
- Time to identify urgency and next action.
- Single Ease Question after each task.
- Misinterpretation of probability, uncertainty, or simulated alternatives.
- Preference and information-load comments by clinical role.

## Stop conditions

Stop a task if the participant interprets NADI-HD as autonomous machine control, treats a simulated
alternative as a prescription, or believes the temporal research baseline is a validated alarm. Treat
each occurrence as a critical design defect.

## Acceptance gate

- 100% identify the research-only and clinician-review boundary.
- At least 90% complete the primary session task without assistance.
- No participant believes NADI-HD changed machine settings.
- Median urgency-identification time under 20 seconds.
- All critical interpretation defects resolved and re-tested.
