"""
Tests for DocumentComparisonService ("What Changed?").
"""

import pytest
from backend.app.services.comparison_service import DocumentComparisonService
from backend.app.config import get_settings
from backend.app.database import get_db_connection


def test_comparison_requires_at_least_two_docs():
    svc = DocumentComparisonService()
    with pytest.raises(ValueError, match="At least two documents"):
        svc.compare_documents(["doc-1"])


def test_comparison_live_delhivery_documents():
    conn = get_db_connection(get_settings())
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM documents LIMIT 2;")
            rows = cur.fetchall()
    finally:
        conn.close()

    if len(rows) < 2:
        pytest.skip("Not enough documents in database to test live comparison.")

    doc_ids = [str(r[0]) for r in rows]
    svc = DocumentComparisonService()
    resp = svc.compare_documents(doc_ids)

    assert len(resp.documents) >= 2
    assert resp.summary.total_metrics_compared >= 0
    assert isinstance(resp.metrics, list)

    for item in resp.metrics:
        assert item.category in (
            "INCREASED",
            "DECREASED",
            "UNCHANGED",
            "ADDED",
            "NOT_FOUND",
            "CONTEXT_CHANGED",
        )
        if item.variance_percent is not None:
            # Check percentage math
            if item.doc_a_value and item.doc_b_value:
                va = item.doc_a_value.normalized_value
                vb = item.doc_b_value.normalized_value
                if va and vb and abs(va) > 1e-9:
                    expected = round(((vb - va) / abs(va)) * 100, 2)
                    assert abs(item.variance_percent - expected) < 0.05
