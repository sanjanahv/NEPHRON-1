from __future__ import annotations

from .domain import Forecast, PatientProfile, Prescription, RiskBand
from .physics import estimate_adequacy, simulate_physiology


def risk_band(probability: float) -> RiskBand:
    if probability >= 0.75:
        return RiskBand.CRITICAL
    if probability >= 0.50:
        return RiskBand.HIGH
    if probability >= 0.25:
        return RiskBand.MODERATE
    return RiskBand.LOW


def explain_risk(patient: PatientProfile, prescription: Prescription) -> tuple[str, ...]:
    reasons: list[tuple[float, str]] = []
    uf_rate = prescription.uf_rate_ml_kg_h(patient.pre_weight_kg)
    if uf_rate > 10:
        reasons.append(
            (uf_rate - 10, "Ultrafiltration rate is above the personalized tolerance range")
        )
    if patient.prior_idh_rate >= 0.2:
        reasons.append(
            (
                patient.prior_idh_rate * 5,
                "Recurrent hypotension is present in recent sessions",
            )
        )
    if patient.prior_nadir_sbp < 100:
        reasons.append(((100 - patient.prior_nadir_sbp) / 10, "Recent nadir blood pressure is low"))
    if patient.interdialytic_weight_gain_kg > 3:
        reasons.append(
            (
                patient.interdialytic_weight_gain_kg / 3,
                "Interdialytic weight gain increases the fluid-removal burden",
            )
        )
    if patient.albumin_g_dl < 3.5:
        reasons.append(
            (
                (3.5 - patient.albumin_g_dl) * 2,
                "Low albumin may reduce plasma-refill resilience",
            )
        )
    if not reasons:
        reasons.append((0.1, "No dominant high-risk signal was detected"))
    return tuple(text for _, text in sorted(reasons, reverse=True)[:4])


def forecast_session(
    patient: PatientProfile,
    prescription: Prescription,
    data_quality: float = 0.94,
) -> Forecast:
    if not 0 <= data_quality <= 1:
        raise ValueError("Data quality must be between zero and one")
    points = simulate_physiology(patient, prescription)
    peak = max(point.idh_risk for point in points)
    warning = next((point.minute for point in points if point.idh_risk >= 0.5), None)
    return Forecast(
        points=points,
        peak_idh_risk=peak,
        warning_minute=warning,
        risk_band=risk_band(peak),
        adequacy=estimate_adequacy(patient, prescription),
        data_quality=data_quality,
        reasons=explain_risk(patient, prescription),
    )
