import numpy as np
import pandas as pd

from apps.api.nephron.ml.temporal_training import session_operating_threshold


def test_session_threshold_targets_sensitivity_without_row_weighting() -> None:
    context = pd.DataFrame(
        {
            "session_id": ["event-a", "event-a", "event-b", "quiet", "quiet"],
            "minute": [0, 30, 0, 0, 30],
            "minutes_to_event": [60, 30, 45, np.nan, np.nan],
        }
    )
    probability = np.array([0.7, 0.8, 0.75, 0.1, 0.2])
    threshold = session_operating_threshold(context, probability)
    assert 0.2 < threshold <= 0.75
