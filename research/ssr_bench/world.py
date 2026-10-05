"""Latent world model for the SSR benchmark: data types only, no semantics.

Semantics live in two independently written oracles (oracle_a.py, oracle_b.py).
Time is a sequence of integer slots 1..horizon. State at slot s = state after all events with slot <= s.
Slot 0 is the initial state (told in an intro). At most one event per slot.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Tuple, Union

KINDS = ("move", "give", "pickup", "drop", "injure", "heal", "noop")
ATTRS = ("loc", "holder", "proploc", "injured")
NOBODY = "nobody"
Key = Tuple[str, str, int]  # (attr, entity, slot): loc/injured -> entity is a character; holder/proploc -> a prop


@dataclass(frozen=True)
class Event:
    slot: int
    kind: str
    actor: str          # acting character (for injure/heal: the affected character)
    target: str = ""    # move: destination location; give: receiving character
    prop: str = ""      # give/pickup/drop


@dataclass(frozen=True)
class Assertion:
    """A stated fact about the world at a slot (not an event)."""
    slot: int
    attr: str
    entity: str
    value: str


Evidence = Union[Event, Assertion]


@dataclass
class Story:
    chars: List[str]
    props: List[str]
    locs: List[str]
    init_loc: Dict[str, str]
    init_holder: Dict[str, str]      # prop -> character or NOBODY
    init_proploc: Dict[str, str]     # prop -> location (used when held by nobody; ignored when held)
    init_injured: FrozenSet[str]
    events: List[Event]
    n_slots: int                     # story occupies slots 1..n_slots
    horizon: int = 0                 # claims may refer to slots 1..horizon (>= n_slots)

    def __post_init__(self):
        if not self.horizon:
            self.horizon = self.n_slots + 2
        slots = [e.slot for e in self.events]
        assert len(slots) == len(set(slots)), "one event per slot"
        self.events = sorted(self.events, key=lambda e: e.slot)

    def free_slots(self) -> List[int]:
        used = {e.slot for e in self.events}
        return [s for s in range(1, self.horizon + 1) if s not in used]

    def with_event(self, ev: Event) -> "Story":
        return Story(self.chars, self.props, self.locs, self.init_loc, self.init_holder, self.init_proploc,
                     self.init_injured, list(self.events) + [ev], self.n_slots, self.horizon)

    def all_keys(self) -> List[Key]:
        keys: List[Key] = []
        for s in range(1, self.horizon + 1):
            for c in self.chars:
                keys += [("loc", c, s), ("injured", c, s)]
            for p in self.props:
                keys += [("holder", p, s), ("proploc", p, s)]
        return keys


class InvalidIntervention(Exception):
    """Raised when evidence cannot be given an unambiguous gold label (generator resamples)."""
