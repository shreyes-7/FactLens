"""
Cross-Document Comparison Service ("What Changed?").
Performs fast, deterministic multi-document comparison across 2 to 5 PDFs.
Identifies metric progression (increased, decreased, unchanged, added, not found, context changed)
without making any LLM calls or regenerating embeddings.
Zero LLM calls. Sub-50ms execution.
"""

from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field
from psycopg2.extras import RealDictCursor
from backend.app.config import Settings, get_settings
from backend.app.database import get_db_connection


class DocumentRef(BaseModel):
    id: str
    filename: str
    total_facts: int = 0


class MetricValuePoint(BaseModel):
    document_id: str
    document_filename: str
    fact_id: str
    raw_value: str
    normalized_value: float | None = None
    unit: str | None = None
    period: str | None = None
    scope: str | None = None
    page_number: int | None = None
    evidence_quote: str | None = None


class MetricComparisonItem(BaseModel):
    metric_id: str
    subject: str
    predicate: str
    unit: str | None = None
    scope: str | None = None
    category: str = Field(
        ...,
        description="INCREASED, DECREASED, UNCHANGED, ADDED, NOT_FOUND, or CONTEXT_CHANGED"
    )
    change_label: str
    variance_percent: float | None = None
    absolute_difference: float | None = None
    # In 2-doc comparisons: doc_a vs doc_b
    doc_a_value: MetricValuePoint | None = None
    doc_b_value: MetricValuePoint | None = None
    # In 3-5 doc comparisons: timeline points across all selected docs
    timeline: list[MetricValuePoint | None] = []


class DocumentComparisonSummary(BaseModel):
    total_metrics_compared: int
    increased_count: int
    decreased_count: int
    unchanged_count: int
    added_count: int
    not_found_count: int
    context_changed_count: int


class DocumentComparisonResponse(BaseModel):
    documents: list[DocumentRef]
    summary: DocumentComparisonSummary
    metrics: list[MetricComparisonItem]


class DocumentComparisonService:
    """
    Analyzes what changed between documents using already extracted and normalized database facts.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()

    @staticmethod
    def _normalize_key(text: str | None) -> str:
        if not text:
            return ""
        return " ".join(str(text).strip().lower().split())

    def compare_documents(
        self,
        document_ids: list[str],
    ) -> DocumentComparisonResponse:
        """
        Compare 2 to 5 documents deterministically.
        """
        if not document_ids or len(document_ids) < 2:
            raise ValueError("At least two documents must be selected for comparison.")

        # Cap comparison to 5 documents for clean UX and performance
        doc_ids_clean = [str(d) for d in document_ids[:5]]

        conn = get_db_connection(self.settings)
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Fetch document metadata
                cur.execute(
                    """
                    SELECT d.id, d.filename, COUNT(f.id) AS total_facts
                    FROM public.documents d
                    LEFT JOIN public.facts f ON f.document_id = d.id
                    WHERE d.id = ANY(%s::uuid[])
                    GROUP BY d.id, d.filename;
                    """,
                    (doc_ids_clean,),
                )
                doc_rows = {str(r["id"]): r for r in cur.fetchall()}

                # Preserve order of user's selection
                ordered_docs: list[DocumentRef] = []
                for d_id in doc_ids_clean:
                    if d_id in doc_rows:
                        ordered_docs.append(
                            DocumentRef(
                                id=d_id,
                                filename=doc_rows[d_id]["filename"],
                                total_facts=int(doc_rows[d_id]["total_facts"] or 0),
                            )
                        )

                if len(ordered_docs) < 2:
                    raise ValueError("Could not find at least two valid documents in database.")

                # 2. Fetch facts and evidence for the selected documents
                cur.execute(
                    """
                    SELECT 
                        f.id AS fact_id,
                        f.document_id,
                        f.subject,
                        f.predicate,
                        f.raw_claim AS raw_value,
                        COALESCE(f.normalized_value_numeric, f.value_numeric) AS normalized_value,
                        COALESCE(f.normalized_unit, f.unit) AS unit,
                        f.period_text AS period,
                        f.scope,
                        COALESCE(dp.pdf_page_number, (f.metadata->>'page_number')::int, 1) AS page_number,
                        (SELECT quote FROM public.evidence e WHERE e.fact_id = f.id ORDER BY e.created_at ASC LIMIT 1) AS evidence_quote
                    FROM public.facts f
                    LEFT JOIN LATERAL (
                        SELECT dp.pdf_page_number 
                        FROM public.evidence e
                        JOIN public.document_pages dp ON e.page_id = dp.id
                        WHERE e.fact_id = f.id 
                        LIMIT 1
                    ) dp ON true
                    WHERE f.document_id = ANY(%s::uuid[])
                    ORDER BY f.created_at ASC;
                    """,
                    (doc_ids_clean,),
                )
                fact_rows = cur.fetchall()

        finally:
            conn.close()

        # 3. Group facts by (canonical_subject, canonical_predicate)
        # map: key -> { doc_id: MetricValuePoint }
        doc_map = {d.id: d.filename for d in ordered_docs}
        metrics_index: dict[tuple[str, str], dict[str, MetricValuePoint]] = {}

        for row in fact_rows:
            d_id = str(row["document_id"])
            subj_clean = self._normalize_key(row["subject"])
            pred_clean = self._normalize_key(row["predicate"])

            if not pred_clean:
                continue

            # Grouping key
            key = (subj_clean, pred_clean)
            if key not in metrics_index:
                metrics_index[key] = {}

            # Don't overwrite if a non-null numeric value is already present
            if d_id in metrics_index[key] and metrics_index[key][d_id].normalized_value is not None:
                continue

            point = MetricValuePoint(
                document_id=d_id,
                document_filename=doc_map.get(d_id, "Unknown"),
                fact_id=str(row["fact_id"]),
                raw_value=str(row["raw_value"] or ""),
                normalized_value=float(row["normalized_value"]) if row["normalized_value"] is not None else None,
                unit=row["unit"],
                period=row["period"],
                scope=row["scope"],
                page_number=int(row["page_number"]) if row["page_number"] is not None else None,
                evidence_quote=row["evidence_quote"],
            )
            metrics_index[key][d_id] = point

        # 4. Compare across documents
        doc_a_id = ordered_docs[0].id
        doc_b_id = ordered_docs[1].id

        compared_items: list[MetricComparisonItem] = []
        inc_count = 0
        dec_count = 0
        unch_count = 0
        add_count = 0
        not_found_count = 0
        ctx_changed_count = 0

        metric_counter = 0
        for (subj, pred), doc_points in metrics_index.items():
            metric_counter += 1
            metric_id = f"metric-{metric_counter}"

            point_a = doc_points.get(doc_a_id)
            point_b = doc_points.get(doc_b_id)

            # Timeline for multi-document view
            timeline: list[MetricValuePoint | None] = [doc_points.get(d.id) for d in ordered_docs]

            # At least one document has this metric
            sample = point_a or point_b or next(iter(doc_points.values()))
            subject_disp = sample.document_filename if not subj else sample.raw_value and len(subj) < 40 and subj.title() or "Metric"
            predicate_disp = pred.title() if pred else "Claim"
            unit_disp = sample.unit
            scope_disp = sample.scope

            category = "UNCHANGED"
            change_label = "No change"
            variance_pct: float | None = None
            abs_diff: float | None = None

            if point_a and not point_b:
                category = "NOT_FOUND"
                change_label = f"Not found in {ordered_docs[1].filename}"
                not_found_count += 1

            elif not point_a and point_b:
                category = "ADDED"
                change_label = f"Added in {ordered_docs[1].filename}"
                add_count += 1

            elif point_a and point_b:
                val_a = point_a.normalized_value
                val_b = point_b.normalized_value

                # Scope difference
                scope_a = self._normalize_key(point_a.scope)
                scope_b = self._normalize_key(point_b.scope)
                if scope_a and scope_b and scope_a != scope_b:
                    category = "CONTEXT_CHANGED"
                    change_label = f"Scope changed: {scope_a.title()} → {scope_b.title()}"
                    ctx_changed_count += 1

                # Numeric delta calculation
                elif val_a is not None and val_b is not None:
                    abs_diff = round(val_b - val_a, 4)
                    if abs(val_a) > 1e-9:
                        variance_pct = round(((val_b - val_a) / abs(val_a)) * 100, 2)
                    elif abs(val_b) > 1e-9:
                        variance_pct = 100.0
                    else:
                        variance_pct = 0.0

                    if variance_pct > 0.5:
                        category = "INCREASED"
                        change_label = f"+{variance_pct:.2f}% ↑"
                        inc_count += 1
                    elif variance_pct < -0.5:
                        category = "DECREASED"
                        change_label = f"{variance_pct:.2f}% ↓"
                        dec_count += 1
                    else:
                        category = "UNCHANGED"
                        change_label = "0.00% (No change)"
                        unch_count += 1

                else:
                    # Semantic string comparison
                    raw_a = self._normalize_key(point_a.raw_value)
                    raw_b = self._normalize_key(point_b.raw_value)
                    if raw_a == raw_b:
                        category = "UNCHANGED"
                        change_label = "Identical claim"
                        unch_count += 1
                    else:
                        category = "CONTEXT_CHANGED"
                        change_label = "Qualitative claim variance"
                        ctx_changed_count += 1

            compared_items.append(
                MetricComparisonItem(
                    metric_id=metric_id,
                    subject=subject_disp,
                    predicate=predicate_disp,
                    unit=unit_disp,
                    scope=scope_disp,
                    category=category,
                    change_label=change_label,
                    variance_percent=variance_pct,
                    absolute_difference=abs_diff,
                    doc_a_value=point_a,
                    doc_b_value=point_b,
                    timeline=timeline,
                )
            )

        # Sort: items present in both first (increased, decreased, context_changed, unchanged), then added, then not_found
        sort_priority = {
            "INCREASED": 1,
            "DECREASED": 2,
            "CONTEXT_CHANGED": 3,
            "UNCHANGED": 4,
            "ADDED": 5,
            "NOT_FOUND": 6,
        }
        compared_items.sort(
            key=lambda item: (
                sort_priority.get(item.category, 99),
                -abs(item.variance_percent or 0.0),
                item.predicate,
            )
        )

        summary = DocumentComparisonSummary(
            total_metrics_compared=len(compared_items),
            increased_count=inc_count,
            decreased_count=dec_count,
            unchanged_count=unch_count,
            added_count=add_count,
            not_found_count=not_found_count,
            context_changed_count=ctx_changed_count,
        )

        return DocumentComparisonResponse(
            documents=ordered_docs,
            summary=summary,
            metrics=compared_items,
        )
