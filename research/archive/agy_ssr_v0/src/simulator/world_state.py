from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

@dataclass(frozen=True)
class StateClaim:
    entity: str
    attribute: str
    value: str
    time_start: int
    time_end: int = 9999
    evidence: str = ""

    def to_tuple(self) -> Tuple[str, str, str, int, int]:
        return (self.entity, self.attribute, self.value, self.time_start, self.time_end)

@dataclass
class WorldState:
    sequence: int = 1
    entities: Set[str] = field(default_factory=set)
    locations: Set[str] = field(default_factory=set)
    props: Set[str] = field(default_factory=set)
    claims: Dict[Tuple[str, str], StateClaim] = field(default_factory=dict)

    def set_claim(self, entity: str, attribute: str, value: str, evidence: str = "") -> StateClaim:
        key = (entity, attribute)
        claim = StateClaim(
            entity=entity,
            attribute=attribute,
            value=value,
            time_start=self.sequence,
            time_end=9999,
            evidence=evidence
        )
        self.claims[key] = claim
        return claim

    def get_claim(self, entity: str, attribute: str) -> Optional[StateClaim]:
        return self.claims.get((entity, attribute))

    def copy(self) -> WorldState:
        new_ws = WorldState(
            sequence=self.sequence,
            entities=set(self.entities),
            locations=set(self.locations),
            props=set(self.props),
            claims=dict(self.claims)
        )
        return new_ws
