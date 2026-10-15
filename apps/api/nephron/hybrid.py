from __future__ import annotations

from dataclasses import dataclass
from math import exp, log


@dataclass(frozen=True)
class HybridRisk:
    probability: float
    lower_bound: float
    upper_bound: float
    physics_probability: float
    learned_probability: float
    learned_weight: float
    disagreement: float
    status: str
    audit_trace: tuple[str, ...]


def _bounded_probability(value: float) -> float:
    if not 0 <= value <= 1:
        raise ValueError("Probabilities must be between zero and one")
    return min(1 - 1e-6, max(1e-6, value))


def _logit(probability: float) -> float:
    probability = _bounded_probability(probability)
    return log(probability / (1 - probability))


def fuse_risk(
    physics_probability: float,
    learned_probability: float,
    *,
    data_quality: float,
    learned_model_externally_validated: bool = False,
) -> HybridRisk:
    """Fuse independently testable risk channels without concealing disagreement."""
    if not 0 <= data_quality <= 1:
        raise ValueError("Data quality must be between zero and one")
    physics = _bounded_probability(physics_probability)
    learned = _bounded_probability(learned_probability)
    maximum_learned_weight = 0.55 if learned_model_externally_validated else 0.35
    learned_weight = maximum_learned_weight * data_quality
    combined_logit = (1 - learned_weight) * _logit(physics) + learned_weight * _logit(learned)
    probability = 1 / (1 + exp(-combined_logit))
    disagreement = abs(physics - learned)
    uncertainty = min(0.35, 0.06 + 0.45 * disagreement + 0.18 * (1 - data_quality))
    status = "discordant" if disagreement >= 0.30 else "concordant"
    return HybridRisk(
        probability=round(probability, 4),
        lower_bound=round(max(0, probability - uncertainty), 4),
        upper_bound=round(min(1, probability + uncertainty), 4),
        physics_probability=round(physics_probability, 4),
        learned_probability=round(learned_probability, 4),
        learned_weight=round(learned_weight, 3),
        disagreement=round(disagreement, 4),
        status=status,
        audit_trace=(
            "Combined probabilities in log-odds space",
            f"Capped learned-model weight at {maximum_learned_weight:.2f}",
            f"Scaled learned-model weight by data quality {data_quality:.2f}",
            "Expanded uncertainty when model channels disagreed",
        ),
    )
