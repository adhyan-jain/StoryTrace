"""Story-replay oracle (text only): parses story + evidence + claim questions, replays the world, answers each claim.
Independent of the V1 oracles (uses the V1 text parser + its own replay in systems/symbolic.py, which never imports the oracles).
Handles the set-valued disjunctive evidence by returning the first alternative (either world is valid)."""
from __future__ import annotations
import re
from typing import Dict
from ..ssr_bench.systems import symbolic as S

DISJ = re.compile(r"^(?P<m>.*?)\s(?P<a>[A-Z][a-z]+) went to either the (?P<L1>[a-z ]+?) or the (?P<L2>[a-z ]+?), though it was unclear which\.$")


def novel_pools():
    """Parser pools for the novel-template transform (grammar-aware replay oracle: shows the task is solvable from the story)."""
    from ..ssr_bench.adv import novel_realize as NR
    ev = [(k, S._rx(t)) for k, tpls in NR.EVENT_TPL.items() for t in tpls]
    mk = [re.compile("^" + re.escape(m).replace(r"\{t\}", r"(?P<t>\d+)") + r"\s+") for m in NR.MARKERS]
    return ev, [], mk


def predict_final(task: dict, privileged: bool = False, pools=None) -> Dict[str, str]:
    pools = pools or S._pools(privileged)
    P = S.parse_story(task["story"], pools)
    text = task["evidence"]
    m = DISJ.match(text)
    if m:
        text = f"{m['m']} {m['a']} walked to the {m['L1']}."
    pe = S._parse_evidence(text, pools)
    fallback = {c["id"]: "" for c in task["claims"]}
    if not P.ok or pe is None or pe[0] != "event":
        return fallback
    horizon = max([c["slot"] for c in task["claims"]] + [pe[1]] + list(P.events) + [1])
    before, _ = S._replay(P, None, horizon)
    after, viol = S._replay(P, (pe[1], pe[2]), horizon)
    snaps = before if viol else after
    return {c["id"]: S._val(snaps[c["slot"]], c["attr"] if c["attr"] != "holder" else "holder", c["entity"]) for c in task["claims"]}
