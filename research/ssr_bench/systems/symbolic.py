"""Strong symbolic baseline: regex semantic parser (built from the TRAIN template pool only) + its own rule-based replay.

Reads TASK records only; does not import oracles. `privileged=True` additionally knows the held-out paraphrase templates and
markers (a *grammar-privileged ceiling*, never a fair baseline). Parse failures fall back to all-KEEP and are counted.
"""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
from .. import lexicon as lx

NOB = "nobody"
_PH = {"{a}": r"(?P<a>[A-Z][a-z]+)", "{b}": r"(?P<b>[A-Z][a-z]+)", "{L}": r"(?P<L>[a-z][a-z ]*?)", "{p}": r"(?P<p>[a-z][a-z ]*?)"}


def _rx(tpl: str) -> re.Pattern:
    parts = re.split(r"(\{[abLp]\})", tpl)
    return re.compile("^" + "".join(_PH[x] if x in _PH else re.escape(x) for x in parts) + "$")


def _pools(privileged: bool):
    both = (lambda e: e[0] + e[1]) if privileged else (lambda e: e[0])
    ev = [(k, _rx(t)) for k, e in lx.EVENT_TPL.items() for t in both(e)]
    asr = []
    for k, e in lx.ASSERT_TPL.items():
        asr += [(k, _rx(t)) for t in both(e)]
    mk = [re.compile("^" + re.escape(m).replace(r"\{t\}", r"(?P<t>\d+)") + r"\s+") for m in both(lx.MARKERS)]
    return ev, asr, mk


def _split(sentence: str, mk) -> Optional[Tuple[int, str]]:
    for m in mk:
        r = m.match(sentence)
        if r:
            return int(r.group("t")), sentence[r.end():].rstrip(".")
    return None


class Parsed:
    def __init__(self):
        self.loc, self.holder, self.ploc, self.inj, self.events, self.ok = {}, {}, {}, set(), {}, True


def parse_story(sents: List[str], pools) -> Parsed:
    ev, _, mk = pools
    P = Parsed()
    for s in sents:
        if s.startswith("At the start,"):
            body = s[len("At the start,"):].strip().rstrip(".")
            for pat, fn in ((r"^(?P<a>[A-Z][a-z]+) was in the (?P<L>.+)$", lambda m: P.loc.__setitem__(m["a"], m["L"])),
                            (r"^(?P<a>[A-Z][a-z]+) was carrying the (?P<p>.+)$", lambda m: P.holder.__setitem__(m["p"], m["a"])),
                            (r"^the (?P<p>.+) lay on the floor of the (?P<L>.+)$", lambda m: (P.holder.__setitem__(m["p"], NOB), P.ploc.__setitem__(m["p"], m["L"]))),
                            (r"^(?P<a>[A-Z][a-z]+) was injured$", lambda m: P.inj.add(m["a"]))):
                m = re.match(pat, body)
                if m:
                    fn(m)
                    break
            else:
                P.ok = False
            continue
        sp = _split(s, mk)
        if not sp:
            P.ok = False
            continue
        day, body = sp
        for kind, rx in ev:
            m = rx.match(body)
            if m:
                P.events[day] = (kind, m.groupdict())
                break
        else:
            P.ok = False
    return P


def _replay(P: Parsed, extra: Optional[Tuple[int, tuple]], horizon: int):
    """Own replay. Returns (snapshots, violation) where violation = (attr, entity, slot-1) for the extra event if impossible."""
    st = {"loc": dict(P.loc), "holder": dict(P.holder), "ploc": dict(P.ploc), "inj": set(P.inj)}
    for p, h in st["holder"].items():
        if h != NOB:
            st["ploc"][p] = st["loc"].get(h, "")
    evs = dict(P.events)
    if extra:
        evs[extra[0]] = extra[1]
    snaps, viol = [], None
    snap = lambda: {"loc": dict(st["loc"]), "holder": dict(st["holder"]), "ploc": dict(st["ploc"]), "inj": set(st["inj"])}
    snaps.append(snap())
    for d in range(1, horizon + 1):
        if d in evs:
            kind, g = evs[d]
            is_extra = bool(extra) and d == extra[0]
            a, b, p, L = g.get("a"), g.get("b"), g.get("p"), g.get("L")
            if kind == "give" and "received" in str(g):  # unreachable; roles handled by template groups below
                pass
            bad = None
            if kind == "move":
                bad = ("injured", a) if a in st["inj"] else None
                if not bad:
                    st["loc"][a] = L
                    for q, h in st["holder"].items():
                        if h == a:
                            st["ploc"][q] = L
            elif kind == "give":
                giver, recv = (g["a"], g["b"])
                bad = ("holder", p) if st["holder"].get(p) != giver else None
                if not bad:
                    st["holder"][p] = recv
            elif kind == "pickup":
                bad = ("holder", p) if st["holder"].get(p, NOB) != NOB else None
                if not bad:
                    st["holder"][p] = a
            elif kind == "drop":
                bad = ("holder", p) if st["holder"].get(p) != a else None
                if not bad:
                    st["holder"][p] = NOB
                    st["ploc"][p] = st["loc"].get(a, "")
            elif kind == "injure":
                st["inj"].add(a)
            elif kind == "heal":
                st["inj"].discard(a)
            if bad and is_extra:
                viol = (bad[0], bad[1], d - 1)
        snaps.append(snap())
    return snaps, viol


def _val(snap, attr, ent):
    if attr == "loc":
        return snap["loc"].get(ent, "")
    if attr == "holder":
        return snap["holder"].get(ent, "")
    if attr == "proploc":
        return snap["ploc"].get(ent, "")
    return "injured" if ent in snap["inj"] else "unharmed"


def _parse_evidence(text: str, pools):
    ev, asr, mk = pools
    sp = _split(text, mk)
    if not sp:
        return None
    day, body = sp
    for kind, rx in ev:
        m = rx.match(body)
        if m:
            return ("event", day, (kind, m.groupdict()))
    for kind, rx in asr:
        m = rx.match(body)
        if m:
            g = m.groupdict()
            if kind == "loc":
                return ("assert", day, ("loc", g["a"], g["L"]))
            if kind == "holder":
                return ("assert", day, ("holder", g["p"], g["a"]))
            if kind == "holder_nobody":
                return ("assert", day, ("holder", g["p"], NOB))
            if kind == "proploc":
                return ("assert", day, ("proploc", g["p"], g["L"]))
            return ("assert", day, ("injured", g["a"], "injured" if kind == "injured" else "unharmed"))
    return None


def predict(task: dict, privileged: bool = False) -> Tuple[Dict[str, Tuple[str, str]], bool]:
    """Returns ({claim_id: (label, value)}, parsed_ok)."""
    pools = _pools(privileged)
    keep_all = {c["id"]: ("KEEP", "") for c in task["claims"]}
    P = parse_story(task["story"], pools)
    pe = _parse_evidence(task["evidence"], pools)
    if not P.ok or pe is None:
        return keep_all, False
    horizon = max([c["slot"] for c in task["claims"]] + [pe[1]] + list(P.events) + [1])
    before, _ = _replay(P, None, horizon)
    out = dict(keep_all)
    if pe[0] == "assert":
        attr, ent, val = pe[2]
        if _val(before[pe[1]], attr, ent) != val:
            for c in task["claims"]:
                if (c["attr"], c["entity"], c["slot"]) == (attr, ent, pe[1]):
                    out[c["id"]] = ("CONFLICT", "")
        return out, True
    after, viol = _replay(P, (pe[1], pe[2]), horizon)
    if viol:
        for c in task["claims"]:
            if (c["attr"], c["entity"], c["slot"]) == viol:
                out[c["id"]] = ("CONFLICT", "")
        return out, True
    for c in task["claims"]:
        b, a = _val(before[c["slot"]], c["attr"], c["entity"]), _val(after[c["slot"]], c["attr"], c["entity"])
        if a != b:
            out[c["id"]] = ("REVISE", a.lower())
    return out, True
