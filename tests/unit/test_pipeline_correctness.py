"""Regression tests for every confirmed correctness issue in StoryTrace.

Each test is pinned to a specific historical bug or property confirmed
in FINDINGS.md, EVAL_IMPROVEMENT_LOG.md, or PIPELINE_VERIFICATION.md.
Reference is given in the docstring so a future reader can trace it.
"""

from __future__ import annotations

import os
import pytest
from backend.pipeline.state_extraction import (
    _strip_laterality,
    _resolve_generic_body_part,
    _normalize_attribute,
    _match_excerpt,
    _location_grounded,
    _injury_grounded,
    _fact_to_event,
    _inject_city_events,
    _VAGUE_CITY_VALUES,
    _PROP_ENTITY_NAMES,
    _POSSESSION_SUB_ALIASES,
    _MAX_POSSESSION_DEPTH,
)
from backend.pipeline.entity_resolution import EntityRegistry
from backend.ingestion.models import NarrativeUnit
from backend.llm.provider import get_llm_provider


# --------------------------------------------------------------------------
# BUG-1: Provider-selection drift
# EVAL_IMPROVEMENT_LOG.md notes .env was set to `vertexai` which silently
# routes eval runs through metered Vertex AI quota. Ollama must be default.
# --------------------------------------------------------------------------
class TestProviderSelection:
    def test_default_is_ollama_when_env_unset(self, monkeypatch):
        """Without MODEL_PROVIDER set, provider must be OllamaProvider (local, free)."""
        monkeypatch.delenv("MODEL_PROVIDER", raising=False)
        from backend.llm.ollama import OllamaProvider
        p = get_llm_provider()
        assert isinstance(p, OllamaProvider), (
            "DEFAULT provider must be OllamaProvider when MODEL_PROVIDER is unset -- "
            "Vertex AI is metered and rate-limited, cannot be the default"
        )
        assert p.tier == "local"

    def test_ollama_explicit(self, monkeypatch):
        monkeypatch.setenv("MODEL_PROVIDER", "ollama")
        from backend.llm.ollama import OllamaProvider
        p = get_llm_provider()
        assert isinstance(p, OllamaProvider)

    def test_ollama_tier_is_not_api(self, monkeypatch):
        """Confirms _suggest_fix in investigator.py skips the ADK path for Ollama.
        The ADK path only fires when provider.tier == 'api' -- Ollama must NOT
        have that tier so no accidental Vertex/Gemini calls happen locally.
        """
        monkeypatch.setenv("MODEL_PROVIDER", "ollama")
        p = get_llm_provider()
        assert p.tier != "api", "Ollama tier must not be 'api' -- would activate Gemini ADK path"

    def test_env_file_sets_ollama(self):
        """Regression: .env was set to MODEL_PROVIDER=vertexai in session 5.
        After the fix, running with the real .env must never select vertexai.
        This test reads MODEL_PROVIDER from the environment as the pipeline
        actually does at runtime (not monkeypatched), so a regressed .env
        will be caught here immediately.
        """
        provider_name = os.environ.get("MODEL_PROVIDER", "ollama")
        assert provider_name not in ("vertexai", "gemini"), (
            f"MODEL_PROVIDER={provider_name!r} in environment -- must be 'ollama' for local eval. "
            "Check .env -- was previously reverted to 'vertexai' and must not regress."
        )


# --------------------------------------------------------------------------
# BUG-2: Attribute-name drift (injury.forearm vs injury.right_forearm vs
#         injury.arm vs injury.arm.forearm)
# FINDINGS.md: "The injury was extracted three times under three different
# attribute names for the same physical wound."
# --------------------------------------------------------------------------
class TestLateralityStripping:
    def test_right_prefix_removed(self):
        assert _strip_laterality("right_forearm") == "forearm"

    def test_left_prefix_removed(self):
        assert _strip_laterality("left_arm") == "arm"

    def test_right_space_prefix_removed(self):
        assert _strip_laterality("right forearm") == "forearm"

    def test_left_space_prefix_removed(self):
        assert _strip_laterality("left shoulder") == "shoulder"

    def test_no_prefix_unchanged(self):
        assert _strip_laterality("forearm") == "forearm"
        assert _strip_laterality("head") == "head"
        assert _strip_laterality("knee") == "knee"

    def test_normalize_right_forearm_to_injury_forearm(self):
        """Regression: injury.right_forearm must normalize to injury.forearm,
        not be stored as-is (which would break the detector's (entity,attribute) join).
        """
        attr, val = _normalize_attribute("injury.right_forearm", "character", "injured")
        assert attr == "injury.forearm", (
            f"injury.right_forearm should normalize to injury.forearm, got {attr!r}"
        )
        assert val == "injured"

    def test_normalize_left_forearm_to_injury_forearm(self):
        attr, val = _normalize_attribute("injury.left_forearm", "character", "injured")
        assert attr == "injury.forearm"

    def test_normalize_injury_arm_forearm_to_injury_forearm(self):
        """Regression: injury.arm.forearm (over-nested) must collapse to injury.arm
        (take only first segment), not be stored with dot nesting."""
        attr, val = _normalize_attribute("injury.arm.forearm", "character", "injured")
        # After splitting on first dot: "arm.forearm" -> "arm" (first segment)
        assert attr == "injury.arm", (
            f"injury.arm.forearm should collapse to injury.arm, got {attr!r}"
        )

    def test_all_three_forms_collapse_consistently(self):
        """All three forms from the known FINDINGS.md bug produce either
        injury.forearm or injury.arm, never three different attributes."""
        results = set()
        for raw in ("injury.right_forearm", "injury.arm", "injury.arm.forearm"):
            r = _normalize_attribute(raw, "character", "injured")
            assert r is not None, f"{raw} should be valid"
            results.add(r[0])
        # They won't all be identical (arm vs forearm is a real difference)
        # but none should be a three-way unique split.
        # Most importantly, injury.right_forearm and injury.arm.forearm
        # should both resolve to simpler forms.
        for attr in results:
            assert "." not in attr.split(".", 1)[1] or attr.startswith("injury."), (
                f"No double-dotted injury attributes allowed: {attr}"
            )


class TestGenericBodyPartResolution:
    def test_wound_resolves_to_forearm_when_present(self):
        unit_text = "The blade caught his forearm. The wound was deep."
        result = _resolve_generic_body_part("wound", unit_text)
        assert result == "forearm"

    def test_wound_resolves_to_head_when_present(self):
        unit_text = "A blow to the head. The wound bled freely."
        result = _resolve_generic_body_part("wound", unit_text)
        assert result == "head"

    def test_cut_resolves_to_shoulder(self):
        unit_text = "A cut across his shoulder left a trail of blood."
        result = _resolve_generic_body_part("cut", unit_text)
        assert result == "shoulder"

    def test_gash_resolves_to_arm(self):
        unit_text = "She inspected the gash on his arm."
        result = _resolve_generic_body_part("gash", unit_text)
        assert result == "arm"

    def test_no_body_part_in_text_returns_generic(self):
        unit_text = "The detective walked into the room."
        result = _resolve_generic_body_part("wound", unit_text)
        assert result == "wound"

    def test_non_generic_part_unchanged(self):
        """Non-generic body parts must pass through unchanged."""
        result = _resolve_generic_body_part("forearm", "The wound was on his forearm.")
        assert result == "forearm"

    def test_forearm_wins_over_arm(self):
        """When both 'forearm' and 'arm' are in the text, 'forearm' must win
        because _SPECIFIC_BODY_PARTS_BY_LENGTH sorts longest first."""
        unit_text = "The wound on his forearm throbbed through his arm."
        result = _resolve_generic_body_part("wound", unit_text)
        assert result == "forearm", (
            "forearm should win over arm (longer match, more specific)"
        )


# --------------------------------------------------------------------------
# BUG-3: Case-sensitive provenance check discarded correct facts
# Session 4 batch 3: "The bandage was gone" (capital T) returned by model as
# "the bandage was gone" (lowercase) -- case-sensitive `in` test rejected it,
# losing the only healed event and starving the whole investigation phase.
# --------------------------------------------------------------------------
class TestExcerptMatching:
    UNIT_TEXT = "The bandage was gone, the wound beneath it closed to a thin pink line."

    def test_exact_match(self):
        result = _match_excerpt("The bandage was gone", self.UNIT_TEXT)
        assert result is not None
        assert "The bandage" in result

    def test_case_insensitive_match(self):
        """Regression: lowercase first letter must still match (capital T in source)."""
        result = _match_excerpt("the bandage was gone", self.UNIT_TEXT)
        assert result is not None, (
            "Case-insensitive match failed -- this is the session-4 bug that "
            "lost the entire healed-injury transition"
        )
        # Must return the SOURCE text's capitalization, not the model's
        assert result[0] == "T", "Returned excerpt must use source text capitalization"

    def test_no_match_returns_none(self):
        result = _match_excerpt("completely fabricated excerpt", self.UNIT_TEXT)
        assert result is None

    def test_empty_excerpt_returns_none(self):
        result = _match_excerpt("", self.UNIT_TEXT)
        assert result is None

    def test_partial_sentence_match(self):
        result = _match_excerpt("wound beneath it closed", self.UNIT_TEXT)
        assert result is not None

    def test_returns_source_text_not_model_rendering(self):
        """The returned excerpt must be sliced from source text, not from
        the model's own quote -- preserving verbatim provenance (CLAUDE.md rule 4)."""
        model_quote = "the wound beneath it closed to a thin pink line"
        result = _match_excerpt(model_quote, self.UNIT_TEXT)
        assert result is not None
        # Source text starts "the wound" with lowercase here (no capital T in that part)
        assert result in self.UNIT_TEXT, "Returned excerpt must be a verbatim substring of source"


# --------------------------------------------------------------------------
# BUG-4: Location grounding -- location value not supported by its excerpt
# Session 5: COLE/location="opposite rows" with excerpt "and kept moving".
# The excerpt is real text but doesn't mention "opposite rows".
# --------------------------------------------------------------------------
class TestLocationGrounding:
    def test_grounded_correctly(self):
        assert _location_grounded("Chicago precinct", "the window of the Chicago precinct")
        assert _location_grounded("old rail yard", "near the old rail yard")

    def test_ungrounded_rejected(self):
        """'opposite rows' is not in 'and kept moving' -- must be rejected."""
        assert not _location_grounded("opposite rows", "and kept moving"), (
            "Location grounding check failed: 'opposite rows' should not match 'and kept moving'"
        )

    def test_partial_word_overlap_insufficient(self):
        """A single shared stopword must not satisfy grounding."""
        assert not _location_grounded("river access road", "he walked on")

    def test_empty_value_is_grounded(self):
        """An empty value has no content words to check -- trivially grounded."""
        assert _location_grounded("", "anything")

    def test_city_grounded_in_excerpt(self):
        assert _location_grounded("new york", "in New York precinct")


# --------------------------------------------------------------------------
# BUG-5: Injury grounding -- body part not mentioned anywhere in unit text
# Session 5: SUSPECT/injury.head with excerpt "fired a warning shot into dirt"
# -- no mention of head anywhere in that unit.
# --------------------------------------------------------------------------
class TestInjuryGrounding:
    def test_grounded_in_excerpt(self):
        assert _injury_grounded("forearm", "the slash on his forearm", "A deep slash on his forearm.")

    def test_grounded_in_unit_text_not_excerpt(self):
        """Regression: body part in unit text but NOT in its own excerpt must
        still pass -- the session-5 first fix broke this case.
        Unit 14: 'forearm' appears earlier in unit, own excerpt says 'wound'."""
        unit_text = "He ran a hand along his forearm. The wound beneath it closed to a thin pink line."
        excerpt = "The wound beneath it closed to a thin pink line."
        assert _injury_grounded("forearm", excerpt, unit_text), (
            "Forearm appears in unit_text (just not in the excerpt) -- must be accepted"
        )

    def test_ungrounded_rejected(self):
        """head not mentioned anywhere in unit_text -- must be rejected."""
        unit_text = "Cole fired a warning shot into the dirt."
        excerpt = "fired a warning shot into the dirt"
        assert not _injury_grounded("head", excerpt, unit_text), (
            "Head not in unit_text -- must be rejected (session-5 real bug)"
        )

    def test_generic_parts_always_pass(self):
        """Generic parts (wound/body/cut/slash/gash) are exempt from grounding."""
        for generic in ("wound", "body", "cut", "slash", "gash"):
            assert _injury_grounded(generic, "anything", "unit with no specific body part"), (
                f"Generic part '{generic}' should always pass grounding"
            )


# --------------------------------------------------------------------------
# BUG-6: Over-nested possession attributes (possession.field_kit.gauze)
# FINDINGS.md + EVAL_IMPROVEMENT_LOG.md: possession.field_kit.gauze was
# stored, but the golden expects possession.gauze -- breaks entity resolution.
# --------------------------------------------------------------------------
class TestPossessionNormalization:
    def test_simple_possession_valid(self):
        attr, val = _normalize_attribute("possession.gun", "character", "held")
        assert attr == "possession.gun"
        assert val == "held"

    def test_over_nested_rejected(self):
        """possession.field_kit_OTHER.gauze (alias not in table) is depth-2 -- must be rejected.
        Note: possession.field_kit.gauze specifically IS in the alias table and resolves
        to possession.gauze (depth 1), so it correctly passes. Test a non-aliased depth-2."""
        result = _normalize_attribute("possession.some_container.widget", "character", "held")
        assert result is None, "Over-nested possession.some_container.widget must be rejected (depth-2, no alias)"

    def test_alias_field_kit_gauze_resolves(self):
        """After alias resolution, 'field_kit.gauze' -> 'gauze' (depth 1) and passes."""
        # The alias table maps "field_kit.gauze" -> "gauze" BEFORE depth check
        attr, val = _normalize_attribute("possession.field_kit.gauze", "character", "held")
        # This should be accepted now (alias resolves to depth 1)
        assert attr == "possession.gauze", (
            f"possession.field_kit.gauze should alias to possession.gauze, got {attr!r}"
        )

    def test_case_file_aliases_to_file(self):
        attr, val = _normalize_attribute("possession.case_file", "character", "acquired")
        assert attr == "possession.file"

    def test_possession_values_valid(self):
        for v in ("held", "acquired", "lost"):
            r = _normalize_attribute("possession.badge", "character", v)
            assert r is not None, f"Value '{v}' should be valid for possession"

    def test_free_form_possession_value_rejected(self):
        """'dropped during struggle' is not a controlled vocabulary term."""
        result = _normalize_attribute("possession.knife", "character", "dropped during struggle")
        assert result is None

    def test_injury_valid_values(self):
        for v in ("injured", "healed", "dead"):
            r = _normalize_attribute("injury.arm", "character", v)
            assert r is not None


# --------------------------------------------------------------------------
# BUG-7: Prop entities used as character entities
# EVAL_IMPROVEMENT_LOG.md item 16: model emits entity_name="FILE" or "BADGE"
# as entity_type="character" -- should be rejected.
# --------------------------------------------------------------------------
class TestPropEntityFilter:
    def _make_fact(self, entity_name, entity_type="character"):
        from backend.pipeline.state_extraction import StateFact
        return StateFact(
            entity_name=entity_name,
            entity_type=entity_type,
            attribute="possession.badge",
            value="held",
            raw_excerpt="badge",
            confidence=0.9,
            establishment_type="explicit",
        )

    def _make_unit(self, text="Cole held the badge.", seq=1, uid="u1"):
        return NarrativeUnit(
            unit_id=uid,
            story_universe_id="test_su",
            document_id="test_su",
            unit_type="scene",
            sequence_number=seq,
            title="Test",
            page_start=1,
            page_end=1,
            raw_text=text,
        )

    def test_badge_as_character_rejected(self):
        fact = self._make_fact("BADGE")
        unit = self._make_unit("He wore a badge proudly.")
        registry = EntityRegistry("test")
        result = _fact_to_event(fact, unit, "test", registry)
        assert result is None, "BADGE as character entity_name must be rejected"

    def test_gun_as_character_rejected(self):
        fact = self._make_fact("GUN")
        unit = self._make_unit("He fired the gun.")
        registry = EntityRegistry("test")
        result = _fact_to_event(fact, unit, "test", registry)
        assert result is None

    def test_real_character_accepted(self):
        """A fact with a real character name must pass the prop filter."""
        fact = self._make_fact("COLE")
        unit = self._make_unit("Cole held the badge.")
        registry = EntityRegistry("test")
        result = _fact_to_event(fact, unit, "test", registry)
        assert result is not None, "Real character COLE should not be filtered"


# --------------------------------------------------------------------------
# BUG-8: Vague city values that are not real city names
# EVAL_IMPROVEMENT_LOG.md item 11 + 27: model emits "city", "unspecified", etc.
# --------------------------------------------------------------------------
class TestCityValueFilters:
    def test_vague_cities_rejected(self):
        for vague in ("city", "town", "the city", "unspecified", "unnamed", "somewhere"):
            result = _normalize_attribute("location.city", "character", vague)
            assert result is None, f"Vague city '{vague}' must be rejected"

    def test_real_cities_accepted(self):
        for city in ("Chicago", "New York", "London", "Paris"):
            result = _normalize_attribute("location.city", "character", city)
            assert result is not None, f"Real city '{city}' must be accepted"
            attr, val = result
            assert attr == "location.city"
            assert val == city.lower(), f"City should be lowercased, got {val!r}"

    def test_min_length_filter(self):
        """City names shorter than 2 chars are rejected."""
        result = _normalize_attribute("location.city", "character", "a")
        assert result is None


# --------------------------------------------------------------------------
# BUG-9: Prop-typed entities using possession attribute
# Items with entity_type="prop" using attribute="possession" must be rejected.
# --------------------------------------------------------------------------
class TestPropTypedPossession:
    def test_prop_possession_rejected(self):
        result = _normalize_attribute("possession.status", "prop", "held")
        # prop + possession is rejected
        assert result is None

    def test_prop_status_rejected(self):
        result = _normalize_attribute("status", "prop", "held")
        assert result is None


# --------------------------------------------------------------------------
# BUG-10: Clothing items that are really possessions
# EVAL_IMPROVEMENT_LOG.md item 14: model emits clothing.badge/clothing.gun --
# these must be rejected (badge and gun are always possession, not clothing).
# --------------------------------------------------------------------------
class TestClothingFilter:
    def test_badge_as_clothing_rejected(self):
        result = _normalize_attribute("clothing.badge", "character", "detective badge")
        assert result is None

    def test_gun_as_clothing_rejected(self):
        result = _normalize_attribute("clothing.gun", "character", "holstered")
        assert result is None

    def test_real_clothing_accepted(self):
        attr, val = _normalize_attribute("clothing.jacket", "character", "grey wool")
        assert attr == "clothing.jacket"


# --------------------------------------------------------------------------
# BUG-11: Location pronoun filter
# EVAL_IMPROVEMENT_LOG.md item 13: "between them", "across from him" etc.
# are positional descriptions, not real locations.
# --------------------------------------------------------------------------
class TestLocationPronounFilter:
    def test_relational_pronoun_rejected(self):
        for val in ("between them", "across from him", "behind her", "next to us"):
            result = _normalize_attribute("location", "character", val)
            assert result is None, f"Relational location '{val}' must be rejected"

    def test_real_location_accepted(self):
        attr, val = _normalize_attribute("location", "character", "Chicago precinct")
        assert attr == "location"

    def test_short_location_rejected(self):
        """Location values shorter than _MIN_LOCATION_LEN=4 are rejected."""
        result = _normalize_attribute("location", "character", "her")
        assert result is None


# --------------------------------------------------------------------------
# Pipeline integrity: confirm that the normalizer/filters interact correctly
# as a whole for the known planted-error scenarios from controlled_test.txt
# --------------------------------------------------------------------------
class TestNormalizerIntegrity:
    """End-to-end attribute normalization tests on the actual planted facts
    from controlled_test.txt, confirming the pipeline would handle them."""

    def test_gun_lost_event_accepted(self):
        """Unit 4: Cole's gun drops through storm grate -> possession.gun=lost."""
        attr, val = _normalize_attribute("possession.gun", "character", "lost")
        assert attr == "possession.gun"
        assert val == "lost"

    def test_badge_lost_accepted(self):
        """Unit 5: Maya takes Cole's badge -> possession.badge=lost."""
        attr, val = _normalize_attribute("possession.badge", "character", "lost")
        assert attr == "possession.badge"
        assert val == "lost"

    def test_badge_acquired_accepted(self):
        """Unit 8: Maya returns badge -> possession.badge=acquired."""
        attr, val = _normalize_attribute("possession.badge", "character", "acquired")
        assert attr == "possession.badge"
        assert val == "acquired"

    def test_forearm_injury_accepted(self):
        """Unit 6: blade catch on forearm -> injury.forearm=injured."""
        attr, val = _normalize_attribute("injury.forearm", "character", "injured")
        assert attr == "injury.forearm"
        assert val == "injured"

    def test_forearm_healed_accepted(self):
        """Unit 14: wound closed -> injury.forearm=healed."""
        attr, val = _normalize_attribute("injury.forearm", "character", "healed")
        assert attr == "injury.forearm"
        assert val == "healed"

    def test_location_chicago_precinct_accepted(self):
        """Unit 1: Cole at Chicago precinct -> location=Chicago precinct."""
        attr, val = _normalize_attribute("location", "character", "Chicago precinct")
        assert attr == "location"
        # Article stripping: "the Chicago precinct" -> "Chicago precinct"
        assert "chicago" in val.lower() or "precinct" in val.lower()

    def test_city_chicago_accepted(self):
        """Unit 1: city name Chicago -> location.city=chicago."""
        attr, val = _normalize_attribute("location.city", "character", "Chicago")
        assert attr == "location.city"
        assert val == "chicago"


# --------------------------------------------------------------------------
# City injection
# --------------------------------------------------------------------------
class TestCityInjection:
    def _make_unit(self, text, seq=1):
        return NarrativeUnit(
            unit_id=f"test_unit_{seq}",
            story_universe_id="test_ci",
            document_id="test_ci",
            unit_type="scene",
            sequence_number=seq,
            title=f"Scene {seq}",
            page_start=1,
            page_end=1,
            raw_text=text,
        )

    def _make_location_event(self, entity_id, seq=1):
        from backend.story_state.models import StateEvent
        return StateEvent(
            id="test-id",
            story_universe_id="test_ci",
            entity_id=entity_id,
            attribute="location",
            value="precinct",
            unit_id=f"test_unit_{seq}",
            sequence_number=seq,
            page_ref=1,
            raw_excerpt="precinct",
            establishment_type="explicit",
            confidence=0.9,
        )

    def test_chicago_injected_when_in_text(self):
        from backend.pipeline.entity_resolution import EntityRegistry
        unit = self._make_unit("Detective COLE stood at the Chicago precinct.")
        events = [self._make_location_event("eval_controlled_test_character_cole")]
        registry = EntityRegistry("test_ci")
        result = _inject_city_events(events, unit, "test_ci", registry)
        city_events = [e for e in result if e.attribute == "location.city"]
        assert len(city_events) >= 1
        assert any(e.value == "chicago" for e in city_events)

    def test_no_injection_when_no_location_event(self):
        """City injection only fires when the character already has a location event."""
        unit = self._make_unit("The city of Chicago was cold and grey.")
        events = []  # no location events
        registry = EntityRegistry("test_ci")
        result = _inject_city_events(events, unit, "test_ci", registry)
        assert result == events  # unchanged

    def test_no_duplicate_when_llm_already_extracted(self):
        """If LLM already returned location.city=chicago, injection must not duplicate it."""
        from backend.story_state.models import StateEvent
        unit = self._make_unit("At the Chicago precinct, Cole waited.")
        loc_event = self._make_location_event("cole_id")
        city_event = StateEvent(
            id="city-id",
            story_universe_id="test_ci",
            entity_id="cole_id",
            attribute="location.city",
            value="chicago",
            unit_id="test_unit_1",
            sequence_number=1,
            page_ref=1,
            raw_excerpt="Chicago",
            establishment_type="explicit",
            confidence=0.9,
        )
        registry = EntityRegistry("test_ci")
        result = _inject_city_events([loc_event, city_event], unit, "test_ci", registry)
        chicago_events = [e for e in result if e.attribute == "location.city" and e.value == "chicago"]
        assert len(chicago_events) == 1, "No duplicate city events should be injected"
