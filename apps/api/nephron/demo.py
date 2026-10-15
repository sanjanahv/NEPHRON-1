from .domain import PatientProfile, Prescription


def meera_profile() -> PatientProfile:
    return PatientProfile(
        patient_id="DT-042",
        age_years=58,
        sex="female",
        pre_weight_kg=64.8,
        dry_weight_kg=61.5,
        pre_sbp_mmhg=132,
        pre_dbp_mmhg=78,
        urea_pre_mg_dl=148,
        prior_idh_rate=5 / 18,
        prior_nadir_sbp=91,
        diabetes=True,
        cardiac_disease=True,
        hemoglobin_g_dl=9.4,
        albumin_g_dl=3.4,
    )


def meera_baseline() -> Prescription:
    return Prescription(
        duration_minutes=240,
        blood_flow_ml_min=320,
        dialysate_flow_ml_min=500,
        ultrafiltration_l=3.3,
        dialysate_temperature_c=36.5,
        dialyzer_koa_ml_min=700,
    )
