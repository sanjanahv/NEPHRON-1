from __future__ import annotations

import csv
import random
from dataclasses import asdict
from pathlib import Path

from .domain import PatientProfile, Prescription
from .physics import simulate_physiology


def generate_cohort(
    output: Path,
    patients: int = 120,
    sessions: int = 18,
    seed: int = 2026,
) -> None:
    """Create a deterministic, visibly synthetic training cohort."""
    rng = random.Random(seed)
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "patient_id", "session_id", "minute", "age_years", "sex", "diabetes",
        "cardiac_disease", "pre_weight_kg", "dry_weight_kg", "pre_sbp_mmhg",
        "pre_dbp_mmhg", "prior_idh_rate", "prior_nadir_sbp", "hemoglobin_g_dl",
        "albumin_g_dl", "duration_minutes", "blood_flow_ml_min",
        "dialysate_flow_ml_min", "ultrafiltration_l", "dialysate_temperature_c",
        "sbp_mmhg", "dbp_mmhg", "plasma_volume_change_pct", "cumulative_uf_l",
        "urea_mg_dl", "idh_risk", "idh_label",
    ]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for patient_index in range(patients):
            dry_weight = rng.uniform(45, 90)
            profile = PatientProfile(
                patient_id=f"SYN-{patient_index + 1:04d}",
                age_years=rng.randint(28, 82),
                sex=rng.choice(("female", "male")),
                pre_weight_kg=dry_weight + rng.uniform(1.5, 4.5),
                dry_weight_kg=dry_weight,
                pre_sbp_mmhg=rng.uniform(105, 165),
                pre_dbp_mmhg=rng.uniform(58, 92),
                urea_pre_mg_dl=rng.uniform(90, 210),
                prior_idh_rate=rng.betavariate(2, 7),
                prior_nadir_sbp=rng.uniform(78, 115),
                diabetes=rng.random() < 0.48,
                cardiac_disease=rng.random() < 0.28,
                hemoglobin_g_dl=rng.uniform(8.2, 12.2),
                albumin_g_dl=rng.uniform(2.9, 4.5),
            )
            for session_index in range(sessions):
                prescription = Prescription(
                    duration_minutes=rng.choice((210, 240, 270, 300)),
                    blood_flow_ml_min=rng.choice((280, 300, 320, 350, 380)),
                    dialysate_flow_ml_min=rng.choice((500, 600)),
                    ultrafiltration_l=rng.uniform(1.5, 4.8),
                    dialysate_temperature_c=rng.choice((35.8, 36.0, 36.5)),
                )
                for point in simulate_physiology(profile, prescription, step_minutes=15):
                    writer.writerow({
                        "patient_id": profile.patient_id,
                        "session_id": f"{profile.patient_id}-S{session_index + 1:02d}",
                        "minute": point.minute,
                        "age_years": profile.age_years,
                        "sex": profile.sex,
                        "diabetes": int(profile.diabetes),
                        "cardiac_disease": int(profile.cardiac_disease),
                        "pre_weight_kg": round(profile.pre_weight_kg, 2),
                        "dry_weight_kg": round(profile.dry_weight_kg, 2),
                        "pre_sbp_mmhg": round(profile.pre_sbp_mmhg, 1),
                        "pre_dbp_mmhg": round(profile.pre_dbp_mmhg, 1),
                        "prior_idh_rate": round(profile.prior_idh_rate, 3),
                        "prior_nadir_sbp": round(profile.prior_nadir_sbp, 1),
                        "hemoglobin_g_dl": round(profile.hemoglobin_g_dl, 1),
                        "albumin_g_dl": round(profile.albumin_g_dl, 1),
                        **{
                            key: value
                            for key, value in asdict(prescription).items()
                            if key in fields
                        },
                        "sbp_mmhg": point.sbp_mmhg,
                        "dbp_mmhg": point.dbp_mmhg,
                        "plasma_volume_change_pct": point.plasma_volume_change_pct,
                        "cumulative_uf_l": point.cumulative_uf_l,
                        "urea_mg_dl": point.urea_mg_dl,
                        "idh_risk": point.idh_risk,
                        "idh_label": int(point.sbp_mmhg < 90),
                    })


if __name__ == "__main__":
    generate_cohort(Path("data/processed/synthetic_sessions.csv"))
