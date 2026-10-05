"""Hard validators for V2 matched pairs and items (section 5 + Amendment 1 of the preregistration). Returns a list of violations."""
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List
from ..ssr_bench import oracle_a, oracle_b
from ..ssr_bench.leakage import story_from_world
from .core import story_valid
from .scorers import canon


def pair_violations(Ta: dict, Ga: dict, Tb: dict, Gb: dict) -> List[str]:
    v = []
    if Ta["evidence"] != Tb["evidence"]:
        v.append("evidence text differs")
    ka = [(c["id"], c["attr"], c["entity"], c["slot"], c["question"]) for c in Ta["claims"]]
    kb = [(c["id"], c["attr"], c["entity"], c["slot"], c["question"]) for c in Tb["claims"]]
    if ka != kb:
        v.append("claim sets differ")
    diff = [i for i, (x, y) in enumerate(zip(Ta["story"], Tb["story"])) if x != y]
    if len(Ta["story"]) != len(Tb["story"]) or len(diff) != 1:
        v.append(f"story differs in {len(diff)} sentences (len {len(Ta['story'])}/{len(Tb['story'])})")
    for T, G in ((Ta, Ga), (Tb, Gb)):
        if G["world"].get("chars") is None:     # external real-execution items have no synthetic world
            continue
        st, ev = story_from_world(G["world"])
        if not story_valid(st):
            v.append(f"{G['item_id']}: story invalid")
    ra = {i: (Ga["labels"][i], Ga["final"][i]) for i in Ga["labels"] if Ga["labels"][i] != "KEEP"}
    rb = {i: (Gb["labels"][i], Gb["final"][i]) for i in Gb["labels"] if Gb["labels"][i] != "KEEP"}
    if ra == rb:
        v.append("revisions identical")
    d = Ga["meta"]["evidence_slot"]
    cl = {c["id"]: c for c in Ta["claims"]}
    external = Ga["world"].get("chars") is None      # real-execution items: every claim is a final-state claim
    if not any(Ga["final"][i] != Gb["final"][i] for i in Ga["final"] if external or cl[i]["slot"] >= d):
        v.append("no post-evidence claim differs (Amendment 1)")
    if Ga["meta"]["depth"] != Gb["meta"]["depth"]:
        v.append("depth differs")
    if Ga["valid_final"] == Gb["valid_final"]:
        v.append("valid sets identical")
    return v


def validate_split(T: List[dict], G: List[dict]) -> Dict:
    byp = defaultdict(dict)
    for t, g in zip(T, G):
        if t["member"] in ("A", "B"):
            byp[t["pair_id"]][t["member"]] = (t, g)
    bad = {}
    for pid, m in byp.items():
        viol = pair_violations(m["A"][0], m["A"][1], m["B"][0], m["B"][1])
        if viol:
            bad[pid] = viol
    return {"pairs": len(byp), "pairs_with_violations": len(bad), "violations": bad}
