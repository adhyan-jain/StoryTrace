"""Condition C (ablation): unconstrained-vocabulary state extraction.

Same shape and grounding checks as backend/pipeline/state_extraction.py, but
the LLM is free to write any string it wants into the `value` field -- the
REQUIRED VALUE VOCABULARY section and its worked examples are removed from
the prompt, and the possession/injury value allowlists are not enforced
during normalization.

This isolates what the controlled vocabulary (Condition A) buys: with
free-form values, backend/candidate_detection/detector.py's SQL
lagInFrame(...) join can only match an exact repeated string across units,
so semantically-identical-but-differently-worded values (e.g. "no longer has
it" vs "lost it" vs "dropped") fail to collapse into the same detected
transition -- expected to sharply reduce candidates_generated relative to
Condition A, which is the ablation's point.

Reuses backend/pipeline/state_extraction.py's private helpers directly
(hallucination/grounding checks, entity resolution, city injection) rather
than reimplementing them, so both conditions share identical logic for
everything except the one deliberately-varied piece: value vocabulary
enforcement. Does not modify state_extraction.py itself.
"""

from __future__ import annotations

import logging
import re
import uuid

from backend.ingestion.models import NarrativeUnit
from backend.llm.base import LLMError, LLMProvider, LLMRequest
from backend.pipeline.entity_resolution import EntityRegistry
from backend.pipeline.state_extraction import (
    EntityType,
    EstablishmentType,
    StateFact,
    StateFactsExtraction,
    _clean,
    _clean_location_value,
    _FURNITURE_OBJECT_LOCATIONS,
    _inject_city_events,
    _injury_grounded,
    _location_grounded,
    _LOCATION_PRONOUN_FILTER,
    _match_excerpt,
    _MIN_CONFIDENCE,
    _MIN_LOCATION_LEN,
    _MAX_POSSESSION_DEPTH,
    _resolve_generic_body_part,
    _strip_laterality,
    _VALID_BODY_PARTS,
    _VAGUE_CITY_VALUES,
    _PROP_ENTITY_NAMES,
    _POSSESSION_SUB_ALIASES,
)
from backend.story_state.models import StateEvent

logger = logging.getLogger(__name__)

# Same task framing as SYSTEM_PROMPT, minus the "REQUIRED VALUE VOCABULARY"
# section and its worked examples -- attribute *shape* (possession.<prop>,
# injury.<body_part>, location, location.city, clothing.<item>) is kept,
# since that's the structural join key the SQL detector needs to compare
# anything at all; only the *value* a fact is allowed to take is freed.
UNCONSTRAINED_SYSTEM_PROMPT = """
You are a narrative continuity analyst. Extract all trackable story state facts
from the provided scene or chapter text.

Many units contain SEVERAL distinct facts at once (e.g. a location, an
injury, AND a possession change, all in one paragraph) -- do not stop
scanning after finding the first one or two. Before finalizing your
answer, check the text separately against EACH of these four categories:
location, injury, possession, clothing -- a unit that mentions a place,
a wound, and an item changing hands should produce facts for all three,
not just whichever you noticed first.

Return a JSON array of state facts. Each fact must have:
- entity_name: the canonical name of the character, prop, or location
- entity_type: "character", "prop", or "location"
- attribute: one of the allowed attribute patterns listed below
- value: a concise string describing the current state for this attribute,
  in your own words -- there is no fixed list of allowed values, describe
  the state as precisely as the text supports
- raw_excerpt: the exact sentence or phrase from the text that establishes this fact
- confidence: 0.0 to 1.0 -- how explicitly the text states this fact
- establishment_type: "explicit" (directly stated), "implicit" (clearly implied),
  or "inferred" (reasonable inference)

Allowed attribute patterns:
  character -> location
  character -> location.city
  character -> injury.<body_part>
  character -> clothing.<item>
  character -> possession.<prop_name>
  prop -> status
  prop -> holder

Rules:
- Return ONLY a valid JSON array. No preamble, no markdown fences, no explanation.
- If uncertain about a fact, omit it. Do not guess.
- Only extract facts directly supported by the text.
- confidence < 0.7 should use establishment_type "inferred" or be omitted.
- raw_excerpt must be a verbatim substring of the input text, not a paraphrase.
- For injury events: entity_name must be the character RECEIVING the injury.
- For possession events: entity_name must be the CHARACTER who holds/loses/
  acquires the item, NEVER the item itself.
"""


def _normalize_attribute_unconstrained(raw_attribute: str, entity_type: str, raw_value: str) -> tuple[str, str] | None:
    """Same attribute-shape parsing as state_extraction._normalize_attribute,
    but WITHOUT checking `value` against a controlled vocabulary -- any
    non-empty, cleaned string is accepted for possession/injury values. This
    is the one deliberate difference this whole module exists to isolate."""
    base, _, sub = raw_attribute.strip().lower().partition(".")
    value = _clean(raw_value)
    if not value:
        return None

    if entity_type != "character" and base in ("status", "possession"):
        return None
    if base == "holder":
        return None

    if base == "possession":
        sub = _POSSESSION_SUB_ALIASES.get(sub, sub)
        if sub.count(".") >= _MAX_POSSESSION_DEPTH:
            return None
        attribute = f"possession.{sub}" if sub else "possession"
        return attribute, value

    if base == "injury":
        if not sub:
            return None
        body_part = sub.split(".")[0]
        body_part = _strip_laterality(body_part)
        if body_part not in _VALID_BODY_PARTS:
            return None
        return f"injury.{body_part}", value

    if base == "clothing":
        if not sub:
            return None
        _POSSESSION_NOT_CLOTHING = {
            "badge", "gun", "pistol", "weapon", "knife", "id", "radio",
            "phone", "wallet", "key", "file", "document", "gauze", "bandage",
        }
        if sub.lower() in _POSSESSION_NOT_CLOTHING:
            return None
        return f"clothing.{sub}", value

    if base == "location":
        if sub == "city":
            city_val = _clean_location_value(value).lower()
            if city_val in _VAGUE_CITY_VALUES or len(city_val) < 2:
                return None
            return "location.city", city_val
        loc_val = _clean_location_value(value)
        if len(loc_val) < _MIN_LOCATION_LEN:
            return None
        if _LOCATION_PRONOUN_FILTER.search(loc_val):
            return None
        loc_words = loc_val.split()
        if len(loc_words) <= 2 and loc_words[-1].lower() in _FURNITURE_OBJECT_LOCATIONS:
            return None
        return "location", loc_val

    return None


def _fact_to_event_unconstrained(
    fact: StateFact,
    unit: NarrativeUnit,
    story_universe_id: str,
    registry: EntityRegistry,
) -> StateEvent | None:
    if fact.confidence < _MIN_CONFIDENCE:
        return None
    excerpt = _match_excerpt(fact.raw_excerpt, unit.raw_text)
    if excerpt is None:
        return None
    try:
        entity_type = EntityType(fact.entity_type.strip().lower())
    except ValueError:
        return None
    try:
        establishment_type = EstablishmentType(fact.establishment_type.strip().lower())
    except ValueError:
        return None

    if entity_type == EntityType.CHARACTER:
        entity_upper = fact.entity_name.strip().upper()
        if entity_upper in _PROP_ENTITY_NAMES:
            return None

    normalized = _normalize_attribute_unconstrained(fact.attribute, entity_type.value, fact.value)
    if normalized is None:
        return None
    attribute, value = normalized
    if attribute in ("location", "location.city"):
        if not _location_grounded(value, excerpt):
            return None
    if attribute.startswith("injury."):
        raw_body_part = attribute.split(".", 1)[1]
        if not _injury_grounded(raw_body_part, excerpt, unit.raw_text):
            return None
        body_part = _resolve_generic_body_part(raw_body_part, unit.raw_text)
        attribute = f"injury.{body_part}"
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
        raw_excerpt=excerpt,
        establishment_type=establishment_type.value,
        confidence=fact.confidence,
    )


async def extract_state_events_unconstrained(
    unit: NarrativeUnit,
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry | None = None,
) -> list[StateEvent]:
    """Unconstrained-vocabulary counterpart to
    state_extraction.extract_state_events, for Condition C. Single
    deterministic pass only (temperature=0) -- self-consistency sampling is
    a Condition-A/local-tier concern orthogonal to this ablation."""
    registry = registry if registry is not None else EntityRegistry(story_universe_id)

    prompt = f"""Narrative unit: {unit.title or unit.sequence_number}
Text:
{unit.raw_text}

Extract all trackable state facts from this text."""

    request = LLMRequest(
        stage="state_extraction_unconstrained",
        prompt=prompt,
        system=UNCONSTRAINED_SYSTEM_PROMPT,
        temperature=0.0,
    )

    try:
        result = llm_provider.complete(request, StateFactsExtraction)
    except LLMError as exc:
        logger.error("unconstrained state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []
    except Exception as exc:
        logger.error("unconstrained state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []

    events: list[StateEvent] = []
    for fact in result.value.facts:
        event = _fact_to_event_unconstrained(fact, unit, story_universe_id, registry)
        if event is not None:
            events.append(event)

    return _inject_city_events(events, unit, story_universe_id, registry)
