"""Enriched Scene & State Extractor for StoryTrace V2.

Performs structured extraction of hierarchical spatial state, temporal anchors,
co-presence lists, possession transitions, physical states, and narrative events
from screenplay narrative units.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from typing import List, Optional, Tuple, Any

from backend.ingestion.models import NarrativeUnit
from backend.llm.base import LLMProvider, LLMRequest, LLMResult, LLMError, LLMParseError
from backend.pipeline.entity_resolution import EntityRegistry
from backend.v2.story_state.models import (
    SceneExtractionV2, StateEventV2, SceneCoPresence,
    RawStateFactV2, RawNarrativeEventV2, RawSceneMetadataV2,
    TemporalAnchor, HierarchicalLocationV2
)
from backend.v2.pipeline.prompts import (
    ENRICHED_EXTRACTION_SYSTEM_PROMPT, ENRICHED_EXTRACTION_USER_PROMPT
)
from backend.v2.clickhouse.client import ClickHouseClientV2

logger = logging.getLogger(__name__)


def _match_verbatim_excerpt(excerpt: str, source_text: str) -> Optional[str]:
    """Verify and ground excerpt in source text with exact, normalized, or case-insensitive matching."""
    if not excerpt or not source_text:
        return None
    cleaned_excerpt = excerpt.strip()
    if cleaned_excerpt in source_text:
        return cleaned_excerpt
    
    # Try normalized whitespace search
    norm_source = re.sub(r"\s+", " ", source_text).lower()
    norm_excerpt = re.sub(r"\s+", " ", cleaned_excerpt).lower()
    if norm_excerpt in norm_source:
        return cleaned_excerpt
    
    # Try case-insensitive substring
    pattern = re.compile(re.escape(cleaned_excerpt), re.IGNORECASE)
    match = pattern.search(source_text)
    if match:
        return match.group(0)
        
    return None


class EnrichedExtractor:
    def __init__(self, provider: LLMProvider, client: Optional[ClickHouseClientV2] = None):
        self.provider = provider
        self.client = client

    def extract_scene(
        self,
        unit: NarrativeUnit,
        entity_registry: Optional[EntityRegistry] = None
    ) -> SceneExtractionV2:
        """Call LLM to extract structured scene metadata, state facts, and events."""
        user_prompt = ENRICHED_EXTRACTION_USER_PROMPT.format(
            unit_id=unit.unit_id,
            sequence_number=unit.sequence_number,
            title=unit.title,
            text=unit.raw_text
        )
        
        request = LLMRequest(
            stage="v2_state_extraction",
            prompt=user_prompt,
            system=ENRICHED_EXTRACTION_SYSTEM_PROMPT,
            temperature=0.0
        )
        
        try:
            result = self.provider.complete(request, SceneExtractionV2)
            extraction = result.value
        except (LLMError, LLMParseError, Exception) as exc:
            logger.warning(
                "Enriched extraction failed/parse error for unit %s: %s -- falling back to minimal metadata",
                unit.unit_id, exc
            )
            setting_type = "INT" if "INT" in unit.title.upper() else ("EXT" if "EXT" in unit.title.upper() else "")
            extraction = SceneExtractionV2(
                scene_metadata=RawSceneMetadataV2(
                    setting_type=setting_type,
                    environment=unit.title,
                    time_anchor=TemporalAnchor.CONTINUOUS
                )
            )

        # Ground excerpts
        extraction = self._validate_and_ground_facts(extraction, unit.raw_text)
        return extraction

    def _validate_and_ground_facts(
        self,
        extraction: SceneExtractionV2,
        source_text: str
    ) -> SceneExtractionV2:
        """Filter out or correct facts that lack verifiable textual grounding."""
        grounded_facts: List[RawStateFactV2] = []
        for fact in extraction.state_facts:
            grounded_span = _match_verbatim_excerpt(fact.raw_excerpt, source_text)
            if grounded_span:
                fact.raw_excerpt = grounded_span
                grounded_facts.append(fact)
            else:
                # If short excerpt not directly matched, check if fact value words exist in source text
                words = [w for w in re.split(r"\W+", fact.raw_excerpt) if len(w) > 3]
                if words and any(w.lower() in source_text.lower() for w in words):
                    grounded_facts.append(fact)
                else:
                    logger.debug("Rejecting ungrounded state fact: %s=%s ('%s')", fact.attribute, fact.value, fact.raw_excerpt)

        extraction.state_facts = grounded_facts
        return extraction

    def to_clickhouse_records(
        self,
        extraction: SceneExtractionV2,
        unit: NarrativeUnit,
        story_universe_id: str,
        entity_registry: Optional[EntityRegistry] = None
    ) -> Tuple[List[StateEventV2], SceneCoPresence]:
        """Convert validated extraction into ClickHouse state_events_v2 and scene_co_presence_v2 records."""
        state_events: List[StateEventV2] = []
        meta = extraction.scene_metadata
        
        # 1. Build SceneCoPresence
        co_entity_ids: List[str] = []
        for name in meta.present_entity_names:
            if entity_registry:
                entity = entity_registry.get_or_create(story_universe_id, name, "character")
                co_entity_ids.append(entity.id)
            else:
                co_entity_ids.append(name.strip().lower().replace(" ", "_"))

        co_presence = SceneCoPresence(
            id=str(uuid.uuid4()),
            story_universe_id=story_universe_id,
            unit_id=unit.unit_id,
            sequence_number=unit.sequence_number,
            entity_ids=co_entity_ids,
            setting_type=meta.setting_type,
            environment=meta.environment,
            specific_room=meta.specific_room,
            time_of_day=meta.time_of_day,
            time_anchor=meta.time_anchor.value if isinstance(meta.time_anchor, TemporalAnchor) else str(meta.time_anchor)
        )

        # 2. Build StateEventV2 records
        for fact in extraction.state_facts:
            if entity_registry:
                entity = entity_registry.get_or_create(
                    story_universe_id, fact.entity_name, fact.entity_type
                )
                entity_id = entity.id
            else:
                entity_id = f"{fact.entity_type}_{fact.entity_name.strip().lower().replace(' ', '_')}"

            rel_entity_id = ""
            if fact.related_entity_name:
                if entity_registry:
                    rel_entity = entity_registry.get_or_create(
                        story_universe_id, fact.related_entity_name, "character"
                    )
                    rel_entity_id = rel_entity.id
                else:
                    rel_entity_id = fact.related_entity_name.strip().lower().replace(" ", "_")

            hier_setting = meta.setting_type
            hier_env = meta.environment
            hier_room = meta.specific_room
            hier_city = meta.city_region

            if fact.spatial_details:
                if fact.spatial_details.setting_type:
                    hier_setting = fact.spatial_details.setting_type
                if fact.spatial_details.environment:
                    hier_env = fact.spatial_details.environment
                if fact.spatial_details.specific_room:
                    hier_room = fact.spatial_details.specific_room
                if fact.spatial_details.city_region:
                    hier_city = fact.spatial_details.city_region

            event = StateEventV2(
                id=str(uuid.uuid4()),
                story_universe_id=story_universe_id,
                entity_id=entity_id,
                attribute=fact.attribute,
                value=fact.value,
                unit_id=unit.unit_id,
                sequence_number=unit.sequence_number,
                page_ref=unit.page_start,
                raw_excerpt=fact.raw_excerpt,
                establishment_type=fact.establishment_type,
                confidence=fact.confidence,
                hier_setting_type=hier_setting,
                hier_environment=hier_env,
                hier_specific_room=hier_room,
                hier_city_region=hier_city,
                time_anchor=meta.time_anchor.value if isinstance(meta.time_anchor, TemporalAnchor) else str(meta.time_anchor),
                related_entity_id=rel_entity_id
            )
            state_events.append(event)

        return state_events, co_presence

    def extract_and_store_scene(
        self,
        unit: NarrativeUnit,
        story_universe_id: str,
        entity_registry: Optional[EntityRegistry] = None
    ) -> Tuple[SceneExtractionV2, List[StateEventV2], SceneCoPresence]:
        """Convenience method to extract and store in ClickHouse."""
        extraction = self.extract_scene(unit, entity_registry)
        state_events, co_presence = self.to_clickhouse_records(
            extraction, unit, story_universe_id, entity_registry
        )
        if self.client:
            self.client.insert_state_events_v2(state_events)
            self.client.insert_scene_co_presence_v2([co_presence])
        return extraction, state_events, co_presence
