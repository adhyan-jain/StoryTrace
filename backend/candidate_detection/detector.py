from typing import List
from backend.clickhouse.client import ClickHouseClient
from backend.story_state.models import CandidateConflict
import uuid

class CandidateDetector:
    def __init__(self, client: ClickHouseClient):
        self.client = client

    def detect_conflicts(self, story_universe_id: str) -> List[CandidateConflict]:
        # We look for possession conflicts: lost -> held without an acquired event.
        # This uses ClickHouse window functions to look at the previous state,
        # ordered by the document-agnostic sequence_number rather than any
        # per-document numbering (e.g. scene or chapter number).

        query = f"""
        WITH ranked_events AS (
            SELECT
                entity_id,
                unit_id,
                sequence_number,
                attribute,
                value,
                raw_excerpt,
                lagInFrame(value) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_value,
                lagInFrame(unit_id) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_unit_id,
                lagInFrame(raw_excerpt) OVER (PARTITION BY entity_id, attribute ORDER BY sequence_number) AS prev_raw_excerpt
            FROM state_events
            WHERE story_universe_id = '{story_universe_id}'
            ORDER BY entity_id, sequence_number
        )
        SELECT *
        FROM ranked_events
        WHERE
            ((attribute = 'possession' OR startsWith(attribute, 'possession.')) AND prev_value = 'lost' AND value = 'held') OR
            ((attribute = 'possession' OR startsWith(attribute, 'possession.')) AND prev_value = 'lost' AND value = 'acquired') OR
            (startsWith(attribute, 'injury.') AND prev_value = 'injured' AND value = 'healed') OR
            (attribute = 'location.city' AND prev_value != '' AND value != prev_value)
        """
        # location.city (distinct from plain 'location') is populated by the
        # extraction prompt ONLY when a city/region is explicitly named --
        # unlike scene-level 'location', it should change on the order of
        # once or twice in an entire story, not every unit. That's what
        # makes a bare "value changed" rule safe here where it was NOT safe
        # for plain 'location' (see the reverted-rule note above): city
        # mentions are rare enough that this can't degrade into flagging
        # ordinary scene transitions the way the reverted rule did.
        # lost -> acquired is the same "item came back with no explanation
        # logged yet" shape as lost -> held -- an item can't be re-acquired
        # if it was never lost in the first place, so this is just as
        # narrow/specific as the original two patterns (unlike the reverted
        # location rule, this can't fire on ordinary narrative flow). Added
        # specifically because it's a distinct value pair from lost -> held,
        # so the original rule alone can never catch a lost -> acquired ->
        # held chain at the first (suspicious) transition.
        # A "flag any location change" rule was tried here and reverted: on a
        # real eval run it turned every ordinary scene-to-scene transition
        # (precinct -> warehouse -> apartment -> rooftop -> ...) into a
        # candidate -- 16 of 18 candidates were false positives, tanking
        # Detection precision from 1.000 to 0.111. "Is this location change
        # narratively explained" is not a structural property a SQL window
        # function can evaluate; it requires reading the actual text, which
        # is the Investigation Agent's job, not the deterministic detector's.
        # Location-based conflicts (e.g. Chicago -> New York with no travel
        # scene) remain a known, disclosed detection gap -- see
        # data/eval/golden_dataset.py's docstring.

        result = self.client.client.query(query)

        conflicts = []
        for row in result.result_rows:
            entity_id = row[0]
            unit_id = row[1]
            attribute = row[3]
            value = row[4]
            raw_excerpt = row[5]
            prev_value = row[6]
            prev_unit_id = row[7]
            prev_raw_excerpt = row[8]

            description = f"Suspicious transition for {attribute}: {prev_value} -> {value} without bridging event."

            conflict = CandidateConflict(
                id=f"{story_universe_id}_{uuid.uuid4().hex[:8]}",
                story_universe_id=story_universe_id,
                entity_id=entity_id,
                attribute=attribute,
                prior_evidence_unit_id=prev_unit_id,
                prior_evidence_excerpt=prev_raw_excerpt,
                current_evidence_unit_id=unit_id,
                current_evidence_excerpt=raw_excerpt,
                description=description
            )
            conflicts.append(conflict)

        return conflicts
