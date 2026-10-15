"""Transparent physiological approximations used by the prototype twin.

The functions in this module are deterministic and deliberately isolated from the
learned risk layer. They are suitable for simulation and unit testing, not clinical use.
"""

from __future__ import annotations

from math import exp, log

from .domain import Adequacy, PatientProfile, Prescription, TimePoint


def dialyzer_clearance_ml_min(
    blood_flow_ml_min: float,
    dialysate_flow_ml_min: float,
    koa_ml_min: float,
) -> float:
    """Approximate small-solute clearance using a flow-limited mass-transfer model."""
    if min(blood_flow_ml_min, dialysate_flow_ml_min, koa_ml_min) <= 0:
        raise ValueError("Flow rates and KoA must be positive")
    flow_limit = (blood_flow_ml_min * dialysate_flow_ml_min) / (
        blood_flow_ml_min + dialysate_flow_ml_min
    )
    membrane_factor = 1 - exp(-koa_ml_min / (blood_flow_ml_min + dialysate_flow_ml_min))
    return min(blood_flow_ml_min, flow_limit * (1 + membrane_factor))


def estimate_adequacy(patient: PatientProfile, prescription: Prescription) -> Adequacy:
    clearance = dialyzer_clearance_ml_min(
        prescription.blood_flow_ml_min,
        prescription.dialysate_flow_ml_min,
        prescription.dialyzer_koa_ml_min,
    )
    distribution_volume_l = max(20.0, 0.55 * patient.dry_weight_kg)
    raw_kt_v = clearance * prescription.duration_minutes / (distribution_volume_l * 1000)
    # Correct the idealized value for access recirculation and urea rebound.
    sp_kt_v = raw_kt_v * 0.91
    urr = 100 * (1 - exp(-sp_kt_v))
    return Adequacy(round(urr, 1), round(sp_kt_v, 2), round(clearance, 1))


def daugirdas_sp_kt_v(
    pre_urea_mg_dl: float,
    post_urea_mg_dl: float,
    duration_hours: float,
    ultrafiltration_l: float,
    post_weight_kg: float,
) -> float:
    """Second-generation Daugirdas estimate for delivered single-pool Kt/V."""
    if min(pre_urea_mg_dl, post_urea_mg_dl, duration_hours, post_weight_kg) <= 0:
        raise ValueError("Daugirdas inputs must be positive")
    ratio = post_urea_mg_dl / pre_urea_mg_dl
    value = -log(ratio - 0.008 * duration_hours) + (4 - 3.5 * ratio) * (
        ultrafiltration_l / post_weight_kg
    )
    return round(value, 2)


def simulate_physiology(
    patient: PatientProfile,
    prescription: Prescription,
    step_minutes: int = 5,
) -> tuple[TimePoint, ...]:
    if step_minutes <= 0:
        raise ValueError("Step size must be positive")

    adequacy = estimate_adequacy(patient, prescription)
    uf_rate = prescription.uf_rate_ml_kg_h(patient.pre_weight_kg)
    points: list[TimePoint] = []

    for minute in range(0, prescription.duration_minutes + 1, step_minutes):
        fraction = minute / prescription.duration_minutes
        cumulative_uf = prescription.ultrafiltration_l * fraction
        refill_fraction = 0.43 + min(0.20, patient.albumin_g_dl * 0.035)
        net_intravascular_loss_l = cumulative_uf * (1 - refill_fraction)
        plasma_change = -100 * net_intravascular_loss_l / max(2.4, patient.pre_weight_kg * 0.045)

        vulnerability = (
            0.42 * patient.prior_idh_rate
            + 0.006 * max(0, 105 - patient.prior_nadir_sbp)
            + 0.08 * float(patient.diabetes)
            + 0.10 * float(patient.cardiac_disease)
        )
        thermal_relief = max(0.0, 36.5 - prescription.dialysate_temperature_c) * 2.0
        sbp_drop = (
            0.20 * minute
            + max(0, uf_rate - 7.0) * 1.15 * fraction
            + abs(plasma_change) * (0.55 + vulnerability)
            - thermal_relief * fraction
        )
        sbp = patient.pre_sbp_mmhg - sbp_drop
        dbp = patient.pre_dbp_mmhg - sbp_drop * 0.43
        cardiac_output = max(2.7, 4.9 + plasma_change * 0.075 - vulnerability * 0.8)
        urea = patient.urea_pre_mg_dl * exp(-adequacy.sp_kt_v * fraction)

        hemodynamic_signal = (92 - sbp) / 12
        rate_signal = (uf_rate - 8.0) / 3.0
        history_signal = patient.prior_idh_rate * 2.1
        logit = -2.2 + hemodynamic_signal + 0.52 * rate_signal + history_signal
        risk = 1 / (1 + exp(-logit))
        uncertainty = 4.0 + 3.0 * fraction

        points.append(
            TimePoint(
                minute=minute,
                sbp_mmhg=round(sbp, 1),
                dbp_mmhg=round(dbp, 1),
                plasma_volume_change_pct=round(plasma_change, 1),
                estimated_cardiac_output_l_min=round(cardiac_output, 2),
                cumulative_uf_l=round(cumulative_uf, 2),
                urea_mg_dl=round(urea, 1),
                idh_risk=round(risk, 4),
                confidence_low_sbp=round(sbp - uncertainty, 1),
                confidence_high_sbp=round(sbp + uncertainty, 1),
            )
        )
    return tuple(points)
