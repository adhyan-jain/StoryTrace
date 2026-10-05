"""Novel surface forms for the `novel_templates` transform (analysis only). Same interface as ssr_bench/realize.py,
but every event/assertion template and every day marker is NEW (disjoint from lexicon.py train and held-out pools; a test enforces this).
The intro sentences ("At the start, ...") and claim statements are unchanged because the prompts reference them."""
from __future__ import annotations
import random
from typing import List
from .. import lexicon as lx
from .. import realize as R0
from ..world import Assertion, Event, NOBODY, Story

EVENT_TPL = {
    "move": ["{a} traveled on to the {L}", "{a} wandered off toward the {L} and stayed there", "{a} ended up in the {L}"],
    "give": ["{a} placed the {p} in {b}'s care", "{b} was given the {p} by {a}"],
    "pickup": ["{a} seized the {p} off the ground", "{a} bent down and took the {p}"],
    "drop": ["{a} released the {p} onto the ground", "{a} set aside the {p}, leaving it behind"],
    "injure": ["{a} was struck down with an injury", "{a} twisted a knee badly"],
    "heal": ["{a} bounced back to full health", "{a} was restored to good health"],
    "noop": ["{a} whistled absentmindedly", "{a} paced about idly", "{a} thought about the {p}", "{a} mentioned the {L} in passing"],
}
ASSERT_TPL = {
    "loc": ["{a} happened to be in the {L}", "someone spotted {a} inside the {L}"],
    "holder": ["{a} was in possession of the {p}", "{a} kept the {p} on them"],
    "holder_nobody": ["the {p} had no holder", "the {p} was left lying unheld"],
    "proploc": ["the {p} sat in the {L}", "the {p} lay somewhere in the {L}"],
    "injured": ["{a} bore an injury", "{a} was hurt and aching"],
    "unharmed": ["{a} was healthy", "{a} showed no signs of injury"],
}
MARKERS = ["Come day {t},", "Back on day {t},", "On the morning of day {t},"]


def all_templates() -> List[str]:
    out = list(MARKERS)
    for tbl in (EVENT_TPL, ASSERT_TPL):
        for v in tbl.values():
            out += v
    return out


def _sentence_for_event(e: Event, rng, ctx: Story) -> str:
    p = e.prop or (rng.choice(ctx.props) if ctx.props else "")
    L = e.target or (rng.choice(ctx.locs) if ctx.locs else "")
    return rng.choice(EVENT_TPL[e.kind]).format(a=e.actor, b=e.target, L=L, p=p)


def assertion_text(a: Assertion, rng) -> str:
    if a.attr == "loc":
        tpl, kw = ASSERT_TPL["loc"], dict(a=a.entity, L=a.value)
    elif a.attr == "holder":
        tpl, kw = (ASSERT_TPL["holder_nobody"], dict(p=a.entity)) if a.value == NOBODY else (ASSERT_TPL["holder"], dict(a=a.value, p=a.entity))
    elif a.attr == "proploc":
        tpl, kw = ASSERT_TPL["proploc"], dict(p=a.entity, L=a.value)
    else:
        tpl, kw = (ASSERT_TPL["injured"] if a.value == "injured" else ASSERT_TPL["unharmed"]), dict(a=a.entity)
    return rng.choice(tpl).format(**kw)


def evidence_text(ev, story: Story, rng, heldout=False) -> str:
    body = assertion_text(ev, rng) if isinstance(ev, Assertion) else _sentence_for_event(ev, rng, story)
    return f"{rng.choice(MARKERS).format(t=ev.slot)} {body}."


def story_sentences(story: Story, rng, heldout: bool, shuffle: bool) -> List[str]:
    intro = []
    for c in story.chars:
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["loc"].format(a=c, L=story.init_loc[c]))
    for p in story.props:
        h = story.init_holder[p]
        intro.append(f"{lx.INTRO_MARK} " + (lx.INTRO_TPL["holder"].format(a=h, p=p) if h != NOBODY else lx.INTRO_TPL["ground"].format(p=p, L=story.init_proploc[p])))
    for c in sorted(story.init_injured):
        intro.append(f"{lx.INTRO_MARK} " + lx.INTRO_TPL["injured"].format(a=c))
    body = [f"{rng.choice(MARKERS).format(t=e.slot)} {_sentence_for_event(e, rng, story)}." for e in story.events]
    if shuffle:
        rng.shuffle(body)
    return intro + body
