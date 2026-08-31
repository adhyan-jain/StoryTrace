"""LLM-backed state-fact extraction for a single NarrativeUnit.

Takes a NarrativeUnit, asks the LLM (via the existing LLMProvider
abstraction) what trackable story-state facts it contains, and turns the
result into StateEvents ready for `ClickHouseClient.insert_state_events`.
"""

from __future__ import annotations

import logging
import re
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

REQUIRED VALUE VOCABULARY -- you must use exactly these values, no others:

possession.{prop}:
  "held"      -- character currently has/is holding the item
  "acquired"  -- character just obtained the item this unit
  "lost"      -- character no longer has the item (dropped, taken, used up)

injury.{body_part}:
  "injured"   -- injury is present and active
  "healed"    -- injury has resolved or been treated
  "dead"      -- character has died from this or other causes

character -> location:
  Use the location name exactly as it appears in the text.
  e.g. "Gu Yue Clan", "flower wine monk's cave", "city gates"

character -> clothing.{item}:
  Describe concisely in 2-4 words.
  e.g. "grey robe", "torn sleeve", "battle armor"

Do NOT use free-form descriptions as values.
Do NOT include quotes, parentheses, or explanations in the value field.
The raw_excerpt field is where you put the supporting evidence text.
The value field must be a single controlled term from the list above,
or a concise noun phrase for location/clothing.

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


_POSSESSION_VALUES = {"held", "acquired", "lost"}
_INJURY_VALUES = {"injured", "healed", "dead"}
_MIN_CONFIDENCE = 0.6
_STRIP_CHARS = re.compile(r'["\'()]')


def _clean(value: str) -> str:
    """Strip quotes/parens the model adds despite being told not to, and
    collapse whitespace -- cosmetic cleanup, not a meaning change."""
    return _STRIP_CHARS.sub("", value).strip()


def _normalize_attribute(raw_attribute: str, entity_type: str, raw_value: str) -> tuple[str, str] | None:
    """Build the full dotted attribute ('possession.gun', 'injury.left_arm',
    'location', 'clothing.jacket') and validate/clean its value against the
    controlled vocabulary. Returns None if the fact doesn't fit any allowed
    shape or (for possession/injury) uses a value outside the fixed set --
    dropping an ambiguous fact is safer than storing an uncontrolled one the
    detector can never match.
    """
    base, _, sub = raw_attribute.strip().lower().partition(".")
    value = _clean(raw_value)

    if base == "status" and entity_type == "prop":
        # prop -> status without a named prop in the attribute path; the
        # entity itself *is* the prop, so possession is keyed by entity, not
        # by a sub-attribute name.
        base = "possession"
        sub = ""
    if base == "holder":
        # Redundant with possession from the character's side; not part of
        # the controlled vocabulary and not needed for conflict detection.
        return None

    if base == "possession":
        if value not in _POSSESSION_VALUES:
            return None
        attribute = f"possession.{sub}" if sub else "possession"
        return attribute, value

    if base == "injury":
        if value not in _INJURY_VALUES:
            return None
        if not sub:
            return None
        return f"injury.{sub}", value

    if base == "clothing":
        if not sub or not value:
            return None
        return f"clothing.{sub}", value

    if base == "location":
        if not value:
            return None
        return "location", value

    # Attribute shape the prompt didn't anticipate: don't invent a bucket for
    # it (there's no controlled vocabulary to validate against), drop it.
    return None


async def extract_state_events(
    unit: NarrativeUnit,
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry | None = None,
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

    registry = registry if registry is not None else EntityRegistry(story_universe_id)
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

        normalized = _normalize_attribute(fact.attribute, entity_type.value, fact.value)
        if normalized is None:
            continue
        attribute, value = normalized
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
