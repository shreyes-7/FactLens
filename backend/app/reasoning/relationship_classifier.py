"""
Relationship Classifier Engine for FactLens.
Executes hybrid reasoning (deterministic rules + LLM contextual explanation)
to classify candidate fact pairs into CORROBORATES, CONTRADICTS, CONTEXTUAL_DIFFERENCE, RELATED, or UNCERTAIN.
"""

import json
import logging
import re
from typing import Any
from uuid import UUID

from backend.app.providers.llm.base import LLMProvider
from backend.app.reasoning.deterministic import evaluate_deterministic_relationship
from backend.app.reasoning.prompts import (
    RELATIONSHIP_SYSTEM_PROMPT,
    RELATIONSHIP_USER_PROMPT,
)
from backend.app.schemas.relationship import (
    FactRelationshipCreate,
    LLMReasoningOutput,
    RelationshipType,
)

logger = logging.getLogger("factlens.reasoning.classifier")


class RelationshipClassifier:
    """Hybrid relationship classifier combining mathematical heuristics and LLM contextual reasoning."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm_provider = llm_provider

    async def classify_pair(
        self,
        fact_a: dict[str, Any],
        fact_b: dict[str, Any],
        evidence_a: str | None = None,
        evidence_b: str | None = None,
    ) -> FactRelationshipCreate:
        """
        Classify the relationship between two facts.
        Enforces canonical ordering (fact_a_id < fact_b_id) and applies hybrid reasoning.
        """
        id_a_str = str(fact_a.get("id"))
        id_b_str = str(fact_b.get("id"))

        # Enforce canonical ordering: fact_a_id < fact_b_id
        if id_a_str < id_b_str:
            first_fact, second_fact = fact_a, fact_b
            first_ev, second_ev = evidence_a or "", evidence_b or ""
            id_first, id_second = UUID(id_a_str), UUID(id_b_str)
        else:
            first_fact, second_fact = fact_b, fact_a
            first_ev, second_ev = evidence_b or "", evidence_a or ""
            id_first, id_second = UUID(id_b_str), UUID(id_a_str)

        # -------------------------------------------------------------
        # Tier 1: Deterministic Mathematical & Temporal Heuristics
        # -------------------------------------------------------------
        det_type, det_conf, det_reason, det_factors = evaluate_deterministic_relationship(
            first_fact, second_fact
        )

        if det_type is not None and det_conf >= 0.90:
            logger.info(f"Deterministic classification: {det_type.value} (conf={det_conf})")
            return FactRelationshipCreate(
                fact_a_id=id_first,
                fact_b_id=id_second,
                relationship_type=det_type,
                confidence=det_conf,
                reason=det_reason,
                contextual_factors=det_factors,
                reasoning_method="deterministic_rules",
            )

        # -------------------------------------------------------------
        # Tier 2: LLM Contextual Reasoning
        # -------------------------------------------------------------
        if self.llm_provider is not None:
            try:
                user_prompt = RELATIONSHIP_USER_PROMPT.format(
                    subject_a=first_fact.get("subject", ""),
                    predicate_a=first_fact.get("predicate", ""),
                    claim_a=first_fact.get("raw_claim", ""),
                    value_a=first_fact.get("raw_value_text") or first_fact.get("value_numeric") or "",
                    norm_value_a=first_fact.get("normalized_value_numeric") or "N/A",
                    unit_a=first_fact.get("normalized_unit") or first_fact.get("unit") or "",
                    period_a=first_fact.get("period_text") or "N/A",
                    scope_a=first_fact.get("scope") or "N/A",
                    status_a=first_fact.get("status") or "actual",
                    evidence_a=first_ev,
                    subject_b=second_fact.get("subject", ""),
                    predicate_b=second_fact.get("predicate", ""),
                    claim_b=second_fact.get("raw_claim", ""),
                    value_b=second_fact.get("raw_value_text") or second_fact.get("value_numeric") or "",
                    norm_value_b=second_fact.get("normalized_value_numeric") or "N/A",
                    unit_b=second_fact.get("normalized_unit") or second_fact.get("unit") or "",
                    period_b=second_fact.get("period_text") or "N/A",
                    scope_b=second_fact.get("scope") or "N/A",
                    status_b=second_fact.get("status") or "actual",
                    evidence_b=second_ev,
                )

                raw_output = await self.llm_provider.generate(
                    prompt=user_prompt,
                    system_prompt=RELATIONSHIP_SYSTEM_PROMPT,
                )

                # Clean markdown code fences if LLM wrapped in ```json
                cleaned_output = raw_output.strip()
                if cleaned_output.startswith("```json"):
                    cleaned_output = cleaned_output[7:]
                elif cleaned_output.startswith("```"):
                    cleaned_output = cleaned_output[3:]
                if cleaned_output.endswith("```"):
                    cleaned_output = cleaned_output[:-3]

                # Parse JSON
                data = json.loads(cleaned_output.strip())
                parsed = LLMReasoningOutput(**data)

                return FactRelationshipCreate(
                    fact_a_id=id_first,
                    fact_b_id=id_second,
                    relationship_type=parsed.relationship_type,
                    confidence=round(parsed.confidence, 3),
                    reason=parsed.reason,
                    contextual_factors=parsed.contextual_factors,
                    reasoning_method="llm_contextual_reasoning",
                    model=self.llm_provider.model_name,
                )
            except Exception as exc:
                logger.warning(f"LLM contextual reasoning failed or returned invalid schema: {exc}")

        # Fallback when LLM is unavailable or unresolvable
        return FactRelationshipCreate(
            fact_a_id=id_first,
            fact_b_id=id_second,
            relationship_type=RelationshipType.UNCERTAIN,
            confidence=0.5,
            reason="Ambiguous or insufficient evidence to confirm relationship with certainty.",
            contextual_factors={"fallback_reason": "deterministic_and_llm_inconclusive"},
            reasoning_method="fallback_uncertain",
        )
