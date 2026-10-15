from __future__ import annotations

from dataclasses import dataclass, replace

from .domain import Forecast, PatientProfile, Prescription
from .risk import forecast_session


@dataclass(frozen=True)
class Candidate:
    candidate_id: str
    prescription: Prescription
    forecast: Forecast
    feasible: bool
    rejection_reasons: tuple[str, ...]
    peak_risk_delta: float = 0.0
    kt_v_delta: float = 0.0
    nadir_sbp_mmhg: float = 0.0
    uncertainty_mmhg: float = 0.0
    on_safety_adequacy_frontier: bool = False
    decision_trace: tuple[str, ...] = ()


def evaluate_candidate(
    candidate_id: str,
    patient: PatientProfile,
    prescription: Prescription,
    minimum_kt_v: float = 1.2,
) -> Candidate:
    forecast = forecast_session(patient, prescription)
    rejection_reasons: list[str] = []
    if forecast.adequacy.sp_kt_v < minimum_kt_v:
        rejection_reasons.append("Predicted Kt/V is below the configured adequacy constraint")
    if prescription.uf_rate_ml_kg_h(patient.pre_weight_kg) > 15:
        rejection_reasons.append("Ultrafiltration rate exceeds the prototype safety boundary")
    if prescription.duration_minutes > 360:
        rejection_reasons.append("Treatment duration exceeds the configured operational boundary")
    nadir = min(point.sbp_mmhg for point in forecast.points)
    uncertainty = max(
        point.confidence_high_sbp - point.confidence_low_sbp for point in forecast.points
    )
    return Candidate(
        candidate_id=candidate_id,
        prescription=prescription,
        forecast=forecast,
        feasible=not rejection_reasons,
        rejection_reasons=tuple(rejection_reasons),
        nadir_sbp_mmhg=nadir,
        uncertainty_mmhg=round(uncertainty, 1),
        decision_trace=(
            f"Simulated {len(forecast.points)} time points",
            f"Checked Kt/V >= {minimum_kt_v:.2f}",
            "Checked ultrafiltration rate <= 15 mL/kg/h",
            "No machine setting was changed",
        ),
    )


def _with_comparisons(candidates: list[Candidate]) -> list[Candidate]:
    baseline = next(item for item in candidates if item.candidate_id == "baseline")
    compared = [
        replace(
            item,
            peak_risk_delta=round(
                item.forecast.peak_idh_risk - baseline.forecast.peak_idh_risk, 4
            ),
            kt_v_delta=round(
                item.forecast.adequacy.sp_kt_v - baseline.forecast.adequacy.sp_kt_v,
                2,
            ),
        )
        for item in candidates
    ]
    output: list[Candidate] = []
    for candidate in compared:
        dominated = any(
            other.feasible
            and other.candidate_id != candidate.candidate_id
            and other.forecast.peak_idh_risk <= candidate.forecast.peak_idh_risk
            and other.forecast.adequacy.sp_kt_v >= candidate.forecast.adequacy.sp_kt_v
            and (
                other.forecast.peak_idh_risk < candidate.forecast.peak_idh_risk
                or other.forecast.adequacy.sp_kt_v > candidate.forecast.adequacy.sp_kt_v
            )
            for other in compared
        )
        output.append(
            replace(
                candidate,
                on_safety_adequacy_frontier=candidate.feasible and not dominated,
            )
        )
    return output


def generate_parallel_futures(
    patient: PatientProfile,
    baseline: Prescription,
    minimum_kt_v: float = 1.2,
) -> tuple[Candidate, ...]:
    target_uf = baseline.ultrafiltration_l
    options = [
        ("baseline", baseline),
        (
            "longer-session",
            Prescription(285, 330, 500, target_uf, 36.0, baseline.dialyzer_koa_ml_min),
        ),
        ("balanced", Prescription(270, 350, 500, target_uf, 36.0, baseline.dialyzer_koa_ml_min)),
        (
            "gentle-profile",
            Prescription(300, 320, 500, target_uf, 35.8, baseline.dialyzer_koa_ml_min),
        ),
        (
            "short-high-flow",
            Prescription(210, 400, 600, target_uf, 36.5, baseline.dialyzer_koa_ml_min),
        ),
    ]
    candidates = _with_comparisons([
        evaluate_candidate(identifier, patient, prescription, minimum_kt_v)
        for identifier, prescription in options
    ])
    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                not item.feasible,
                item.forecast.peak_idh_risk,
                -item.forecast.adequacy.sp_kt_v,
            ),
        )
    )
