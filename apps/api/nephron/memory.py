from __future__ import annotations

import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median


@dataclass(frozen=True)
class CompletedSession:
    session_id: str
    patient_id: str
    session_date: str
    nadir_sbp_mmhg: float
    idh_event: bool
    actual_uf_l: float
    duration_minutes: int
    delivered_kt_v: float | None
    predicted_nadir_sbp_mmhg: float | None
    predicted_kt_v: float | None


class SessionMemory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute(
            """CREATE TABLE IF NOT EXISTS completed_sessions (
            session_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            session_date TEXT NOT NULL,
            nadir_sbp_mmhg REAL NOT NULL,
            idh_event INTEGER NOT NULL,
            actual_uf_l REAL NOT NULL,
            duration_minutes INTEGER NOT NULL,
            delivered_kt_v REAL,
            predicted_nadir_sbp_mmhg REAL,
            predicted_kt_v REAL,
            recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        return connection

    def record(self, session: CompletedSession) -> None:
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT * FROM completed_sessions WHERE session_id = ?", (session.session_id,)
            ).fetchone()
            if existing is not None:
                prior = self._from_row(existing)
                if prior == session:
                    return
                raise ValueError("A different completed session already uses this session_id")
            connection.execute(
                "INSERT INTO completed_sessions ("
                "session_id, patient_id, session_date, nadir_sbp_mmhg, idh_event, actual_uf_l, "
                "duration_minutes, delivered_kt_v, predicted_nadir_sbp_mmhg, predicted_kt_v"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    session.session_id,
                    session.patient_id,
                    session.session_date,
                    session.nadir_sbp_mmhg,
                    int(session.idh_event),
                    session.actual_uf_l,
                    session.duration_minutes,
                    session.delivered_kt_v,
                    session.predicted_nadir_sbp_mmhg,
                    session.predicted_kt_v,
                ),
            )

    def patient_history(self, patient_id: str, limit: int = 10) -> tuple[CompletedSession, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM completed_sessions WHERE patient_id = ? "
                "ORDER BY session_date DESC, session_id DESC LIMIT ?",
                (patient_id, limit),
            ).fetchall()
        return tuple(self._from_row(row) for row in rows)

    def comparison(self, patient_id: str, limit: int = 10) -> dict[str, object]:
        history = self.patient_history(patient_id, limit)
        sessions = []
        for item in reversed(history):
            payload = asdict(item)
            payload["nadir_error_mmhg"] = (
                round(item.nadir_sbp_mmhg - item.predicted_nadir_sbp_mmhg, 1)
                if item.predicted_nadir_sbp_mmhg is not None
                else None
            )
            payload["kt_v_error"] = (
                round(item.delivered_kt_v - item.predicted_kt_v, 2)
                if item.delivered_kt_v is not None and item.predicted_kt_v is not None
                else None
            )
            sessions.append(payload)
        return {
            "patient_id": patient_id,
            "source_session_count": len(history),
            "sessions": sessions,
            "recalibration_ready": len(history) >= 4,
            "calibration_inputs": {
                "prior_idh_rate": round(sum(item.idh_event for item in history) / len(history), 4)
                if history
                else None,
                "prior_nadir_sbp_mmhg": round(median(item.nadir_sbp_mmhg for item in history), 1)
                if history
                else None,
            },
        }

    @staticmethod
    def _from_row(row: sqlite3.Row) -> CompletedSession:
        return CompletedSession(
            session_id=row["session_id"],
            patient_id=row["patient_id"],
            session_date=row["session_date"],
            nadir_sbp_mmhg=row["nadir_sbp_mmhg"],
            idh_event=bool(row["idh_event"]),
            actual_uf_l=row["actual_uf_l"],
            duration_minutes=row["duration_minutes"],
            delivered_kt_v=row["delivered_kt_v"],
            predicted_nadir_sbp_mmhg=row["predicted_nadir_sbp_mmhg"],
            predicted_kt_v=row["predicted_kt_v"],
        )
