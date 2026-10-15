from datetime import date

from apps.api.nephron.demo import meera_profile
from apps.api.nephron.twin import HistoricalSession, calibrate_patient_twin


def test_calibration_excludes_future_and_incomplete_sessions() -> None:
    patient = meera_profile()
    history = (
        HistoricalSession(date(2026, 1, 1), 82, True),
        HistoricalSession(date(2026, 1, 2), 70, True, completed=False),
        HistoricalSession(date(2026, 1, 4), 65, True),
    )
    result = calibrate_patient_twin(patient, history, as_of=date(2026, 1, 3))
    assert result.source_session_count == 1
    assert result.latest_session_date == date(2026, 1, 1)
    assert result.confidence == "low"


def test_calibration_shrinks_sparse_history() -> None:
    patient = meera_profile()
    result = calibrate_patient_twin(
        patient,
        (HistoricalSession(date(2026, 1, 1), 80, True),),
        as_of=date(2026, 1, 2),
    )
    assert patient.prior_idh_rate < result.patient.prior_idh_rate < 1
    assert 80 < result.patient.prior_nadir_sbp < patient.prior_nadir_sbp
    assert result.effective_history_weight == 0.2


def test_calibration_is_order_independent_and_bounded_to_recent_history() -> None:
    patient = meera_profile()
    history = tuple(
        HistoricalSession(date(2026, 1, day), 80 + day, day % 2 == 0)
        for day in range(1, 13)
    )
    first = calibrate_patient_twin(patient, history, as_of=date(2026, 2, 1))
    second = calibrate_patient_twin(patient, tuple(reversed(history)), as_of=date(2026, 2, 1))
    assert first == second
    assert first.source_session_count == 10
    assert first.confidence == "high"
