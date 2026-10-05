"""Turn events/assertions/claims into text. Pure surface realisation; no semantics."""
from __future__ import annotations
import random
from typing import Dict, List
from . import lexicon as lx
from .world import Assertion, Event, Evidence, Key, NOBODY, Story


def _cap(s: str) -> str:
    return s[0].upper() + s[1:]


def marker(slot: int, rng: random.Random, heldout: bool) -> str:
    return rng.choice(lx.pool(lx.MARKERS, heldout)).format(t=slot)


def _sentence_for_event(e: Event, rng, heldout, ctx: Story) -> str:
    # noop templates may mention a prop/location: pick harmless ones from the story world
    p = e.prop or (rng.choice(ctx.props) if ctx.props else "")
    L = e.target or (rng.choice(ctx.locs) if ctx.locs else "")
    tpl = rng.choice(lx.pool(lx.EVENT_TPL[e.kind], heldout))
    return tpl.format(a=e.actor, b=e.target, L=L, p=p)


def assertion_text(a: Assertion, rng, heldout) -> str:
    if a.attr == "loc":
        tpl, kw = lx.ASSERT_TPL["loc"], dict(a=a.entity, L=a.value)
    elif a.attr == "holder":
        if a.value == NOBODY:
            tpl, kw = lx.ASSERT_TPL["holder_nobody"], dict(p=a.entity)
        else:
            tpl, kw = lx.ASSERT_TPL["holder"], dict(a=a.value, p=a.entity)
    elif a.attr == "proploc":
        tpl, kw = lx.ASSERT_TPL["proploc"], dict(p=a.entity, L=a.value)
    else:
        tpl, kw = (lx.ASSERT_TPL["injured"] if a.value == "injured" else lx.ASSERT_TPL["unharmed"]), dict(a=a.entity)
    return rng.choice(lx.pool(tpl, heldout)).format(**kw)


def evidence_text(ev: Evidence, story: Story, rng, heldout) -> str:
    body = assertion_text(ev, rng, heldout) if isinstance(ev, Assertion) else _sentence_for_event(ev, rng, heldout, story)
    return f"{marker(ev.slot, rng, heldout)} {body}."


def story_sentences(story: Story, rng, heldout: bool, shuffle: bool) -> List[str]:
    intro = []
    for c in story.chars:
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["loc"].format(a=c, L=story.init_loc[c]))
    for p in story.props:
        h = story.init_holder[p]
        intro.append(f"{lx.INTRO_MARK} " + (lx.INTRO_TPL["holder"].format(a=h, p=p) if h != NOBODY
                                              else lx.INTRO_TPL["ground"].format(p=p, L=story.init_proploc[p])))
    for c in sorted(story.init_injured):
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["injured"].format(a=c))
    body = [f"{marker(e.slot, rng, heldout)} {_sentence_for_event(e, rng, heldout, story)}." for e in story.events]
    if shuffle:
        rng.shuffle(body)
    return intro + body


def claim_statement(k: Key, value: str) -> str:
    attr, ent, s = k
    if attr == "loc":
        return f"On day {s}, {ent} is in the {value}."
    if attr == "injured":
        return f"On day {s}, {ent} is {value}."
    if attr == "holder":
        return f"On day {s}, the {ent} is held by {'nobody' if value == NOBODY else value}."
    return f"On day {s}, the {ent} is located in the {value}."


def question_text(k: Key) -> str:
    attr, ent, s = k
    return {"loc": f"Where is {ent} on day {s}?",
            "injured": f"On day {s}, is {ent} injured or unharmed?",
            "holder": f"Who is holding the {ent} on day {s}? (answer a name or 'nobody')",
            "proploc": f"Where is the {ent} on day {s}?"}[attr]
