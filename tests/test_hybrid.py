import pytest

from apps.api.nephron.hybrid import fuse_risk


def test_unvalidated_model_weight_is_capped() -> None:
    result = fuse_risk(0.2, 0.8, data_quality=1, learned_model_externally_validated=False)
    assert result.learned_weight == 0.35
    assert 0.2 < result.probability < 0.8
    assert result.status == "discordant"


def test_disagreement_widens_interval() -> None:
    agreeing = fuse_risk(0.4, 0.45, data_quality=0.9)
    disagreeing = fuse_risk(0.1, 0.9, data_quality=0.9)
    agreeing_width = agreeing.upper_bound - agreeing.lower_bound
    disagreeing_width = disagreeing.upper_bound - disagreeing.lower_bound
    assert disagreeing_width > agreeing_width


def test_invalid_probability_fails_closed() -> None:
    with pytest.raises(ValueError):
        fuse_risk(1.2, 0.5, data_quality=1)
