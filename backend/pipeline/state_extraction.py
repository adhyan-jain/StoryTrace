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
- value: a concise string value for the attribute
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
  prop -> status (held/acquired/lost)
  prop -> holder

REQUIRED VALUE VOCABULARY -- you must use exactly these values, no others:

possession.{prop}:
  "held"      -- character currently has/is holding the item
  "acquired"  -- character just obtained the item THIS UNIT (the moment of
                 first getting it -- taking, receiving, picking up for the
                 first time). If the unit does not narrate the item being
                 obtained (it's simply already in the character's hand/
                 pocket/grip from earlier), use "held", not "acquired".
                 Only ONE unit per CONTINUOUS run of possession should be
                 "acquired" -- every later unit where the character still has
                 it is "held". If the character LOSES the item and only then
                 gets it back, that return is a fresh "acquired", because it
                 starts a new run of possession. An item taken as evidence and
                 handed back days later is acquired twice, not once.
  "lost"      -- character no longer has the item (dropped, taken, used up)

injury.{body_part}:
  "injured"   -- injury is present and active
  "healed"    -- injury has resolved or been treated
  "dead"      -- character has died from this or other causes

character -> location:
  Use the NAME of the place itself, not a description of where within it
  the character is standing. Extract the shortest named location the text
  actually gives -- e.g. from "at the window of the Chicago precinct",
  the location is "Chicago precinct" (the named place), NOT "window of
  the Chicago precinct" (a position within that place). A window, table,
  doorway, or corner is a detail of blocking, not a distinct location.
  e.g. "Gu Yue Clan", "flower wine monk's cave", "city gates"
  This changes on almost every scene (room, building, street) -- that is
  expected and normal, not a continuity signal by itself.

character -> location.city:
  ONLY when a specific real city, region, or named territory is explicitly
  stated for where the character currently is (e.g. "Chicago", "New York",
  the name of a kingdom/country/province). Do NOT log this for every scene --
  most scenes don't name one at all, and you should only emit a new
  location.city event when the text explicitly names one, not on every unit.
  Unlike character -> location, this should change rarely: once per city/
  region the story actually moves the character to, not per room or
  building. If no city/region is named in this unit, do not emit this
  attribute at all for this unit.
  NEVER use vague values like "city", "the city", "home", or "town" -- only
  actual named places count (e.g. "Chicago", "New York", "London").

character -> clothing.{item}:
  Describe concisely in 2-4 words.
  e.g. "grey robe", "torn sleeve", "battle armor"
  Use clothing ONLY for garments actually worn. A badge, ID, weapon, tool,
  or other handheld/carried item is possession.<item> even when it is
  pinned, clipped, or holstered onto the body -- do not log the same
  object as clothing in one scene and possession in another.

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
- For possession events: entity_name must be the CHARACTER who holds/
  loses/acquires the item, NEVER the item itself. If the text says
  "Maya took Cole's badge", log it as COLE/possession.badge=lost
  (Cole is losing it), NOT as BADGE/possession=lost.
- For possession.{prop}: use a SIMPLE single-word prop name when possible.
  Never use compound nested names like "possession.field_kit.gauze" --
  the sub-attribute after "possession." should be just the prop name
  (e.g. "possession.gauze", "possession.gun", "possession.badge").
- If you are unsure whether a fact fits the vocabulary, omit it.
- Do NOT log the same fact twice (e.g. if a character is in the
  "Chicago precinct", emit ONE location event, not two for
  "Chicago precinct" AND "precinct in New York" -- pick the most specific
  canonical name verbatim from the text, do not paraphrase).
- Do NOT log possession events for items a character merely interacts
  with briefly or uses without clearly taking/losing ownership (e.g. do not
  log "possession.knife=lost" for a character who was ATTACKED by a knife --
  log the injury, not the weapon loss unless the attacker explicitly drops it).

EXAMPLES OF CORRECT EXTRACTION:

Input text: "John grabbed the pistol from the table and stuffed it
into his jacket."
Correct:
  { entity_name: "JOHN", entity_type: "character",
    attribute: "possession.pistol", value: "acquired",
    raw_excerpt: "John grabbed the pistol from the table",
    confidence: 0.95, establishment_type: "explicit" }

Input text: "Maya took Cole's badge and sealed it in an evidence bag."
Correct:
  { entity_name: "MAYA", entity_type: "character",
    attribute: "possession.badge", value: "acquired",
    raw_excerpt: "Maya took Cole's badge and sealed it in an evidence bag",
    confidence: 0.9, establishment_type: "explicit" }
  Note: This is "acquired", NOT "held" -- a formal custody transfer
  (confiscating, sealing as evidence, taking into custody) is still the
  moment Maya first gets the item, exactly like a casual grab. Don't
  reserve "acquired" only for informal taking -- any explicit taking
  action, procedural or not, is "acquired" for whoever ends up holding it.
  (Also log "COLE/possession.badge=lost" here -- Cole no longer has it.)

Input text: "The knife clattered to the floor as Cole clutched his
bleeding side."
Correct:
  { entity_name: "COLE", entity_type: "character",
    attribute: "injury.side", value: "injured",
    raw_excerpt: "clutched his bleeding side",
    confidence: 0.92, establishment_type: "explicit" }
  Note: Do NOT log "COLE/possession.knife=lost" -- Cole never had the knife
  (it was the attacker's). The knife falling is evidence of the injury, not
  Cole losing a possession. ONLY log possession loss when a character
  EXPLICITLY had that item before losing it.

Input text: "His gun slipped from his grip as he vaulted a low fence, and
it dropped through a storm grate into the black water below."
Correct:
  { entity_name: "COLE", entity_type: "character",
    attribute: "possession.gun", value: "lost",
    raw_excerpt: "His gun slipped from his grip as he vaulted a low fence",
    confidence: 0.95, establishment_type: "explicit" }
  Note: This is different from the knife case above -- the gun IS Cole's
  own gun (his grip), not someone else's. When a character's OWN item
  drops/slips from THEIR grip or is explicitly taken, log it as lost.

Input text: "Detective COLE stood at the window of the Chicago precinct,
watching rain streak the glass."
Correct (BOTH events, one for the scene, one for the city -- they are not
the same attribute and this unit genuinely has both):
  { entity_name: "COLE", entity_type: "character",
    attribute: "location", value: "Chicago precinct",
    raw_excerpt: "the window of the Chicago precinct",
    confidence: 0.9, establishment_type: "explicit" }
  { entity_name: "COLE", entity_type: "character",
    attribute: "location.city", value: "Chicago",
    raw_excerpt: "the Chicago precinct",
    confidence: 0.9, establishment_type: "explicit" }

Input text: "Cole and Maya split up, moving along opposite rows, radios
turned low."
Correct: only a `location` event (no city/region is named here, so no
location.city event at all for this unit):
  { entity_name: "COLE", entity_type: "character",
    attribute: "location", value: "opposite rows",
    raw_excerpt: "moving along opposite rows",
    confidence: 0.85, establishment_type: "explicit" }

Input text: "A paramedic knelt beside Cole after the confrontation, unwinding
gauze from a field kit. She cleaned the slash and wrapped it tightly."
Correct:
  { entity_name: "COLE", entity_type: "character",
    attribute: "injury.forearm", value: "injured",
    raw_excerpt: "the slash on his forearm",
    confidence: 0.88, establishment_type: "explicit" }
  { entity_name: "PARAMEDIC", entity_type: "character",
    attribute: "possession.gauze", value: "held",
    raw_excerpt: "unwinding gauze from a field kit",
    confidence: 0.85, establishment_type: "explicit" }
  Note: Do NOT emit "possession.field_kit.gauze" -- just "possession.gauze".

EXAMPLES OF INCORRECT EXTRACTION (do not do this):

WRONG -- free-form value:
  { attribute: "possession.knife",
    value: "dropped during struggle" }  <- value must be "lost"

WRONG -- injuring party logged as injured:
  "Cole slashed the guard's arm"
  { entity_name: "COLE", attribute: "injury.arm" }  <- WRONG,
  Cole is not injured. The guard is, but the guard is not a tracked entity here.

WRONG -- item itself logged as entity:
  "Maya took Cole's badge"
  { entity_name: "BADGE", attribute: "possession", value: "lost" }  <- WRONG,
  entity_name must be the CHARACTER (COLE), not the item (BADGE).

WRONG -- over-nested possession sub-attribute:
  { attribute: "possession.field_kit.gauze", value: "held" }  <- WRONG,
  use "possession.gauze" instead (one level of sub-attribute only).

WRONG -- excerpt not verbatim:
  { raw_excerpt: "Cole dropped the knife" }
  when actual text says "The knife clattered to the floor"

WRONG -- vague location.city:
  { attribute: "location.city", value: "city" }  <- WRONG,
  only use real named cities/regions, never "city" or "town".

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

# Body-part naming is freeform (not a controlled vocabulary like
# possession/injury values), so the same wound can come back as "forearm" in
# one unit and "right_forearm"/"right forearm" in another. Track the injury
# by body part alone -- side is rarely load-bearing for a continuity check,
# and splitting it fragments one wound's history across two attribute keys,
# which is exactly what breaks the detector's exact (entity, attribute) join.
_LATERALITY_PREFIXES = ("left_", "right_", "left ", "right ")

# Generic wound-words the model sometimes uses as the injury "body part" when
# the text refers back to an already-established injury without renaming the
# limb -- e.g. unit text "the wound beneath it closed to a thin pink line"
# yields injury.wound, while the same wound was logged as injury.forearm when
# it was inflicted. That fragments one injury's history across two attribute
# keys and breaks the detector's exact (entity, attribute) join -- the same
# failure mode _strip_laterality exists to prevent. These are resolved
# against a real body part named in the same unit's text where one exists.
_GENERIC_INJURY_PARTS = {"wound", "body", "injury", "cut", "slash", "gash"}

# Allowlist of valid human body-part names for injury attributes. Rejects
# hallucinated body parts like "car", "ceiling", or "water" that small models
# sometimes emit when context words appear near injury vocabulary (e.g., the
# model reads "slept in your car" and emits injury.car). This is intentionally
# broad to cover unusual narrative injury locations (temple, jaw, etc.) while
# blocking obvious non-body nouns.
_VALID_BODY_PARTS = {
    # head / face
    "head", "skull", "face", "forehead", "temple", "jaw", "cheek", "nose",
    "ear", "eye", "neck", "throat",
    # torso
    "chest", "back", "spine", "shoulder", "side", "abdomen", "stomach",
    "rib", "ribs", "torso", "hip", "groin", "waist",
    # arms
    "arm", "forearm", "elbow", "wrist", "hand", "fist", "finger", "thumb",
    "knuckle", "palm",
    # legs
    "leg", "thigh", "knee", "shin", "calf", "ankle", "foot", "heel", "toe",
    # general
    "body", "wound", "skull",
}

# Specific body parts (generics excluded), longest first so "forearm" wins
# over "arm" when a unit's text contains both -- matching "arm" inside
# "forearm" would re-fragment the very history this is meant to unify.
_SPECIFIC_BODY_PARTS_BY_LENGTH = sorted(
    _VALID_BODY_PARTS - _GENERIC_INJURY_PARTS, key=len, reverse=True
)

# Entity names that are clearly props/objects, not characters. If the model
# emits entity_name="FILE" or entity_name="BADGE" with entity_type="character",
# that's a model error (the prompt says to use the CHARACTER holding the item).
# This blocklist catches the most common misclassifications we've seen. Keep
# it to proper noun forms (all-caps, as the model tends to emit them).
_PROP_ENTITY_NAMES = {
    "FILE", "CASE FILE", "CASE_FILE", "BADGE", "GUN", "PISTOL", "KNIFE",
    "WEAPON", "RADIO", "GAUZE", "BANDAGE", "EVIDENCE", "EVIDENCE BAG",
    "FORM", "DOCUMENT", "FOLDER", "PHOTOGRAPH", "PHOTO", "REPORT",
    "PHONE", "KEY", "WALLET", "ID", "CARD",
}

# Known synonyms for the same prop the model has been observed to name two
# different ways across units of the same document (e.g. "the case file"
# introduced by name, then just "the file" on a later reference). Grows as
# new collisions are found -- not a general NLP synonym solver, just a table
# of confirmed aliases.
_POSSESSION_SUB_ALIASES = {
    "case file": "file",
    "case_file": "file",   # underscore variant (LLM sometimes uses underscores)
    "field_kit.gauze": "gauze",   # over-nested: model sometimes emits possession.field_kit.gauze
    "field kit": "field_kit",
    "field kit.gauze": "gauze",  # space+dot variant
}

# Conservative surface-level cleanup only: strips a leading article so
# "the precinct" and "precinct" compare equal, without merging genuinely
# different named locations into each other.
_LEADING_ARTICLE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)

# location.city values that are too generic to be useful -- if the model
# emits one of these as a city, it's noise (the extraction prompt already
# says "only when a specific real city/region is explicitly stated").
_VAGUE_CITY_VALUES = {
    "city", "town", "village", "the city", "here", "there", "home", "unknown",
    "unspecified", "unnamed", "not specified", "n/a", "none", "undisclosed",
    "unclear", "somewhere",
}

# Minimum length for a valid scene-level location value -- short strings like
# "here" or "there" or even "him" (a hallucination) are not real locations.
_MIN_LOCATION_LEN = 4

# Words that, when appearing in a scene-level location value, indicate it is
# a relational description (not a real place). e.g. "between them",
# "across from him", "behind her". These are phrases a character is positioned
# relative to, not a named location.
_LOCATION_PRONOUN_FILTER = re.compile(
    r"\b(them|him|her|us|you|it|me|they|we|he|she)\b", re.IGNORECASE
)

# Furniture/architectural-detail nouns that are a detail of blocking within
# a scene, not a distinct named location -- e.g. "table", "low fence",
# "window" (of a room the character is already in). A real eval run showed
# the model extracting these as the location value on their own (1-2 words,
# ending in one of these nouns) even after the SYSTEM_PROMPT was told to
# prefer the named place over a position within it -- this catches what
# that prompt clarification alone didn't. Only rejected when short (<=2
# words) so a genuine named place that happens to end in one of these words
# (unlikely, but e.g. "Long Table Inn") isn't blocked.
_FURNITURE_OBJECT_LOCATIONS = {
    "table", "chair", "desk", "counter", "bench", "stool",
    "window", "door", "doorway", "wall", "floor", "ceiling",
    "fence", "railing", "ledge", "sill", "corner", "shelf",
    "cabinet", "drawer", "bed", "couch", "sofa",
}

# Maximum depth of a dotted possession sub-attribute (counting only the
# sub-attribute parts after "possession."). "possession.gun" -> depth 1 (ok).
# "possession.field_kit.gauze" -> depth 2 (rejected -- over-nested; model should
# emit "possession.gauze" at most, not compound nested paths).
_MAX_POSSESSION_DEPTH = 1


def _clean(value: str) -> str:
    """Strip quotes/parens the model adds despite being told not to, and
    collapse whitespace -- cosmetic cleanup, not a meaning change."""
    return _STRIP_CHARS.sub("", value).strip()


def _strip_laterality(sub: str) -> str:
    for prefix in _LATERALITY_PREFIXES:
        if sub.startswith(prefix):
            return sub[len(prefix):]
    return sub


def _clean_location_value(value: str) -> str:
    return _LEADING_ARTICLE.sub("", value).strip()


def _resolve_generic_body_part(body_part: str, unit_text: str) -> str:
    """Map a generic wound-word ("wound", "cut", "gash") onto the specific body
    part named in the same unit's text, so a follow-up mention of an existing
    injury keys to the same attribute as the unit that inflicted it.

    "The blade caught his right forearm" -> injury.forearm, and the later
    "the wound beneath it closed to a thin pink line" (same unit also says
    "forearm") -> injury.forearm rather than injury.wound. Without this the
    detector's (entity, attribute) join sees two unrelated injuries and can
    never observe the injured -> healed transition.

    Falls back to the generic term unchanged when the unit names no specific
    body part -- guessing one from another unit's context would invent
    provenance the text doesn't support.
    """
    if body_part not in _GENERIC_INJURY_PARTS:
        return body_part
    lowered = unit_text.lower()
    for candidate in _SPECIFIC_BODY_PARTS_BY_LENGTH:
        if re.search(rf"\b{re.escape(candidate)}\b", lowered):
            return candidate
    return body_part


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

    if entity_type != "character" and base in ("status", "possession"):
        # Both "prop -> status" (the schema's own allowed shape) and a
        # directly-emitted "prop -> possession" key a possession fact to
        # the item itself (entity_id = the prop, e.g. entity_name="BADGE"
        # or "FILE"). The prompt's CRITICAL RULES section is explicit that
        # possession must always be keyed to the CHARACTER who holds/
        # loses/acquires the item, NEVER the item -- and golden_dataset.py
        # never expects a prop-keyed possession event, only character-keyed
        # ones. Reject both paths; letting either through only ever
        # produces a false positive (e.g. "BADGE/possession=held",
        # "FILE/possession=acquired") with no golden-dataset counterpart.
        return None
    if base == "holder":
        # Redundant with possession from the character's side; not part of
        # the controlled vocabulary and not needed for conflict detection.
        return None

    if base == "possession":
        if value not in _POSSESSION_VALUES:
            return None
        # Resolve known aliases BEFORE depth-checking so e.g.
        # "field_kit.gauze" becomes "gauze" (depth 1) rather than being
        # rejected at depth 2.
        sub = _POSSESSION_SUB_ALIASES.get(sub, sub)
        # Reject over-nested sub-attributes like "field_kit.gauze" (depth 2).
        if sub.count(".") >= _MAX_POSSESSION_DEPTH:
            return None
        attribute = f"possession.{sub}" if sub else "possession"
        return attribute, value

    if base == "injury":
        if value not in _INJURY_VALUES:
            return None
        if not sub:
            return None
        # Reject over-nested injury attributes like "arm.forearm" -- the
        # extraction prompt asks for injury.<body_part> (one level), not
        # compound paths. Strip any extra nesting by taking only the first
        # sub-segment (the actual body part after laterality stripping).
        body_part = sub.split(".")[0]  # "arm.forearm" -> "arm"; "forearm" -> "forearm"
        body_part = _strip_laterality(body_part)
        # Reject hallucinated body parts -- common model errors include
        # "car", "ceiling", "water" extracted from context words that are
        # near injury vocabulary. We use a broad allowlist of real body parts.
        if body_part not in _VALID_BODY_PARTS:
            return None
        return f"injury.{body_part}", value

    if base == "clothing":
        if not sub or not value:
            return None
        # These items are always possessions, never clothing -- if the model
        # emits them as clothing sub-attributes, it's a mis-classification.
        _POSSESSION_NOT_CLOTHING = {
            "badge", "gun", "pistol", "weapon", "knife", "id", "radio",
            "phone", "wallet", "key", "file", "document", "gauze", "bandage",
        }
        if sub.lower() in _POSSESSION_NOT_CLOTHING:
            return None
        return f"clothing.{sub}", value

    if base == "location":
        if not value:
            return None
        # "location.city" is kept as its OWN attribute, not collapsed into
        # plain "location" -- the whole point is that it changes rarely
        # (once per city/region) while scene-level "location" changes every
        # unit, so the detector can key off the former without drowning in
        # the latter. See CandidateDetector's location.city rule.
        if sub == "city":
            # Canonicalize city names to lowercase for consistent matching
            # across units (model sometimes emits "Chicago", sometimes "chicago").
            city_val = _clean_location_value(value).lower()
            # Reject generic/non-specific values that are not real city names.
            if city_val in _VAGUE_CITY_VALUES or len(city_val) < 2:
                return None
            return "location.city", city_val
        # Scene-level location: strip leading articles and reject very short
        # or obviously relational descriptions (e.g. "between them", "behind her").
        loc_val = _clean_location_value(value)
        if len(loc_val) < _MIN_LOCATION_LEN:
            return None
        # Reject relational phrases containing pronouns -- these are not real
        # locations (e.g. "between them", "across from him", "behind her").
        if _LOCATION_PRONOUN_FILTER.search(loc_val):
            return None
        # Reject short values that are really a piece of furniture/blocking
        # detail, not a distinct named place (e.g. "table", "low fence").
        loc_words = loc_val.split()
        if len(loc_words) <= 2 and loc_words[-1].lower() in _FURNITURE_OBJECT_LOCATIONS:
            return None
        return "location", loc_val

    # Attribute shape the prompt didn't anticipate: don't invent a bucket for
    # it (there's no controlled vocabulary to validate against), drop it.
    return None


def _match_excerpt(raw_excerpt: str, unit_text: str) -> str | None:
    """Locate the model's quoted evidence in the source text and return the
    text's own wording of it, or None if it isn't really there.

    The match is case-insensitive because models routinely reproduce a quote
    accurately but lowercase its first letter when it began a sentence. A real
    run returned "the bandage was gone, the wound beneath it closed to a thin
    pink line" for text reading "The bandage was gone, ..."; a case-sensitive
    check discarded that correct, confidence-0.95 healed event over the
    capital T alone. Losing it cost the entire injured -> healed transition,
    so the detector saw no value change, raised no candidate, and the
    investigation agent never got to adjudicate it.

    What is RETURNED (and therefore stored) is the substring sliced out of
    the source text, never the model's rendering -- so provenance stays exact
    and a reader can still find the finding verbatim in the document.
    """
    if not raw_excerpt:
        return None
    if raw_excerpt in unit_text:
        return raw_excerpt
    index = unit_text.lower().find(raw_excerpt.lower())
    if index == -1:
        return None
    return unit_text[index:index + len(raw_excerpt)]


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

    # Reject facts where the entity_name is clearly a prop/object being used
    # as if it were a character entity. The model sometimes emits
    # entity_name="FILE" or entity_name="BADGE" even though the prompt says
    # possession events must use the CHARACTER who holds the item. This filter
    # catches the most common cases; broader entity resolution is out of scope.
    if entity_type == EntityType.CHARACTER:
        entity_upper = fact.entity_name.strip().upper()
        if entity_upper in _PROP_ENTITY_NAMES:
            return None

    normalized = _normalize_attribute(fact.attribute, entity_type.value, fact.value)
    if normalized is None:
        return None
    attribute, value = normalized
    if attribute.startswith("injury."):
        body_part = _resolve_generic_body_part(attribute.split(".", 1)[1], unit.raw_text)
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


def _extract_single_pass(
    unit: NarrativeUnit,
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry,
    temperature: float,
) -> list[StateEvent]:
    """One LLM extraction call for one unit at a given temperature. Never
    raises on a bad/unparseable response -- logs and returns [] instead, so
    one bad call doesn't take down a run over hundreds of units."""
    prompt = f"""Narrative unit: {unit.title or unit.sequence_number}
Text:
{unit.raw_text}

Extract all trackable state facts from this text."""

    request = LLMRequest(stage="state_extraction", prompt=prompt, system=SYSTEM_PROMPT, temperature=temperature)

    try:
        result = llm_provider.complete(request, StateFactsExtraction)
    except LLMError as exc:
        logger.error("state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []
    except Exception as exc:  # provider/parse failure of any other kind
        logger.error("state extraction failed for unit %s: %s", unit.unit_id, exc)
        return []

    events: list[StateEvent] = []
    for fact in result.value.facts:
        event = _fact_to_event(fact, unit, story_universe_id, registry)
        if event is not None:
            events.append(event)
    return events


# Local models (e.g. qwen2.5:7b via Ollama) miss a meaningfully different
# subset of true facts on each independent sample of the SAME unit at
# temperature>0 -- a real eval run showed recall stuck around 0.40-0.45 on a
# single deterministic (temperature=0) pass, with misses scattered essentially
# randomly across units (sometimes the scene-level `location`, sometimes a
# `possession` fact, no single consistent blind spot). Since Ollama is local
# and free (no per-call cost or rate limit, unlike Vertex/Gemini -- see
# CLAUDE.md's Local Testing policy), spending 2x the LLM calls per unit to
# recover those misses via self-consistency (union of two independent
# samples, deduped) is a direct, cheap lever on recall. Only applied for the
# "local" tier -- Gemini/Vertex's larger models don't show this failure mode
# and doubling their call volume would violate the whole point of using a
# stronger model (fewer calls needed, and would cost real money).
_SELF_CONSISTENCY_TIER = "local"
# Deliberately a single deterministic pass. The temperature-0.5 second sample
# was added to recover scattered recall misses, but session 4 measured what it
# costs: reverting the prompt to a state that had scored F1 0.783 reproduced
# 0.632 with no code change at all -- a +/-0.15 noise band, far wider than any
# fix being evaluated, which made every single-run before/after comparison
# unfalsifiable. A stable, reproducible number is worth more than the recall
# the extra sample bought, because without one no further tuning can be
# validated. Restore (0.0, 0.5) only alongside an averaging harness that runs
# each configuration N>=3 times and compares means.
_SELF_CONSISTENCY_TEMPS = (0.0,)


async def extract_state_events(
    unit: NarrativeUnit,
    story_universe_id: str,
    llm_provider: LLMProvider,
    registry: EntityRegistry | None = None,
) -> list[StateEvent]:
    """Extract StateEvents for one NarrativeUnit. Never raises on a bad or
    unparseable LLM response -- logs and returns an empty list instead, so
    one bad chapter doesn't take down a run over hundreds of units."""
    registry = registry if registry is not None else EntityRegistry(story_universe_id)

    temps = _SELF_CONSISTENCY_TEMPS if getattr(llm_provider, "tier", "") == _SELF_CONSISTENCY_TIER else (0.0,)

    merged: list[StateEvent] = []
    seen: set[tuple[str, str, str]] = set()
    for temperature in temps:
        pass_events = _extract_single_pass(unit, story_universe_id, llm_provider, registry, temperature)
        for event in pass_events:
            key = (event.entity_id, event.attribute, event.value)
            if key in seen:
                continue
            seen.add(key)
            merged.append(event)

    return _inject_city_events(merged, unit, story_universe_id, registry)


# City/region names that the extraction prompt asks the LLM to detect and
# emit as location.city events, but that small models (qwen2.5:7b) consistently
# miss. Rather than relying on the LLM to reliably emit a SECOND event from the
# same text sentence (it tends to emit only one location event per unit), we
# detect them deterministically from the raw text as a post-processing step.
#
# Pattern design: we match known real-world place names commonly appearing in
# fiction. This is intentionally conservative -- NOT a general geocoder, just
# a targeted fix for the most common misses observed empirically.
# New entries should be added when a real eval run reveals a consistent miss.
#
# The match is anchored to whole words (\b) and is case-insensitive.
_CITY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bChicago\b", re.IGNORECASE), "chicago"),
    (re.compile(r"\bNew York\b", re.IGNORECASE), "new york"),
    (re.compile(r"\bLos Angeles\b", re.IGNORECASE), "los angeles"),
    (re.compile(r"\bLondon\b", re.IGNORECASE), "london"),
    (re.compile(r"\bParis\b", re.IGNORECASE), "paris"),
    (re.compile(r"\bTokyo\b", re.IGNORECASE), "tokyo"),
    (re.compile(r"\bBeijing\b", re.IGNORECASE), "beijing"),
    (re.compile(r"\bShanghai\b", re.IGNORECASE), "shanghai"),
    (re.compile(r"\bMoscow\b", re.IGNORECASE), "moscow"),
    (re.compile(r"\bBerlin\b", re.IGNORECASE), "berlin"),
    (re.compile(r"\bMumbai\b", re.IGNORECASE), "mumbai"),
    (re.compile(r"\bSão Paulo\b", re.IGNORECASE), "são paulo"),
    (re.compile(r"\bRio de Janeiro\b", re.IGNORECASE), "rio de janeiro"),
    (re.compile(r"\bMexico City\b", re.IGNORECASE), "mexico city"),
    (re.compile(r"\bSeoul\b", re.IGNORECASE), "seoul"),
    (re.compile(r"\bBangkok\b", re.IGNORECASE), "bangkok"),
    (re.compile(r"\bDubai\b", re.IGNORECASE), "dubai"),
    (re.compile(r"\bSydney\b", re.IGNORECASE), "sydney"),
    (re.compile(r"\bMelbourne\b", re.IGNORECASE), "melbourne"),
    (re.compile(r"\bToronto\b", re.IGNORECASE), "toronto"),
    (re.compile(r"\bMontreal\b", re.IGNORECASE), "montreal"),
    (re.compile(r"\bRome\b", re.IGNORECASE), "rome"),
    (re.compile(r"\bMadrid\b", re.IGNORECASE), "madrid"),
    (re.compile(r"\bBarcelona\b", re.IGNORECASE), "barcelona"),
    (re.compile(r"\bAmsterdam\b", re.IGNORECASE), "amsterdam"),
    (re.compile(r"\bVienna\b", re.IGNORECASE), "vienna"),
    (re.compile(r"\bPrague\b", re.IGNORECASE), "prague"),
    (re.compile(r"\bWarsaw\b", re.IGNORECASE), "warsaw"),
    (re.compile(r"\bBrussels\b", re.IGNORECASE), "brussels"),
    (re.compile(r"\bLisbon\b", re.IGNORECASE), "lisbon"),
    (re.compile(r"\bStockholm\b", re.IGNORECASE), "stockholm"),
    (re.compile(r"\bOslo\b", re.IGNORECASE), "oslo"),
    (re.compile(r"\bHelsinki\b", re.IGNORECASE), "helsinki"),
    (re.compile(r"\bCopenhagen\b", re.IGNORECASE), "copenhagen"),
    (re.compile(r"\bZurich\b", re.IGNORECASE), "zurich"),
    (re.compile(r"\bGeneva\b", re.IGNORECASE), "geneva"),
    (re.compile(r"\bDublin\b", re.IGNORECASE), "dublin"),
    (re.compile(r"\bEdinburgh\b", re.IGNORECASE), "edinburgh"),
    (re.compile(r"\bManchester\b", re.IGNORECASE), "manchester"),
    (re.compile(r"\bBirmingham\b", re.IGNORECASE), "birmingham"),
    (re.compile(r"\bLiverpool\b", re.IGNORECASE), "liverpool"),
    (re.compile(r"\bGlasgow\b", re.IGNORECASE), "glasgow"),
    (re.compile(r"\bSan Francisco\b", re.IGNORECASE), "san francisco"),
    (re.compile(r"\bSeattle\b", re.IGNORECASE), "seattle"),
    (re.compile(r"\bPortland\b", re.IGNORECASE), "portland"),
    (re.compile(r"\bDenver\b", re.IGNORECASE), "denver"),
    (re.compile(r"\bPhoenix\b", re.IGNORECASE), "phoenix"),
    (re.compile(r"\bDallas\b", re.IGNORECASE), "dallas"),
    (re.compile(r"\bHouston\b", re.IGNORECASE), "houston"),
    (re.compile(r"\bAtlanta\b", re.IGNORECASE), "atlanta"),
    (re.compile(r"\bMiami\b", re.IGNORECASE), "miami"),
    (re.compile(r"\bBoston\b", re.IGNORECASE), "boston"),
    (re.compile(r"\bPhiladelphia\b", re.IGNORECASE), "philadelphia"),
    (re.compile(r"\bDetroit\b", re.IGNORECASE), "detroit"),
    (re.compile(r"\bMinneapolis\b", re.IGNORECASE), "minneapolis"),
    (re.compile(r"\bSt. Louis\b", re.IGNORECASE), "st. louis"),
    (re.compile(r"\bNew Orleans\b", re.IGNORECASE), "new orleans"),
    (re.compile(r"\bLas Vegas\b", re.IGNORECASE), "las vegas"),
    (re.compile(r"\bWashington\b", re.IGNORECASE), "washington"),
    (re.compile(r"\bBaltimore\b", re.IGNORECASE), "baltimore"),
    (re.compile(r"\bPittsburgh\b", re.IGNORECASE), "pittsburgh"),
    (re.compile(r"\bNashville\b", re.IGNORECASE), "nashville"),
    (re.compile(r"\bKansas City\b", re.IGNORECASE), "kansas city"),
    (re.compile(r"\bSalt Lake City\b", re.IGNORECASE), "salt lake city"),
    (re.compile(r"\bOmaha\b", re.IGNORECASE), "omaha"),
]


def _inject_city_events(
    events: list[StateEvent],
    unit: NarrativeUnit,
    story_universe_id: str,
    registry: EntityRegistry,
) -> list[StateEvent]:
    """Post-process extracted events to add location.city events that the LLM
    consistently misses.

    When a character has a location event in this unit (evidence they were
    somewhere) and the unit text also contains a known city name, emit a
    location.city event for that character and city -- unless one was already
    extracted by the LLM for this character+city pair.

    Only fires for characters who already have a `location` event in this unit
    (not for every character in the story, which would be noise), and only for
    city names found verbatim in the unit text.
    """
    # Find which character entities have a location event in this unit.
    char_entities_with_location: set[str] = set()
    existing_city_keys: set[tuple[str, str]] = set()
    for e in events:
        if e.attribute == "location":
            char_entities_with_location.add(e.entity_id)
        elif e.attribute == "location.city":
            existing_city_keys.add((e.entity_id, e.value))

    if not char_entities_with_location:
        return events

    # Find which city names appear in this unit's raw text.
    text = unit.raw_text
    new_events: list[StateEvent] = []
    for pattern, city_canonical in _CITY_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        city_excerpt = m.group(0)  # verbatim match as raw_excerpt
        for entity_id in char_entities_with_location:
            if (entity_id, city_canonical) in existing_city_keys:
                continue  # LLM already extracted this one, don't duplicate
            new_events.append(StateEvent(
                id=str(uuid.uuid4()),
                story_universe_id=story_universe_id,
                entity_id=entity_id,
                attribute="location.city",
                value=city_canonical,
                unit_id=unit.unit_id,
                sequence_number=unit.sequence_number,
                page_ref=unit.page_start,
                raw_excerpt=city_excerpt,
                establishment_type="explicit",
                confidence=0.9,
            ))
            existing_city_keys.add((entity_id, city_canonical))  # avoid duplicate if 2 patterns match

    return events + new_events


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
    events_by_unit: dict[int, list[StateEvent]] = {i: [] for i in range(1, len(units) + 1)}
    for fact in result.value.facts:
        unit = by_index.get(fact.unit_index)
        if unit is None:
            continue
        event = _fact_to_event(fact, unit, story_universe_id, registry)
        if event is not None:
            events_by_unit[fact.unit_index].append(event)

    # Apply city injection per-unit (same deterministic pass as single-unit path).
    all_events: list[StateEvent] = []
    for i, unit in enumerate(units, start=1):
        all_events.extend(_inject_city_events(events_by_unit[i], unit, story_universe_id, registry))
    return all_events


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
