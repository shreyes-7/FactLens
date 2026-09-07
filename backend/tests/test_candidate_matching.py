"""
Unit tests for Candidate Matching (Phase 06).
Tests structured filters, cosine similarity, hybrid scoring, and candidate retrieval.
"""

from datetime import date
from uuid import uuid4
import pytest

from backend.app.matching.candidate_retrieval import CandidateRetriever
from backend.app.matching.filters import (
    check_cross_document,
    check_dataset_boundary,
    check_metric_compatibility,
    check_non_self,
    check_predicate_alignment,
    check_temporal_compatibility,
    is_candidate_pair,
)
from backend.app.matching.similarity import (
    compute_hybrid_similarity,
    cosine_similarity,
    token_jaccard_similarity,
)


def test_check_dataset_boundary():
    ds1 = str(uuid4())
    ds2 = str(uuid4())
    assert check_dataset_boundary({"dataset_id": ds1}, {"dataset_id": ds1}) is True
    assert check_dataset_boundary({"dataset_id": ds1}, {"dataset_id": ds2}) is False
    assert check_dataset_boundary({"dataset_id": ""}, {"dataset_id": ds1}) is False


def test_check_non_self():
    id1 = str(uuid4())
    id2 = str(uuid4())
    assert check_non_self({"id": id1}, {"id": id2}) is True
    assert check_non_self({"id": id1}, {"id": id1}) is False


def test_check_cross_document():
    doc1 = str(uuid4())
    doc2 = str(uuid4())
    assert check_cross_document({"document_id": doc1}, {"document_id": doc2}) is True
    assert check_cross_document({"document_id": doc1}, {"document_id": doc1}) is False


def test_check_temporal_compatibility():
    # 1. Identical range
    f1 = {"period_start": date(2023, 4, 1), "period_end": date(2024, 3, 31)}
    f2 = {"period_start": date(2023, 4, 1), "period_end": date(2024, 3, 31)}
    ok, reason = check_temporal_compatibility(f1, f2)
    assert ok is True
    assert reason == "identical_period_range"

    # 2. Overlapping range (e.g. Q4 within FY24)
    f3 = {"period_start": date(2024, 1, 1), "period_end": date(2024, 3, 31)}
    ok, reason = check_temporal_compatibility(f1, f3)
    assert ok is True
    assert reason == "overlapping_period_range"

    # 3. Disjoint range (e.g. FY23 vs FY24)
    f4 = {"period_start": date(2022, 4, 1), "period_end": date(2023, 3, 31)}
    ok, reason = check_temporal_compatibility(f1, f4)
    assert ok is False
    assert reason == "disjoint_period_range"

    # 4. Text fallback
    f5 = {"period_text": "FY24"}
    f6 = {"period_text": "FY2023-24"}
    ok, _ = check_temporal_compatibility(f5, f6)
    assert ok is True


def test_check_metric_compatibility():
    # Same canonical unit
    assert check_metric_compatibility({"normalized_unit": "INR"}, {"normalized_unit": "INR"})[0] is True
    assert check_metric_compatibility({"normalized_unit": "PERCENT"}, {"normalized_unit": "PERCENT"})[0] is True

    # Incompatible units
    ok, reason = check_metric_compatibility({"normalized_unit": "INR"}, {"normalized_unit": "METRIC_TON"})
    assert ok is False
    assert "incompatible_units" in reason

    # Currencies (compatible for candidate comparison)
    assert check_metric_compatibility({"normalized_unit": "INR"}, {"normalized_unit": "USD"})[0] is True


def test_check_predicate_alignment():
    assert check_predicate_alignment({"predicate": "EBITDA"}, {"predicate": "EBITDA"}) == (True, 1.0)
    aligned, score = check_predicate_alignment(
        {"predicate": "Revenue"}, {"predicate": "Revenue from operations"}
    )
    assert aligned is True
    assert score > 0.0

    aligned, _ = check_predicate_alignment({"predicate": "EBITDA"}, {"predicate": "Net Debt"})
    assert aligned is False


def test_cosine_similarity():
    v1 = [1.0, 0.0, 0.0]
    v2 = [1.0, 0.0, 0.0]
    assert cosine_similarity(v1, v2) == 1.0

    v3 = [0.0, 1.0, 0.0]
    assert cosine_similarity(v1, v3) == 0.0

    # Edge cases
    assert cosine_similarity([], [1.0]) == 0.0
    assert cosine_similarity([0.0, 0.0], [0.0, 0.0]) == 0.0


def test_token_jaccard_similarity():
    assert token_jaccard_similarity("Delhivery Limited", "delhivery limited") == 1.0
    assert token_jaccard_similarity("Delhivery Logistics", "Delhivery Supply Chain") > 0.0
    assert token_jaccard_similarity("Apple Inc", "Microsoft Corp") == 0.0


def test_compute_hybrid_similarity():
    fact_a = {"subject": "Delhivery", "predicate": "EBITDA", "raw_claim": "FY24 EBITDA reached Rs. 127 Cr"}
    fact_b = {"subject": "Delhivery", "predicate": "EBITDA", "raw_claim": "Annual EBITDA was Rs. 127 Cr"}

    score_with_vec = compute_hybrid_similarity(fact_a, fact_b, vector_similarity=0.95)
    assert 0.85 <= score_with_vec <= 1.0

    score_without_vec = compute_hybrid_similarity(fact_a, fact_b)
    assert 0.5 <= score_without_vec <= 1.0


def test_candidate_retriever_ranking_and_canonical_pairs():
    ds_id = str(uuid4())
    doc1 = str(uuid4())
    doc2 = str(uuid4())

    fact1 = {
        "id": "11111111-1111-1111-1111-111111111111",
        "dataset_id": ds_id,
        "document_id": doc1,
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "raw_claim": "FY24 EBITDA is Rs. 127 Cr",
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "embedding": [1.0, 0.0, 0.0],
    }

    fact2 = {
        "id": "22222222-2222-2222-2222-222222222222",
        "dataset_id": ds_id,
        "document_id": doc2,
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "raw_claim": "Full year EBITDA reached Rs. 127 Cr",
        "normalized_unit": "INR",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "embedding": [0.98, 0.02, 0.0],
    }

    fact3_diff_metric = {
        "id": "33333333-3333-3333-3333-333333333333",
        "dataset_id": ds_id,
        "document_id": doc2,
        "subject": "Delhivery",
        "predicate": "Freight Volume",
        "raw_claim": "Carried 1.4 Mn metric tons",
        "normalized_unit": "METRIC_TON",
        "period_start": date(2023, 4, 1),
        "period_end": date(2024, 3, 31),
        "embedding": [0.1, 0.8, 0.1],
    }

    # Test single fact retrieval
    candidates = CandidateRetriever.find_candidates_for_fact(
        query_fact=fact1,
        candidate_pool=[fact1, fact2, fact3_diff_metric],
        min_similarity=0.5,
        require_cross_document=True,
    )
    assert len(candidates) == 1
    assert str(candidates[0].fact_b_id) == fact2["id"]
    assert candidates[0].similarity_score > 0.85
    assert candidates[0].predicate_match is True
    assert candidates[0].temporal_overlap is True

    # Test all pairs discovery (enforcing canonical id_a < id_b ordering)
    all_pairs = CandidateRetriever.find_all_candidate_pairs(
        facts=[fact2, fact1, fact3_diff_metric],
        min_similarity=0.5,
        require_cross_document=True,
    )
    assert len(all_pairs) == 1
    # Canonical ordering: '1111...' < '2222...'
    assert str(all_pairs[0].fact_a_id) == fact1["id"]
    assert str(all_pairs[0].fact_b_id) == fact2["id"]


def test_generate_fact_embedding_text():
    fact = {
        "subject": "Delhivery",
        "predicate": "EBITDA",
        "raw_claim": "FY24 EBITDA reached Rs. 127 Cr",
        "period_text": "FY24",
        "normalized_unit": "INR",
    }
    emb_text = CandidateRetriever.generate_fact_embedding_text(fact)
    assert "Entity: Delhivery" in emb_text
    assert "Metric: EBITDA" in emb_text
    assert "Claim: FY24 EBITDA reached Rs. 127 Cr" in emb_text
    assert "Period: FY24" in emb_text
    assert "Unit: INR" in emb_text

