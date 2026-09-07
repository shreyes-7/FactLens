"""
Similarity computation engine for candidate matching.
Calculates vector cosine similarity, token Jaccard similarity, and hybrid ranking scores.
"""

import math
import re
from typing import Any


def cosine_similarity(vec_a: list[float] | None, vec_b: list[float] | None) -> float:
    """
    Compute cosine similarity between two float vectors.
    Returns float in range [0.0, 1.0] (clamped for normalized embedding spaces).
    """
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0

    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))

    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0

    sim = dot / (norm_a * norm_b)
    # Clamp to [0.0, 1.0]
    return max(0.0, min(1.0, float(sim)))


def token_jaccard_similarity(text_a: str | None, text_b: str | None) -> float:
    """Compute token-level Jaccard similarity between two text strings."""
    if not text_a or not text_b:
        return 0.0

    tokens_a = set(re.findall(r"\w+", text_a.lower()))
    tokens_b = set(re.findall(r"\w+", text_b.lower()))

    if not tokens_a or not tokens_b:
        return 0.0

    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)

    return float(intersection / union) if union > 0 else 0.0


def compute_hybrid_similarity(
    fact_a: dict[str, Any],
    fact_b: dict[str, Any],
    vector_similarity: float | None = None,
) -> float:
    """
    Compute a composite similarity score between two facts.
    Blends vector cosine similarity (65%), predicate match (20%), and subject match (15%).
    """
    # 1. Subject match
    subj_sim = token_jaccard_similarity(fact_a.get("subject"), fact_b.get("subject"))

    # 2. Predicate match
    pred_sim = token_jaccard_similarity(fact_a.get("predicate"), fact_b.get("predicate"))

    # 3. Vector similarity
    if vector_similarity is not None:
        v_sim = max(0.0, min(1.0, vector_similarity))
        score = (0.65 * v_sim) + (0.20 * pred_sim) + (0.15 * subj_sim)
    else:
        # Fallback when embeddings are not precomputed
        claim_sim = token_jaccard_similarity(fact_a.get("raw_claim"), fact_b.get("raw_claim"))
        score = (0.50 * claim_sim) + (0.30 * pred_sim) + (0.20 * subj_sim)

    return round(float(min(1.0, max(0.0, score))), 4)
