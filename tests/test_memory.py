from pathlib import Path

import pytest

from apps.api.nephron.memory import CompletedSession, SessionMemory


def session(identifier: str, nadir: float = 88) -> CompletedSession:
    return CompletedSession(
        session_id=identifier,
        patient_id="patient-1",
        session_date=f"2026-01-{int(identifier[-1]) + 1:02d}",
        nadir_sbp_mmhg=nadir,
        idh_event=nadir < 90,
        actual_uf_l=2.8,
        duration_minutes=240,
        delivered_kt_v=1.3,
        predicted_nadir_sbp_mmhg=92,
        predicted_kt_v=1.25,
    )


def test_session_memory_is_idempotent_and_exposes_prediction_error(tmp_path: Path) -> None:
    memory = SessionMemory(tmp_path / "memory.sqlite")
    memory.record(session("s1"))
    memory.record(session("s1"))
    comparison = memory.comparison("patient-1")
    assert comparison["source_session_count"] == 1
    assert comparison["sessions"][0]["nadir_error_mmhg"] == -4


def test_session_memory_rejects_conflicting_duplicate(tmp_path: Path) -> None:
    memory = SessionMemory(tmp_path / "memory.sqlite")
    memory.record(session("s1"))
    with pytest.raises(ValueError):
        memory.record(session("s1", nadir=80))


def test_recalibration_requires_four_sessions(tmp_path: Path) -> None:
    memory = SessionMemory(tmp_path / "memory.sqlite")
    for index in range(1, 5):
        memory.record(session(f"s{index}"))
    assert memory.comparison("patient-1")["recalibration_ready"] is True
