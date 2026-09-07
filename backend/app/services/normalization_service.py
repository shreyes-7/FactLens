"""
FactLens Normalization Service.
Coordinates batch normalization and re-normalization of facts in Supabase PostgreSQL.
"""

import logging
from typing import Any

from backend.app.config import Settings, get_settings
from backend.app.database import get_all_facts, update_fact_normalization
from backend.app.normalization.normalizer import FactNormalizer

logger = logging.getLogger("factlens.normalization")


class NormalizationService:
    """Service to normalize and update facts stored in the knowledge layer."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.normalizer = FactNormalizer()

    def normalize_stored_facts(self, dataset_id: str | None = None) -> dict[str, Any]:
        """
        Scan all (or dataset-specific) facts in database, compute normalized
        attributes, and update the rows in Supabase.
        """
        facts = get_all_facts(dataset_id=dataset_id, settings=self.settings)
        logger.info(f"Normalizing {len(facts)} facts from database...")

        updated_count = 0
        for f in facts:
            fact_id = str(f["id"])
            norm_fact = self.normalizer.normalize_dict(f)

            update_fact_normalization(
                fact_id=fact_id,
                normalized_value_numeric=norm_fact.get("normalized_value_numeric"),
                normalized_unit=norm_fact.get("normalized_unit"),
                period_start=norm_fact.get("period_start"),
                period_end=norm_fact.get("period_end"),
                settings=self.settings,
            )
            updated_count += 1

        logger.info(f"Successfully normalized {updated_count} facts.")
        return {
            "total_facts": len(facts),
            "updated_count": updated_count,
        }
