from apps.api.nephron.counterfactual import generate_parallel_futures
from apps.api.nephron.demo import meera_baseline, meera_profile
from apps.api.nephron.domain import Prescription, RiskBand
from apps.api.nephron.risk import forecast_session, risk_band


def test_risk_band_thresholds() -> None:
    assert risk_band(0.1) is RiskBand.LOW
    assert risk_band(0.3) is RiskBand.MODERATE
    assert risk_band(0.6) is RiskBand.HIGH
    assert risk_band(0.8) is RiskBand.CRITICAL


def test_forecast_is_explainable() -> None:
    forecast = forecast_session(meera_profile(), meera_baseline())
    assert forecast.reasons
    assert 0 <= forecast.peak_idh_risk <= 1
    assert forecast.data_quality == 0.94


def test_parallel_futures_are_ranked_feasible_first() -> None:
    futures = generate_parallel_futures(meera_profile(), meera_baseline())
    feasible_flags = [future.feasible for future in futures]
    assert feasible_flags == sorted(feasible_flags, reverse=True)
    assert any(future.candidate_id == "baseline" for future in futures)
    assert any(future.on_safety_adequacy_frontier for future in futures)
    baseline = next(future for future in futures if future.candidate_id == "baseline")
    assert baseline.peak_risk_delta == 0
    assert baseline.kt_v_delta == 0
    assert baseline.decision_trace


def test_lower_uf_rate_reduces_modeled_risk() -> None:
    patient = meera_profile()
    high = forecast_session(patient, Prescription(240, 320, 500, 4.2))
    low = forecast_session(patient, Prescription(300, 320, 500, 2.4))
    assert low.peak_idh_risk < high.peak_idh_risk
