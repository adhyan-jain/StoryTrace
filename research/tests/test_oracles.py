"""Oracle correctness: hand fixtures, A==B agreement, and semantic invariants on thousands of random worlds."""
import random
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st
from research.ssr_bench import generate as gen, oracle_a, oracle_b
from research.ssr_bench.world import Assertion, Event, InvalidIntervention, Story

NOB = "nobody"


def tiny():
    # Day 2: Ann moves to Tower (carrying the key). Day 5: Ann moves to Cellar.
    return Story(["Ann", "Bob"], ["key"], ["Hall", "Tower", "Cellar"],
                 {"Ann": "Hall", "Bob": "Hall"}, {"key": "Ann"}, {"key": "Hall"}, frozenset(),
                 [Event(2, "move", "Ann", target="Tower"), Event(5, "move", "Ann", target="Cellar")], 6)


def both(story, ev, keys):
    return oracle_a.gold(story, ev, keys), oracle_b.gold(story, ev, keys)


def test_dependent_claim_and_bounded_temporal_scope():
    s = tiny()
    keys = [("loc", "Ann", 3), ("proploc", "key", 3), ("loc", "Ann", 6), ("proploc", "key", 6), ("loc", "Bob", 3)]
    ev = Event(3, "move", "Ann", target="Hall")   # past insertion; overwritten by the day-5 move
    a, b = both(s, ev, keys)
    assert a == b
    assert a[("loc", "Ann", 3)] == ("REVISE", "Hall")
    assert a[("proploc", "key", 3)] == ("REVISE", "Hall")      # dependent claim follows the holder
    assert a[("loc", "Ann", 6)] == ("KEEP", "")               # temporally local: later state restored
    assert a[("proploc", "key", 6)] == ("KEEP", "")
    assert a[("loc", "Bob", 3)] == ("KEEP", "")


def test_invalid_give_is_conflict_on_holder_claim_only():
    s = tiny()
    keys = [("holder", "key", 3), ("loc", "Ann", 3), ("holder", "key", 4)]
    ev = Event(4, "give", "Bob", target="Ann", prop="key")    # Bob does not hold the key
    a, b = both(s, ev, keys)
    assert a == b
    assert a[("holder", "key", 3)] == ("CONFLICT", "")
    assert a[("loc", "Ann", 3)] == ("KEEP", "") and a[("holder", "key", 4)] == ("KEEP", "")


def test_injured_cannot_move_is_conflict():
    s = tiny()
    s.init_injured = frozenset({"Bob"})
    ev = Event(3, "move", "Bob", target="Tower")
    a, b = both(s, ev, [("injured", "Bob", 2), ("loc", "Bob", 3)])
    assert a == b and a[("injured", "Bob", 2)][0] == "CONFLICT" and a[("loc", "Bob", 3)][0] == "KEEP"


def test_consistent_assertion_and_noop_are_all_keep():
    s = tiny()
    keys = s.all_keys()
    for ev in (Assertion(3, "loc", "Ann", "Tower"), Event(3, "noop", "Bob"), Event(3, "move", "Bob", target="Hall")):
        a, b = both(s, ev, keys)
        assert a == b and all(v[0] == "KEEP" for v in a.values())


def test_false_assertion_conflicts_exactly_its_claim():
    s = tiny()
    a, b = both(s, Assertion(3, "loc", "Ann", "Cellar"), s.all_keys())
    assert a == b
    assert [k for k, v in a.items() if v[0] == "CONFLICT"] == [("loc", "Ann", 3)]


def test_later_event_made_invalid_is_rejected_by_both():
    s = Story(["Ann", "Bob"], ["key"], ["Hall", "Tower"], {"Ann": "Hall", "Bob": "Hall"}, {"key": "Ann"}, {"key": "Hall"},
              frozenset(), [Event(3, "give", "Ann", target="Bob", prop="key")], 4)
    ev = Event(2, "move", "Bob", target="Tower")   # would separate Ann/Bob before the give
    for o in (oracle_a, oracle_b):
        with pytest.raises(InvalidIntervention):
            o.gold(s, ev, s.all_keys())


def random_world(seed, pools="A", struct="id"):
    cfg = dict(gen.BASE, pools=pools, struct=struct)
    rng = random.Random(seed)
    for _ in range(50):
        s = gen.sample_story(rng, cfg)
        if s:
            return s, rng
    raise AssertionError("no story")


def random_evidence(story, rng):
    slot = rng.choice([x for x in story.free_slots() if x >= 2])
    if rng.random() < 0.3:
        attr = rng.choice(["loc", "holder", "proploc", "injured"])
        ent = rng.choice(story.chars if attr in ("loc", "injured") else story.props)
        return Assertion(slot, attr, ent, rng.choice(gen.domain(story, attr)))
    a = rng.choice(story.chars)
    kind = rng.choice(["move", "give", "pickup", "drop", "injure", "heal", "noop"])
    kw = dict(move=dict(target=rng.choice(story.locs)),
              give=dict(target=rng.choice([c for c in story.chars if c != a]), prop=rng.choice(story.props)),
              pickup=dict(prop=rng.choice(story.props)), drop=dict(prop=rng.choice(story.props))).get(kind, {})
    return Event(slot, kind, a, **kw)


@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.integers(0, 10 ** 9), st.sampled_from(["A", "B", "NEAR"]))
def test_oracles_agree_and_satisfy_invariants_on_random_worlds(seed, pools):
    story, rng = random_world(seed, pools)
    keys = story.all_keys()
    assert oracle_a.values(story, keys) == oracle_b.values(story, keys)
    prior = oracle_a.values(story, keys)
    ev = random_evidence(story, rng)
    outs = []
    for o in (oracle_a, oracle_b):
        try:
            outs.append(o.gold(story, ev, keys))
        except InvalidIntervention:
            outs.append("invalid")
    assert outs[0] == outs[1]
    g = outs[0]
    if g == "invalid":
        return
    conflicts = [k for k, v in g.items() if v[0] == "CONFLICT"]
    revises = [k for k, v in g.items() if v[0] == "REVISE"]
    assert len(conflicts) <= 1
    assert not (conflicts and revises)                         # rejected evidence changes nothing
    assert all(g[k][1] != prior[k] for k in revises)           # a REVISE always changes the value
    if isinstance(ev, Assertion):
        assert not revises
    else:
        assert all(k[2] >= ev.slot for k in revises)           # events never change the past
    if isinstance(ev, Event) and ev.kind == "noop":
        assert all(v[0] == "KEEP" for v in g.values())
