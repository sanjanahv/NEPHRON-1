from apps.api.nephron.demo import meera_baseline, meera_profile
from apps.api.nephron.domain import Prescription
from apps.api.nephron.physics import (
    daugirdas_sp_kt_v,
    dialyzer_clearance_ml_min,
    estimate_adequacy,
    simulate_physiology,
)


def test_clearance_is_positive_and_flow_limited() -> None:
    clearance = dialyzer_clearance_ml_min(320, 500, 700)
    assert 150 < clearance < 320


def test_adequacy_increases_with_duration() -> None:
    patient = meera_profile()
    short = Prescription(180, 320, 500, 3.3)
    long = Prescription(300, 320, 500, 3.3)
    assert estimate_adequacy(patient, long).sp_kt_v > estimate_adequacy(patient, short).sp_kt_v


def test_higher_ultrafiltration_worsens_nadir_pressure() -> None:
    patient = meera_profile()
    gentle = Prescription(240, 320, 500, 1.8)
    aggressive = Prescription(240, 320, 500, 4.5)
    gentle_nadir = min(point.sbp_mmhg for point in simulate_physiology(patient, gentle))
    aggressive_nadir = min(point.sbp_mmhg for point in simulate_physiology(patient, aggressive))
    assert aggressive_nadir < gentle_nadir


def test_simulation_hits_prescribed_fluid_target() -> None:
    points = simulate_physiology(meera_profile(), meera_baseline())
    assert points[-1].cumulative_uf_l == meera_baseline().ultrafiltration_l
    assert points[0].minute == 0
    assert points[-1].minute == meera_baseline().duration_minutes


def test_daugirdas_returns_plausible_value() -> None:
    value = daugirdas_sp_kt_v(150, 52, 4, 3.0, 61.5)
    assert 1.0 < value < 2.0
