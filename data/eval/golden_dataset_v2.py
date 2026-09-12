"""Ground truth (golden) dataset for StoryTrace's evaluation framework.

This encodes the manually-verified expected output of the extraction /
candidate-detection / investigation pipeline for `data/test_documents/
controlled_test_v2.txt`, an 18-unit (1-indexed paragraph = sequence_number)
controlled test document.

v2 is deliberately similar to v1 (`controlled_test.txt`) but with one key
structural difference: unit 9 (the armory scene) adds an explicit bridge for
the gun possession conflict. In v1 Cole's gun reappears with no explanation
(verdict = 'verified'). In v2, Cole explicitly signs for a replacement service
pistol at the armory before the gun appears again (verdict = 'resolved'). This
tests that the pipeline generalises its resolution logic rather than
overfitting to v1's specific sequence of events.

Other differences from v1:
- Total units: 18 (v1 has 17) -- the armory unit is a new unit 9.
- Unit numbers shift by 1 after unit 8 (the armory unit inserts before the
  rail yard scene).
- The location.city conflict (Chicago → New York) still exists at
  prior_sequence=1, current_sequence=11 (was 10 in v1).
- The injury.forearm conflict still exists: injured at seq 6, paramedic at
  seq 13, healed at seq 15. The resolved conflict (seq 13 → 15) is still
  expected 'resolved' since the same treatment bridge is present.
- The badge conflict (seq 5 → 7) is still expected 'resolved'.
- The structurally undetectable conflict (climbing ladder with injured arm,
  seq 6 → 12) is still documented as a known gap.

Detection-recall caveat: same four detector patterns as v1 (possession:
lost->held, lost->acquired, injury: injured->healed, location.city value change).
In v2 the gun conflict transitions are: lost (seq 4) -> acquired (seq 9, the
replacement) -> held (seq 10). Because the detector flags `lost -> acquired`
pairs and then `acquired -> held` pairs, it would fire on the seq 4->9 pair
but that pair is bridged (the armory IS the acquisition event, not a ghost
reappearance). The investigation agent must correctly classify this as
'resolved'. This exercises the agent's ability to read the intermediate unit
text and recognize a legitimate acquisition event.
"""

from dataclasses import dataclass, field
from typing import Literal

EntityType = Literal["character", "prop", "location"]
Verdict = Literal["verified", "resolved", "uncertain"]


@dataclass
class GoldenStateEvent:
    entity_name: str
    entity_type: EntityType
    attribute: str
    value: str
    sequence_number: int
    excerpt_contains: str


@dataclass
class GoldenConflict:
    entity_name: str
    attribute: str
    prior_sequence: int
    current_sequence: int
    expected_verdict: Verdict
    description: str


@dataclass
class GoldenDataset:
    document_path: str
    story_universe_id: str
    total_units: int
    state_events: list[GoldenStateEvent] = field(default_factory=list)
    conflicts: list[GoldenConflict] = field(default_factory=list)


GOLDEN_DATASET_V2 = GoldenDataset(
    document_path="data/test_documents/controlled_test_v2.txt",
    story_universe_id="eval_controlled_test_v2",
    total_units=18,
    state_events=[
        # 1. Gun lost when it drops through the storm grate (unit 4 = seq 4).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.gun",
            value="lost",
            sequence_number=4,
            excerpt_contains="gun slipped from his grip",
        ),
        # 2. Maya takes Cole's badge as evidence (unit 5 = seq 5).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="lost",
            sequence_number=5,
            excerpt_contains="badge",
        ),
        # 3. Knife slash on forearm (unit 6 = seq 6).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="injured",
            sequence_number=6,
            excerpt_contains="forearm",
        ),
        # 4. Maya returns the badge (unit 7 = seq 7).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="acquired",
            sequence_number=7,
            excerpt_contains="badge",
        ),
        # 5. Cole pins badge (unit 8 = seq 8).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="held",
            sequence_number=8,
            excerpt_contains="badge",
        ),
        # 6. NEW in v2: Cole signs for a replacement pistol at the armory
        # (unit 9 = seq 9). This is the explicit bridge that was missing in v1.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.gun",
            value="acquired",
            sequence_number=9,
            excerpt_contains="replacement service pistol",
        ),
        # 7. Cole raises his gun at the rail yard (unit 10 = seq 10).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.gun",
            value="held",
            sequence_number=10,
            excerpt_contains="gun",
        ),
        # 8. Opening scene establishes Chicago precinct (unit 1 = seq 1).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="location.city",
            value="chicago",
            sequence_number=1,
            excerpt_contains="Chicago",
        ),
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="location",
            value="chicago precinct",
            sequence_number=1,
            excerpt_contains="Chicago precinct",
        ),
        # 9. Cole is suddenly in a New York precinct (unit 11 = seq 11).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="location.city",
            value="new york",
            sequence_number=11,
            excerpt_contains="New York",
        ),
        # 10. Paramedic treats the forearm slash (unit 13 = seq 13).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="injured",
            sequence_number=13,
            excerpt_contains="gauze",
        ),
        # 11. Wound closed to a thin pink line (unit 15 = seq 15).
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="healed",
            sequence_number=15,
            excerpt_contains="bandage",
        ),
        # 12-18. Background facts (same as v1 equivalents at shifted unit numbers).
        GoldenStateEvent(
            entity_name="COLE", entity_type="character",
            attribute="location", value="briefing room",
            sequence_number=1, excerpt_contains="briefing room",
        ),
        GoldenStateEvent(
            entity_name="COLE", entity_type="character",
            attribute="possession.file", value="acquired",
            sequence_number=1, excerpt_contains="case file",
        ),
        GoldenStateEvent(
            entity_name="MAYA", entity_type="character",
            attribute="location", value="doorframe",
            sequence_number=2, excerpt_contains="doorframe",
        ),
        GoldenStateEvent(
            entity_name="COLE", entity_type="character",
            attribute="possession.file", value="lost",
            sequence_number=2, excerpt_contains="dropped the file",
        ),
        GoldenStateEvent(
            entity_name="COLE", entity_type="character",
            attribute="location", value="opposite rows",
            sequence_number=3, excerpt_contains="opposite rows",
        ),
        GoldenStateEvent(
            entity_name="MAYA", entity_type="character",
            attribute="location", value="opposite rows",
            sequence_number=3, excerpt_contains="opposite rows",
        ),
        GoldenStateEvent(
            entity_name="COLE", entity_type="character",
            attribute="possession.radio", value="held",
            sequence_number=3, excerpt_contains="radios turned low",
        ),
        GoldenStateEvent(
            entity_name="MAYA", entity_type="character",
            attribute="possession.radio", value="held",
            sequence_number=3, excerpt_contains="radios turned low",
        ),
        GoldenStateEvent(
            entity_name="PARAMEDIC", entity_type="character",
            attribute="possession.gauze", value="held",
            sequence_number=13, excerpt_contains="gauze",
        ),
    ],
    conflicts=[
        # KEY DIFFERENCE FROM V1: gun conflict is 'resolved' because the
        # armory scene (unit 9) provides an explicit acquisition bridge.
        GoldenConflict(
            entity_name="COLE",
            attribute="possession.gun",
            prior_sequence=4,
            current_sequence=9,
            expected_verdict="resolved",
            description=(
                "Gun lost at the river (seq 4), but replacement pistol "
                "explicitly signed for at the armory (seq 9) -- this is the "
                "bridge. Detector flags lost->acquired as a candidate; "
                "agent must find and read the armory unit text to resolve it."
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="location.city",
            prior_sequence=1,
            current_sequence=11,
            expected_verdict="verified",
            description=(
                "Chicago precinct (seq 1) to New York precinct (seq 11) with "
                "no travel established -- same structural conflict as v1, just "
                "shifted one unit due to the armory insertion."
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="injury.forearm",
            prior_sequence=6,
            current_sequence=12,
            expected_verdict="uncertain",
            description=(
                "Climbs a ladder with both hands shortly after a forearm "
                "slash (seq 6 -> 12) -- structurally undetectable by SQL "
                "window functions (both endpoints are 'injured', no value "
                "transition to key off), included only as a documentation "
                "marker. Same known gap as v1."
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="possession.badge",
            prior_sequence=5,
            current_sequence=7,
            expected_verdict="resolved",
            description=(
                "Badge taken as evidence (seq 5) then explicitly returned "
                "next morning (seq 7) -- same as v1, not a real conflict."
            ),
        ),
        # NOTE: prior_sequence=13 (paramedic scene), not 6. Same lagInFrame
        # logic as v1 -- the detector sees the most recent 'injured' state.
        GoldenConflict(
            entity_name="COLE",
            attribute="injury.forearm",
            prior_sequence=13,
            current_sequence=15,
            expected_verdict="resolved",
            description=(
                "Injury explicitly healed via paramedic treatment (seq 13) "
                "and narrated recovery (seq 15) -- not a real conflict. "
                "Same as v1's resolved case."
            ),
        ),
    ],
)
