from apps.api.nephron.quality import StreamSnapshot, assess_streams


def healthy() -> StreamSnapshot:
    return StreamSnapshot(20, 124, 72, 320, 1.2, 3.0, 90, 240)


def test_healthy_streams_remain_normal() -> None:
    result = assess_streams(healthy())
    assert result.mode == "normal"
    assert result.score == 1


def test_missing_blood_pressure_disables_forecast() -> None:
    snapshot = StreamSnapshot(20, None, 72, 320, 1.2, 3.0, 90, 240)
    result = assess_streams(snapshot)
    assert result.mode == "unavailable"
    assert "IDH forecast" in result.disabled_outputs


def test_contradictory_streams_fail_conservatively() -> None:
    snapshot = StreamSnapshot(20, 80, 95, 700, 3.8, 3.0, 90, 240)
    result = assess_streams(snapshot)
    assert result.mode == "unavailable"
    assert len(result.issues) >= 3


def test_delayed_stream_enters_conservative_mode() -> None:
    snapshot = StreamSnapshot(360, 124, 72, 320, 1.2, 3.0, 90, 240)
    assert assess_streams(snapshot).mode == "conservative"
