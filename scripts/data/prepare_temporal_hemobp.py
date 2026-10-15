from __future__ import annotations

import argparse
import csv
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import asdict
from itertools import groupby
from pathlib import Path
from typing import Any

from apps.api.nephron.data.hemobp import as_float, date_part, pseudonymize_patient
from apps.api.nephron.ml.temporal import SessionObservation, build_warning_examples

DEFAULT_RAW = Path("data/raw/hemobp-v3")
DEFAULT_PROCESSED = Path("data/processed/hemobp-v3")
OUTPUT_FIELDS = [
    "patient_id",
    "session_id",
    "split",
    "minute",
    "current_sbp_mmhg",
    "current_dbp_mmhg",
    "sbp_change_from_baseline",
    "sbp_slope_30m",
    "current_uf_l_h",
    "current_blood_flow_ml_min",
    "minutes_to_event",
    "event_within_horizon",
    "age_years",
    "sex",
    "diabetes",
    "weight_start_kg",
    "dry_weight_kg",
    "body_temperature_c",
    "prior_session_count",
    "prior_idh_rate_10",
    "prior_mean_nadir_sbp_10",
    "previous_session_idh",
    "previous_nadir_sbp_mmhg",
]


def load_session_metadata(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["session_id"]: row for row in csv.DictReader(handle)}


def raw_session_lookup(
    metadata: dict[str, dict[str, Any]], raw_dir: Path
) -> dict[tuple[str, str], str]:
    by_pseudonym: dict[str, dict[str, str]] = {}
    for session_id, row in metadata.items():
        by_pseudonym.setdefault(row["patient_id"], {})[row["session_date"]] = session_id
    lookup: dict[tuple[str, str], str] = {}
    # Raw identifiers are not written to the processed output or SQLite working table.
    with (raw_dir / "idp.csv").open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            pseudonym = pseudonymize_patient(row["pid"])
            for session_date, session_id in by_pseudonym.get(pseudonym, {}).items():
                lookup[(row["pid"], session_date)] = session_id
    return lookup


def _bounded(value: str | None, minimum: float, maximum: float) -> float | None:
    parsed = as_float(value)
    return parsed if parsed is not None and minimum <= parsed <= maximum else None


def stage_observations(
    connection: sqlite3.Connection,
    vip_path: Path,
    lookup: dict[tuple[str, str], str],
) -> int:
    connection.execute(
        "CREATE TABLE observations ("
        "session_id TEXT NOT NULL, minute REAL NOT NULL, sbp REAL NOT NULL, "
        "dbp REAL, uf REAL, blood_flow REAL)"
    )
    batch: list[tuple[Any, ...]] = []
    inserted = 0
    with vip_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            session_date = date_part(row.get("datatime"))
            session_id = lookup.get((row["pid"], session_date or ""))
            minute = _bounded(row.get("time"), 0, 600)
            sbp = _bounded(row.get("sbp"), 30, 250)
            if session_id is None or minute is None or sbp is None:
                continue
            batch.append(
                (
                    session_id,
                    minute,
                    sbp,
                    _bounded(row.get("dbp"), 20, 160),
                    _bounded(row.get("uf"), 0, 5),
                    _bounded(row.get("blood_flow"), 0, 600),
                )
            )
            if len(batch) >= 20_000:
                connection.executemany("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)", batch)
                inserted += len(batch)
                batch.clear()
    if batch:
        connection.executemany("INSERT INTO observations VALUES (?, ?, ?, ?, ?, ?)", batch)
        inserted += len(batch)
    connection.execute("CREATE INDEX observation_order ON observations(session_id, minute)")
    connection.commit()
    return inserted


def write_temporal_rows(
    connection: sqlite3.Connection,
    metadata: dict[str, dict[str, Any]],
    output_dir: Path,
) -> dict[str, int]:
    handles = {
        split: (output_dir / f"temporal-{split}.csv").open("w", newline="", encoding="utf-8")
        for split in ("train", "validation", "test")
    }
    writers = {
        split: csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        for split, handle in handles.items()
    }
    for writer in writers.values():
        writer.writeheader()
    counts = {split: 0 for split in handles}
    cursor = connection.execute(
        "SELECT session_id, minute, sbp, dbp, uf, blood_flow "
        "FROM observations ORDER BY session_id, minute"
    )
    try:
        for session_id, group in groupby(cursor, key=lambda item: item[0]):
            session = metadata[session_id]
            observations = tuple(
                SessionObservation(
                    minute=row[1],
                    sbp_mmhg=row[2],
                    dbp_mmhg=row[3],
                    uf_l_h=row[4],
                    blood_flow_ml_min=row[5],
                )
                for row in group
            )
            for example in build_warning_examples(session_id, observations):
                payload = asdict(example)
                payload.update(
                    {
                        "patient_id": session["patient_id"],
                        "split": session["split"],
                        **{name: session.get(name) for name in OUTPUT_FIELDS if name in session},
                    }
                )
                writers[session["split"]].writerow(payload)
                counts[session["split"]] += 1
    finally:
        for handle in handles.values():
            handle.close()
    return counts


def prepare(raw_dir: Path, output_dir: Path) -> dict[str, int]:
    metadata = load_session_metadata(output_dir / "sessions-all.csv")
    lookup = raw_session_lookup(metadata, raw_dir)
    with tempfile.NamedTemporaryFile(suffix=".sqlite", dir=output_dir, delete=False) as temporary:
        database_path = Path(temporary.name)
    try:
        with closing(sqlite3.connect(database_path)) as connection:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            stage_observations(connection, raw_dir / "vip.csv", lookup)
            return write_temporal_rows(connection, metadata, output_dir)
    finally:
        database_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build leakage-resistant HEMOBP warning windows")
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_PROCESSED)
    arguments = parser.parse_args()
    print(prepare(arguments.raw_dir, arguments.output_dir))


if __name__ == "__main__":
    main()
