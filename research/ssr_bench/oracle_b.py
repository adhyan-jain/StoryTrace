"""Gold oracle B: stateless backward-lookup ("last write wins") semantics.

Written independently of oracle_a.py: no mutable world state, no replay. The value of any claim is derived by
scanning the event list backwards for the latest event that determines it; preconditions are checked against
values derived at slot-1. Returns {claim_key: (label, new_value)}.
"""
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from .world import Assertion, Event, Evidence, InvalidIntervention, Key, NOBODY, Story


def _latest(events: List[Event], s: int, pred) -> Optional[Event]:
    best = None
    for e in events:
        if e.slot <= s and pred(e) and (best is None or e.slot > best.slot):
            best = e
    return best


def value(story: Story, events: List[Event], attr: str, ent: str, s: int) -> str:
    if attr == "loc":
        e = _latest(events, s, lambda e: e.kind == "move" and e.actor == ent)
        return e.target if e else story.init_loc[ent]
    if attr == "injured":
        e = _latest(events, s, lambda e: e.kind in ("injure", "heal") and e.actor == ent)
        if e is None:
            return "injured" if ent in story.init_injured else "unharmed"
        return "injured" if e.kind == "injure" else "unharmed"
    if attr == "holder":
        e = _latest(events, s, lambda e: e.kind in ("give", "pickup", "drop") and e.prop == ent)
        if e is None:
            return story.init_holder[ent]
        return {"give": e.target, "pickup": e.actor, "drop": NOBODY}[e.kind]
    if attr == "proploc":
        h = value(story, events, "holder", ent, s)
        if h != NOBODY:
            return value(story, events, "loc", h, s)
        d = _latest(events, s, lambda e: e.kind == "drop" and e.prop == ent)
        return value(story, events, "loc", d.actor, d.slot) if d else story.init_proploc[ent]
    raise ValueError(attr)


def check(story: Story, events: List[Event], e: Event) -> Optional[Tuple[str, str]]:
    """None if e is valid given the world at slot e.slot-1; else contradicted (attr, entity)."""
    v = lambda a, x: value(story, events, a, x, e.slot - 1)
    if e.kind == "move":
        if v("injured", e.actor) == "injured":
            return ("injured", e.actor)
    elif e.kind == "give":
        if v("holder", e.prop) != e.actor:
            return ("holder", e.prop)
        if v("loc", e.actor) != v("loc", e.target):
            raise InvalidIntervention("give across locations")
    elif e.kind == "pickup":
        if v("holder", e.prop) != NOBODY:
            return ("holder", e.prop)
        if v("proploc", e.prop) != v("loc", e.actor):
            raise InvalidIntervention("pickup elsewhere")
    elif e.kind == "drop":
        if v("holder", e.prop) != e.actor:
            return ("holder", e.prop)
    return None


def values(story: Story, keys: List[Key]) -> Dict[Key, str]:
    for e in story.events:
        assert check(story, [x for x in story.events if x.slot < e.slot], e) is None, "story itself is invalid"
    return {k: value(story, story.events, k[0], k[1], k[2]) for k in keys}


def gold(story: Story, ev: Evidence, keys: List[Key]) -> Dict[Key, Tuple[str, str]]:
    if isinstance(ev, Assertion):
        bad = value(story, story.events, ev.attr, ev.entity, ev.slot) != ev.value
        ck = (ev.attr, ev.entity, ev.slot) if bad else None
        new_events = story.events
    else:
        if ev.slot < 2:
            raise InvalidIntervention("slot<2")
        # Evidence is checked on its own against the prior world; invalid evidence is rejected, not integrated.
        own = check(story, [x for x in story.events if x.slot < ev.slot], ev)
        new_events = story.events + [ev]
        if own is None:
            ordered = sorted(new_events, key=lambda e: e.slot)
            for e in ordered:
                if e.slot != ev.slot and check(story, [x for x in ordered if x.slot < e.slot], e):
                    raise InvalidIntervention("breaks later events")
        ck = (own[0], own[1], ev.slot - 1) if own else None
    out = {}
    for k in keys:
        if ck is not None:
            out[k] = ("CONFLICT", "") if k == ck else ("KEEP", "")
            continue
        b = value(story, story.events, *k[:2], k[2])
        a = value(story, new_events, *k[:2], k[2])
        out[k] = ("REVISE", a) if a != b else ("KEEP", "")
    return out
