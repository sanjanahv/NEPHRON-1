from apps.api.nephron.data.hemobp import (
    SessionAggregate,
    add_prior_history,
    build_session_row,
    patient_split,
    pseudonymize_patient,
)


def test_patient_pseudonym_is_stable_and_nonidentifying() -> None:
    first = pseudonymize_patient("123456")
    assert first == pseudonymize_patient("123456")
    assert "123456" not in first


def test_patient_split_is_stable() -> None:
    patient = pseudonymize_patient("ABC")
    assert patient_split(patient) == patient_split(patient)
    assert patient_split(patient) in {"train", "validation", "test"}


def test_bp_proxy_label_requires_drop_and_low_nadir() -> None:
    aggregate = SessionAggregate("raw", "2026-01-01")
    aggregate.baseline_elapsed = 0
    aggregate.baseline_sbp = 130
    aggregate.baseline_dbp = 75
    aggregate.nadir_sbp = 89
    aggregate.sbp_sum = 327
    aggregate.max_elapsed = 60
    aggregate.observations = 3
    patient = {"patient_id": "HBP-test", "birth_year": 1970, "sex": "F", "diabetes": 0}
    row = build_session_row(aggregate, patient, None)
    assert row is not None
    assert row["label_nadir90"] == 1
    assert row["label_drop20_nadir90"] == 1


def test_split_sets_are_disjoint_for_many_patients() -> None:
    partitions = {"train": set(), "validation": set(), "test": set()}
    for index in range(1000):
        patient = pseudonymize_patient(str(index))
        partitions[patient_split(patient)].add(patient)
    assert partitions["train"].isdisjoint(partitions["validation"])
    assert partitions["train"].isdisjoint(partitions["test"])
    assert partitions["validation"].isdisjoint(partitions["test"])


def test_history_features_never_include_current_session() -> None:
    rows = [
        {
            "patient_id": "P1",
            "label_drop20_nadir90": label,
            "nadir_sbp_mmhg": nadir,
            "sbp_drop_mmhg": drop,
        }
        for label, nadir, drop in [(1, 85, 30), (0, 105, 12), (1, 88, 26)]
    ]
    add_prior_history(rows)
    assert rows[0]["prior_session_count"] == 0
    assert rows[1]["prior_idh_rate_10"] == 1.0
    assert rows[2]["prior_idh_rate_10"] == 0.5
    assert rows[2]["previous_nadir_sbp_mmhg"] == 105
