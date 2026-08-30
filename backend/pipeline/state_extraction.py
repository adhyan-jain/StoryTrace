"""Gemini-backed state-fact extraction for a single NarrativeUnit.

Takes a NarrativeUnit, asks the LLM (via the existing LLMProvider
abstraction) what trackable story-state facts it contains, and turns the
result into StateEvents ready for `ClickHouseClient.insert_state_events`.
"""

from __future__ import annotations

import logging
import uuid
from enum import Enum

from pydantic import BaseModel, Field

from backend.clickhouse.client import ClickHouseClient
from backend.ingestion.models import NarrativeUnit
from backend.llm.base import LLMError, LLMProvider, LLMRequest
from backend.pipeline.entity_resolution import EntityRegistry
from backend.story_state.models import StateEvent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a narrative continuity analyst. Extract all trackable story state facts
from the provided scene or chapter text.

Return a JSON array of state facts. Each fact must have:
- entity_name: the canonical name of the character, prop, or location
- entity_type: "character", "prop", or "location"
- attribute: one of the allowed attribute patterns listed below
- value: a concise string value for the attribute
- raw_excerpt: the exact sentence or phrase from the text that establishes this fact
- confidence: 0.0 to 1.0 -- how explicitly the text states this fact
- establishment_type: "explicit" (directly stated), "implicit" (clearly implied),
  or "inferred" (reasonable inference)

Allowed attribute patterns:
  character -> location
  character -> injury.<body_part>
  character -> clothing.<item>
  character -> possession.<prop_name>
  prop -> status (held/acquired/lost)
  prop -> holder

Rules:
- Return ONLY a valid JSON array. No preamble, no markdown fences, no explanation.
- If uncertain about a fact, omit it. Do not guess.
- Only extract facts directly supported by the text.
- confidence < 0.7 should use establishment_type "inferred" or be omitted.
- raw_excerpt must be a verbatim substring of the input text, not a paraphrase.
"""


class EntityType(str, Enum):
    CHARACTER = "character"
    PROP = "prop"
    LOCATION = "location"


class EstablishmentType(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT = "implicit"
    INFERRED = "inferred"


class StateFact(BaseModel):
    entity_name: str
    entity_type: str
    attribute: str
    value: str
    raw_excerpt: str
    confidence: float = Field(ge=0.0, le=1.0)
    establishment_type: str


class StateFactsExtraction(BaseModel):
    """Wraps the array the prompt asks for in an object, because the shared
    LLMProvider.complete() plumbing (schema_instructions / extract_json in
    backend/llm/base.py) is built around a single validated Pydantic object,
    not a bare top-level JSON array. `facts` is that array."""

    facts: list[StateFact] = Field(default_factory=list)


# storytrace.state_events.attribute is a ClickHouse Enum8 with exactly these
# five values (backend/clickhouse/schema.sql) -- unlike the richer dotted
# patterns the prompt asks for (e.g. "injury.left_arm"), so every fact must be
# folded into one of these buckets before it can be inserted.
_ALLOWED_ATTRIBUTES = {"presence", "location", "possession", "injury", "clothing"}
_MIN_CONFIDENCE = 0.6


def _map_attribute(raw_attribute: str, value: str) -> tuple[str, str]:
    """Map a free-form 'category.detail' attribute (e.g. 'injury.left_arm',
    'clothing.jacket', prop 'status'/'holder') down to the schema's five
    Enum8 buckets, folding the detail into `value` rather than dropping it."""
    base, _, sub = raw_attribute.strip().lower().partition(".")

    if base == "holder":
        return "possession", f"{value} (holder)"
    if base == "status":
        return "possession", value
    if base in _ALLOWED_ATTRIBUTES:
        return (base, f"{value} ({sub})") if sub else (base, value)

    # Attribute shape the prompt didn't anticipate: keep the fact (it was
    # still confidently extracted) under the closest catch-all bucket rather
    # than silently discarding it.
    return "presence", value


async def extract_state_events(
    unit: NarrativeUnit,
    story_universe_id: str,
    llm_provider: LLMProvider,
) -> list[StateEvent]:
    """Extract StateEvents for one NarrativeUnit. Never raises on a bad or
    unparseable LLM response -- logs and returns an empty list instead, so
    one bad chapter doesn't take down a run over hundreds of units."""

    prompt = f"""Narrative unit: {unit.title or unit.sequence_number}
Text:
{unit.raw_text}

Extract all trackable state facts from this text."""

    request = LLMRequest(stage="state_extraction", prompt=prompt, system=SYSTEM_PROMPT)

    try:
        result = llm_provider.complete(request, StateFactsExtraction)
    except LLMError as exc:
        logger.error("state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []
    except Exception as exc:  # provider/parse failure of any other kind
        logger.error("state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []

    registry = EntityRegistry(story_universe_id)
    events: list[StateEvent] = []

    for fact in result.value.facts:
        if fact.confidence < _MIN_CONFIDENCE:
            continue
        # Hallucination check: raw_excerpt must be evidence that actually
        # appears in the source text, not a paraphrase (provenance is not
        # optional -- see CLAUDE.md).
        if not fact.raw_excerpt or fact.raw_excerpt not in unit.raw_text:
            continue
        try:
            entity_type = EntityType(fact.entity_type.strip().lower())
        except ValueError:
            continue
        try:
            establishment_type = EstablishmentType(fact.establishment_type.strip().lower())
        except ValueError:
            continue

        attribute, value = _map_attribute(fact.attribute, fact.value)
        entity_id = registry.resolve(fact.entity_name, entity_type.value)

        events.append(
            StateEvent(
                id=str(uuid.uuid4()),
                story_universe_id=story_universe_id,
                entity_id=entity_id,
                attribute=attribute,
                value=value,
                unit_id=unit.unit_id,
                sequence_number=unit.sequence_number,
                page_ref=unit.page_start,
                raw_excerpt=fact.raw_excerpt,
                establishment_type=establishment_type.value,
                confidence=fact.confidence,
            )
        )

    return events


async def write_state_events(events: list[StateEvent], ch_client: ClickHouseClient) -> None:
    """Batch insert into storytrace.state_events. Database errors propagate --
    a silently dropped insert would corrupt the continuity record."""
    if not events:
        return
    ch_client.insert_state_events(events)
