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

CRITICAL RULES:
- The value field must ONLY contain a term from the lists above
  (or a short noun phrase for location/clothing).
- Do NOT put descriptions, quotes, or explanations in value.
  Descriptions go in raw_excerpt only.
- For injury events: entity_name must be the character RECEIVING
  the injury. If character A injures character B or an object,
  do NOT log an injury event for character A.
  Only log injury for the character who is harmed.
- If you are unsure whether a fact fits the vocabulary, omit it.

EXAMPLES OF CORRECT EXTRACTION:

Input text: "John grabbed the pistol from the table and stuffed it
into his jacket."
Correct:
  { entity_name: "JOHN", entity_type: "character",
    attribute: "possession.pistol", value: "acquired",
    raw_excerpt: "John grabbed the pistol from the table",
    confidence: 0.95, establishment_type: "explicit" }

Input text: "The knife clattered to the floor as Cole clutched his
bleeding side."
Correct:
  { entity_name: "COLE", entity_type: "character",
    attribute: "injury.side", value: "injured",
    raw_excerpt: "clutched his bleeding side",
    confidence: 0.92, establishment_type: "explicit" }
  { entity_name: "COLE", entity_type: "character",
    attribute: "possession.knife", value: "lost",
    raw_excerpt: "The knife clattered to the floor",
    confidence: 0.90, establishment_type: "explicit" }

EXAMPLES OF INCORRECT EXTRACTION (do not do this):

WRONG -- free-form value:
  { attribute: "possession.knife",
    value: "dropped during struggle" }  <- value must be "lost"

WRONG -- injuring party logged as injured:
  "Cole slashed the guard's arm"
  { entity_name: "COLE", attribute: "injury.arm" }  <- WRONG,
  Cole is not injured. The guard is, but the guard is not a tracked entity here.

WRONG -- excerpt not verbatim:
  { raw_excerpt: "Cole dropped the knife" }
  when actual text says "The knife clattered to the floor"

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


class BatchStateFact(StateFact):
    """Same as StateFact, plus which unit in the batch this fact came from --
    the model is given several units in one prompt (see extract_state_events_batch),
    so each fact must say which one it's about. 1-based to match the labels
    ("UNIT 1", "UNIT 2", ...) put in front of each unit's text in the prompt."""

    unit_index: int = Field(ge=1)


class BatchStateFactsExtraction(BaseModel):
    facts: list[BatchStateFact] = Field(default_factory=list)


_BATCH_FORMAT_NOTE = """
You will be given several narrative units in one request, each labeled
"UNIT <n>". Extract facts from ALL of them, and set each fact's unit_index
to the number of the unit it came from (the <n> in "UNIT <n>"). Do not mix
facts across units -- raw_excerpt must be a verbatim substring of THAT
unit's text specifically, not any other unit's.
"""


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


def _fact_to_event(
    fact: StateFact,
    unit: NarrativeUnit,
    story_universe_id: str,
    registry: EntityRegistry,
) -> StateEvent | None:
    """Shared validation/normalization path for one extracted fact against
    the specific unit it's claimed to be about. Used by both the single-unit
    and batched extraction paths so a fact from either goes through the same
    hallucination check, controlled-vocabulary check, and entity resolution."""
    if fact.confidence < _MIN_CONFIDENCE:
        return None
    # Hallucination check: raw_excerpt must be evidence that actually
    # appears in the source text, not a paraphrase (provenance is not
    # optional -- see CLAUDE.md).
    if not fact.raw_excerpt or fact.raw_excerpt not in unit.raw_text:
        return None
    try:
        entity_type = EntityType(fact.entity_type.strip().lower())
    except ValueError:
        return None
    try:
        establishment_type = EstablishmentType(fact.establishment_type.strip().lower())
    except ValueError:
        return None

    normalized = _normalize_attribute(fact.attribute, entity_type.value, fact.value)
    if normalized is None:
        return None
    attribute, value = normalized
    entity_id = registry.resolve(fact.entity_name, entity_type.value)

    return StateEvent(
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
        event = _fact_to_event(fact, unit, story_universe_id, registry)
        if event is not None:
            events.append(event)
    return events


# How many LLM output tokens to budget per unit in a batch call. A real
# 501-chapter run measured 49% of batches (62/126) hitting mid-JSON
# truncation at the old 1500/unit budget, each retriggering a 4x-call
# per-unit fallback -- effectively erasing most of batching's call-count
# win. Raising the ceiling costs nothing extra (billing is per actual
# output token generated, not the budget), so this is set generously
# relative to gemini-2.5-flash's much larger real output cap.
_BATCH_TOKENS_PER_UNIT = 4000


async def extract_state_events_batch(
    units: list[NarrativeUnit],
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry | None = None,
) -> list[StateEvent]:
    """Same extraction as extract_state_events, but for several units in one
    LLM call -- cuts the total call count (and therefore wall-clock time and
    rate-limit pressure) by roughly len(units)x on top of the concurrency
    fan-out in backend/api/main.py's _run_pipeline_job. Falls back to
    per-unit extraction for this batch if the batched call itself fails or
    returns nothing usable, so a batch failure costs the same calls as never
    batching, not more."""
    if not units:
        return []
    if len(units) == 1:
        return await extract_state_events(units[0], story_universe_id, llm_provider, registry)

    registry = registry if registry is not None else EntityRegistry(story_universe_id)

    sections = "\n\n".join(
        f"UNIT {i}:\n{unit.raw_text}" for i, unit in enumerate(units, start=1)
    )
    prompt = f"""{sections}

Extract all trackable state facts from EVERY unit above. Remember to set
each fact's unit_index to the number of the unit it came from."""

    request = LLMRequest(
        stage="state_extraction_batch",
        prompt=prompt,
        system=SYSTEM_PROMPT + _BATCH_FORMAT_NOTE,
        max_tokens=_BATCH_TOKENS_PER_UNIT * len(units),
    )

    try:
        result = llm_provider.complete(request, BatchStateFactsExtraction)
    except LLMError as exc:
        logger.error(
            "batch state extraction failed for units %s: %s -- falling back to per-unit",
            [u.unit_id for u in units], exc,
        )
        return await _extract_units_individually(units, story_universe_id, llm_provider, registry)
    except Exception as exc:  # provider/parse failure of any other kind
        logger.error(
            "batch state extraction failed for units %s: %s -- falling back to per-unit",
            [u.unit_id for u in units], exc,
        )
        return await _extract_units_individually(units, story_universe_id, llm_provider, registry)

    by_index = {i: unit for i, unit in enumerate(units, start=1)}
    events: list[StateEvent] = []
    for fact in result.value.facts:
        unit = by_index.get(fact.unit_index)
        if unit is None:
            continue
        event = _fact_to_event(fact, unit, story_universe_id, registry)
        if event is not None:
            events.append(event)
    return events


async def _extract_units_individually(
    units: list[NarrativeUnit],
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry,
) -> list[StateEvent]:
    events: list[StateEvent] = []
    for unit in units:
        events.extend(await extract_state_events(unit, story_universe_id, llm_provider, registry))
    return events


async def write_state_events(events: list[StateEvent], ch_client: ClickHouseClient) -> None:
    """Batch insert into storytrace.state_events. Database errors propagate --
    a silently dropped insert would corrupt the continuity record."""
    if not events:
        return
    ch_client.insert_state_events(events)
