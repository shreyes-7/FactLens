"""
FactLens Reasoning Module.
Contains deterministic rule evaluation and hybrid relationship classification.
"""

from backend.app.reasoning.deterministic import (
    compute_numeric_variance,
    evaluate_deterministic_relationship,
)
from backend.app.reasoning.relationship_classifier import RelationshipClassifier

__all__ = [
    "compute_numeric_variance",
    "evaluate_deterministic_relationship",
    "RelationshipClassifier",
]
