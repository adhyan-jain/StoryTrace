"""Ground truth (golden) dataset for StoryTrace's evaluation framework.

This encodes the manually-verified expected output of the extraction /
candidate-detection / investigation pipeline for `data/test_documents/
controlled_test.txt`, a 17-unit (1-indexed paragraph = sequence_number)
controlled test document. The sequence numbers and excerpt substrings below
were verified against the actual source text — not assumed or paraphrased
from a summary — so they should match exactly what
`scripts/run_pipeline_on_text.py` produces when it splits the document on
blank lines into 17 NarrativeUnits.

Detection-recall caveat: the deterministic SQL candidate detector
(`backend/candidate_detection/detector.py`) only flags two specific
transition patterns via ClickHouse `lagInFrame` compared against the
IMMEDIATELY PRECEDING event for a given entity+attribute:
  - possession: lost -> held
  - injury: injured -> healed
Two of the golden conflicts below therefore structurally cannot be produced
by the SQL detector and are expected to appear as false negatives at the
detection stage (not a bug in the eval, and not to be silently smoothed
over in eval notes/report commentary):
  - Conflict #3 (injury, seq 6 -> 11): both endpoints are "injured" — there
    is no value transition at all for the SQL to key off of.
  - Conflict #4 (badge, seq 5 -> 7): the sequence is lost(5) -> acquired(7)
    -> held(8); "acquired" sits between "lost" and "held", so no adjacent
    lost->held pair for lagInFrame to see.
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


GOLDEN_DATASET = GoldenDataset(
    document_path="data/test_documents/controlled_test.txt",
    story_universe_id="eval_controlled_test",
    total_units=17,
    state_events=[
        # 1. Gun lost when it drops through the storm grate.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.gun",
            value="lost",
            sequence_number=4,
            excerpt_contains="gun slipped from his grip",
        ),
        # 2. Maya takes Cole's badge as evidence. Possession is tracked
        # per-character on the entity who has/loses the item, so this is
        # logged as COLE's possession.badge=lost, not a MAYA event.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="lost",
            sequence_number=5,
            excerpt_contains="badge",
        ),
        # 3. Knife slash on his right forearm (text says "forearm", not "arm").
        # NOTE: a real run against this document showed the model extracting
        # "injury.right_forearm" specifically for THIS unit (unlike units
        # 7/12/14 below, which all extracted the plainer "injury.forearm") --
        # a genuine body-part-naming inconsistency within a single document,
        # since the system prompt's injury.<body_part> vocabulary is
        # freeform, not controlled the way possession/injury *values* are.
        # Golden uses the dominant "injury.forearm" term rather than
        # over-fitting to one run's exact phrasing; this event is expected to
        # sometimes show as a false negative for that reason, not an eval bug.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="injured",
            sequence_number=6,
            excerpt_contains="forearm",
        ),
        # 4. Maya returns his badge the next morning.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="acquired",
            sequence_number=7,
            excerpt_contains="badge",
        ),
        # 5. Cole pins the badge to his jacket — a natural "held" state after
        # the return. Speculative: lower confidence this fires as its own
        # event since the acquisition already happened at sequence 7.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.badge",
            value="held",
            sequence_number=8,
            excerpt_contains="badge",
        ),
        # 6. Cole raises and fires his gun despite having lost it at sequence
        # 4, with no recovery scene in between. Planted continuity conflict.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="possession.gun",
            value="held",
            sequence_number=9,
            excerpt_contains="gun",
        ),
        # 7. Opening scene establishes Chicago precinct.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="location",
            value="chicago",
            sequence_number=1,
            excerpt_contains="Chicago",
        ),
        # 8. Cole is suddenly in a New York precinct, no travel established.
        # Planted continuity conflict.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="location",
            value="new york",
            sequence_number=10,
            excerpt_contains="New York",
        ),
        # 9. Paramedic treats the forearm slash on the rooftop. "bandage"
        # does not appear as a literal substring in this unit's text (only
        # in the next unit) — "gauze" does, so that is used instead.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="injured",
            sequence_number=12,
            excerpt_contains="gauze",
        ),
        # 10. Wound has closed to a thin pink line; healed. "bandage" and
        # "wound" both appear literally in this unit's text.
        GoldenStateEvent(
            entity_name="COLE",
            entity_type="character",
            attribute="injury.forearm",
            value="healed",
            sequence_number=14,
            excerpt_contains="bandage",
        ),
    ],
    conflicts=[
        GoldenConflict(
            entity_name="COLE",
            attribute="possession.gun",
            prior_sequence=4,
            current_sequence=9,
            expected_verdict="verified",
            description=(
                "Gun reappears after being lost through a storm grate — "
                "no recovery scene"
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="location",
            prior_sequence=1,
            current_sequence=10,
            expected_verdict="verified",
            description=(
                "Chicago precinct to New York precinct with no travel "
                "established"
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="injury.forearm",
            prior_sequence=6,
            current_sequence=11,
            expected_verdict="uncertain",
            description=(
                "Climbs a ladder with both hands shortly after a forearm "
                "slash — injury status at this point is ambiguous, not "
                "clearly re-established or healed"
            ),
        ),
        GoldenConflict(
            entity_name="COLE",
            attribute="possession.badge",
            prior_sequence=5,
            current_sequence=7,
            expected_verdict="resolved",
            description=(
                "Badge taken as evidence then explicitly returned next "
                "morning — not a real conflict"
            ),
        ),
        # NOTE: prior_sequence is 12, not 6 -- the detector's SQL flags a
        # transition against the IMMEDIATELY PRECEDING event for this
        # entity+attribute (ClickHouse lagInFrame), which for "injury.forearm"
        # is the still-injured state re-established at sequence 12 (paramedic
        # scene), not the original slash at sequence 6.
        GoldenConflict(
            entity_name="COLE",
            attribute="injury.forearm",
            prior_sequence=12,
            current_sequence=14,
            expected_verdict="resolved",
            description=(
                "Injury explicitly healed via paramedic treatment and "
                "narrated recovery — not a real conflict"
            ),
        ),
    ],
)
