from datetime import date

from apps.api.nephron.multisystem import LabObservation, map_multisystem_trends


def test_multisystem_trends_separate_measured_and_modeled_signals() -> None:
    observations = (
        LabObservation(date(2026, 1, 1), 10.2, 8.7, 5.4, 410),
        LabObservation(date(2026, 2, 1), 9.7, 8.8, 6.5, 470),
    )
    anemia, mineral, cardiovascular = map_multisystem_trends(
        observations,
        mean_pre_sbp_mmhg=148,
        mean_weight_gain_kg=3.4,
    )
    assert anemia.trend_per_30_days is not None and anemia.trend_per_30_days < 0
    assert mineral.latest_value is not None and mineral.status == "attention"
    assert cardiovascular.source.startswith("modeled")
    assert "Not an LVH" in cardiovascular.interpretation


def test_echo_measurement_is_not_replaced_by_burden_proxy() -> None:
    *_, cardiovascular = map_multisystem_trends(
        (),
        measured_lv_mass_index_g_m2=126,
    )
    assert cardiovascular.label == "LV mass index"
    assert cardiovascular.source == "measured echocardiography"
    assert cardiovascular.latest_value == 126
