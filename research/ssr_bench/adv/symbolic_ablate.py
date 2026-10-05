"""World-rule ablation ladder of the symbolic parser (analysis only; systems/symbolic.py is imported, not modified).

Flags switch OFF one world rule at a time to show which rules carry the benchmark:
  persistence    facts persist until a later event (off: every day starts again from the initial state)
  injury_rule    an injured character cannot move (off: such a move is accepted)
  preconditions  give/pickup/drop/assertion preconditions (off: never CONFLICT)
  travel         a held prop travels with its holder (off: prop location is not updated on move)
Reads TASK records only.
"""
from __future__ import annotations
from typing import Dict, Tuple
from ..systems import symbolic as S

NOB = S.NOB


def _replay(P, extra, horizon, persistence=True, injury_rule=True, preconditions=True, travel=True):
    base = {"loc": dict(P.loc), "holder": dict(P.holder), "ploc": dict(P.ploc), "inj": set(P.inj)}
    for p, h in base["holder"].items():
        if h != NOB:
            base["ploc"][p] = base["loc"].get(h, "")
    cp = lambda s: {"loc": dict(s["loc"]), "holder": dict(s["holder"]), "ploc": dict(s["ploc"]), "inj": set(s["inj"])}
    st = cp(base)
    evs = dict(P.events)
    if extra:
        evs[extra[0]] = extra[1]
    snaps, viol = [cp(st)], None
    for d in range(1, horizon + 1):
        if not persistence:
            st = cp(base)
        if d in evs:
            kind, g = evs[d]
            is_extra = bool(extra) and d == extra[0]
            a, b, p, L = g.get("a"), g.get("b"), g.get("p"), g.get("L")
            bad = None
            if kind == "move":
                bad = ("injured", a) if (injury_rule and a in st["inj"]) else None
                if not bad:
                    st["loc"][a] = L
                    if travel:
                        for q, h in st["holder"].items():
                            if h == a:
                                st["ploc"][q] = L
            elif kind == "give":
                bad = ("holder", p) if (preconditions and st["holder"].get(p) != a) else None
                if not bad:
                    st["holder"][p] = b
            elif kind == "pickup":
                bad = ("holder", p) if (preconditions and st["holder"].get(p, NOB) != NOB) else None
                if not bad:
                    st["holder"][p] = a
            elif kind == "drop":
                bad = ("holder", p) if (preconditions and st["holder"].get(p) != a) else None
                if not bad:
                    st["holder"][p] = NOB
                    st["ploc"][p] = st["loc"].get(a, "")
            elif kind == "injure":
                st["inj"].add(a)
            elif kind == "heal":
                st["inj"].discard(a)
            if bad and is_extra:
                viol = (bad[0], bad[1], d - 1)
        snaps.append(cp(st))
    return snaps, viol


def predict_ablated(task: dict, persistence=True, injury_rule=True, preconditions=True, travel=True) -> Tuple[Dict[str, Tuple[str, str]], bool]:
    fl = dict(persistence=persistence, injury_rule=injury_rule, preconditions=preconditions, travel=travel)
    pools = S._pools(False)
    keep_all = {c["id"]: ("KEEP", "") for c in task["claims"]}
    P = S.parse_story(task["story"], pools)
    pe = S._parse_evidence(task["evidence"], pools)
    if not P.ok or pe is None:
        return keep_all, False
    horizon = max([c["slot"] for c in task["claims"]] + [pe[1]] + list(P.events) + [1])
    before, _ = _replay(P, None, horizon, **fl)
    out = dict(keep_all)
    if pe[0] == "assert":
        attr, ent, val = pe[2]
        if preconditions and S._val(before[pe[1]], attr, ent) != val:
            for c in task["claims"]:
                if (c["attr"], c["entity"], c["slot"]) == (attr, ent, pe[1]):
                    out[c["id"]] = ("CONFLICT", "")
        return out, True
    after, viol = _replay(P, (pe[1], pe[2]), horizon, **fl)
    if viol:
        for c in task["claims"]:
            if (c["attr"], c["entity"], c["slot"]) == viol:
                out[c["id"]] = ("CONFLICT", "")
        return out, True
    for c in task["claims"]:
        b, a = S._val(before[c["slot"]], c["attr"], c["entity"]), S._val(after[c["slot"]], c["attr"], c["entity"])
        if a != b:
            out[c["id"]] = ("REVISE", a.lower())
    return out, True
