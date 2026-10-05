"""Story-blind attackers for V2 (G9). Inputs: evidence text, claim questions/attr/entity/slot/domain, entity lists. NEVER the story.
Each returns a full final-state prediction {claim_id: value}. The learned ones decide, per claim, whether to apply the value
implied by the evidence sentence; all others fall back to attribute-level guesses (the prior state is unknowable without the story).
Trained on the V2 `train` split only. `bayes_bound` (gold-using, an upper bound for ANY story-blind function) lives in g9.py."""
from __future__ import annotations
import re
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from ..ssr_bench.leakage import delex
from ..ssr_bench.systems import symbolic as S

ATTRS = ["loc", "holder", "proploc", "injured"]
POOLS = S._pools(False)


def ev_day(t: dict) -> int:
    return int(re.search(r"\d+", t["evidence"]).group())


def implied(t: dict) -> Dict[Tuple[str, str], str]:
    """{(attr, entity): value} the evidence sentence directly asserts for slots >= its day (empty if unparseable)."""
    pe = S._parse_evidence(t["evidence"], POOLS)
    if pe is None or pe[0] != "event":
        return {}
    kind, g = pe[2]
    a, b, p, L = g.get("a"), g.get("b"), g.get("p"), g.get("L")
    return {"move": {("loc", a): L}, "give": {("holder", p): b}, "pickup": {("holder", p): a}, "drop": {("holder", p): "nobody"},
            "injure": {("injured", a): "injured"}, "heal": {("injured", a): "unharmed"}}.get(kind, {})


def fallback(c: dict) -> str:
    return {"injured": "unharmed", "holder": "nobody"}.get(c["attr"], c["domain"][0])


def feats(t: dict) -> Tuple[np.ndarray, List[Optional[str]]]:
    imp, d, e = implied(t), ev_day(t), t["evidence"]
    et = set(re.findall(r"[a-z]+", re.sub(r"^[^,:]*[,:]", "", e).lower()))
    rows, vals = [], []
    for i, c in enumerate(t["claims"]):
        v = imp.get((c["attr"], c["entity"])) if c["slot"] >= d else None
        ct = set(re.findall(r"[a-z]+", c["question"].lower())) - {"on", "day", "is", "the", "where", "who", "holding", "or", "a", "name", "answer", "injured", "unharmed", "nobody"}
        jac = len(et & ct) / max(1, len(et | ct))
        ment = int(re.search(rf"\b{re.escape(c['entity'])}\b", e) is not None)
        rows.append([c["slot"] - d, int(c["slot"] >= d), int(c["slot"] == d), int(c["slot"] == d - 1), i, ATTRS.index(c["attr"]), ment,
                     int(v is not None), jac, len(c["domain"]), d, len(t["story"]) if False else 0])
        vals.append(v)
    return np.array(rows, dtype=float), vals


POS, LEX, ALL = [0, 1, 2, 3, 5, 7], [5, 6, 7, 8, 1], list(range(11))


class Attackers:
    NAMES = ["majority_prior", "evidence_apply", "claim_count_prior", "positional", "lexical_overlap", "entity_blind", "template_nn", "gb_all_nonstory"]

    def __init__(self, train_tasks: List[dict], train_gold: List[dict], seed: int = 0):
        self.seed = seed
        X, y, txt = [], [], []
        self.k_dist = []
        self.tpl: Dict[tuple, Dict[int, int]] = {}
        for t, g in zip(train_tasks, train_gold):
            F, V = feats(t)
            k = 0
            for c, r, v in zip(t["claims"], F, V):
                if v is None:
                    continue
                lab = int(g["final"][c["id"]] == v)
                k += lab
                X.append(r)
                y.append(lab)
                txt.append(delex(t["evidence"]))
                key = (delex(t["evidence"]), c["attr"], int(np.sign(r[0])), int(r[6]))
                self.tpl.setdefault(key, {}).setdefault(lab, 0)
                self.tpl[key][lab] += 1
            self.k_dist.append(k)
        X, y = np.array(X), np.array(y)
        self.gb = {n: GradientBoostingClassifier(random_state=seed).fit(X[:, cols], y) for n, cols in (("positional", POS), ("lexical_overlap", LEX), ("gb_all_nonstory", ALL))}
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3)
        self.eb = LogisticRegression(max_iter=4000).fit(hstack([csr_matrix(X[:, POS]), self.vec.fit_transform(txt)]).tocsr(), y)
        self.tpl_rule = {k: max(v, key=v.get) for k, v in self.tpl.items()}

    def _apply(self, t: dict, F, V, decide) -> Dict[str, str]:
        out = {}
        for i, (c, r, v) in enumerate(zip(t["claims"], F, V)):
            out[c["id"]] = v if (v is not None and decide(i, r)) else fallback(c)
        return out

    def predict(self, name: str, t: dict, rng: Optional[np.random.Generator] = None) -> Dict[str, str]:
        F, V = feats(t)
        has = [i for i, v in enumerate(V) if v is not None]
        if name == "majority_prior":
            return self._apply(t, F, V, lambda i, r: False)
        if name == "evidence_apply":
            return self._apply(t, F, V, lambda i, r: True)
        if name == "claim_count_prior":
            rng = rng or np.random.default_rng(self.seed)
            k = min(int(rng.choice(self.k_dist)), len(has))
            pick = set(rng.permutation(has)[:k].tolist()) if has else set()
            return self._apply(t, F, V, lambda i, r: i in pick)
        if name in ("positional", "lexical_overlap", "gb_all_nonstory"):
            cols = {"positional": POS, "lexical_overlap": LEX, "gb_all_nonstory": ALL}[name]
            dec = dict(zip(has, self.gb[name].predict(F[has][:, cols]))) if has else {}
            return self._apply(t, F, V, lambda i, r: bool(dec.get(i, 0)))
        if name == "entity_blind":
            if not has:
                return self._apply(t, F, V, lambda i, r: False)
            Xs = hstack([csr_matrix(F[has][:, POS]), self.vec.transform([delex(t["evidence"])] * len(has))]).tocsr()
            dec = dict(zip(has, self.eb.predict(Xs)))
            return self._apply(t, F, V, lambda i, r: bool(dec.get(i, 0)))
        if name == "template_nn":
            d = delex(t["evidence"])
            return self._apply(t, F, V, lambda i, r: bool(self.tpl_rule.get((d, t["claims"][i]["attr"], int(np.sign(r[0])), int(r[6])), 0)))
        raise ValueError(name)
