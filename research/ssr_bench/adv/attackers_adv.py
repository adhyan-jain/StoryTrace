"""Non-LLM attackers for the adversarial audit (Addendum C). CPU only.

Every attacker returns, per item, {claim_id: (label, value)} exactly like an LLM, so the existing value-aware metrics apply.
Learned attackers are trained on the `train` split only. They read TASK records at inference; the only attacker that touches
gold at inference is `delta_size_oracle`, which is a labelled DIAGNOSTIC (told the true number of changed claims).

None of these replays the story except the `symbolic*` references and `world_rule_partial` (the ablation ladder).
"""
from __future__ import annotations
import itertools, re
from typing import Dict, List, Optional, Tuple
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from scipy.sparse import csr_matrix, hstack
from ..io import load_gold, load_task
from ..leakage import delex
from ..systems import rules, symbolic as S

Pred = Dict[str, Tuple[str, str]]
ATTRS = ["loc", "holder", "proploc", "injured"]
CATS = ["resolving", "irrelevant", "contradictory"]


def ev_slot(t: dict) -> int:
    return int(re.search(r"\d+", t["evidence"]).group())


def _toks(s: str) -> set:
    return set(re.findall(r"[a-z]+", s.lower()))


def claim_feats(t: dict) -> np.ndarray:
    """Task-only per-claim features. Columns: 0 slot-ev, 1 slot>=ev, 2 slot==ev, 3 slot==ev-1, 4 idx, 5 attr,
    6 entity mentioned, 7 value mentioned, 8 token jaccard(evidence, claim statement)."""
    e, ev = t["evidence"], ev_slot(t)
    et = _toks(re.sub(r"^[^,:]*[,:]", "", e))
    rows = []
    for i, c in enumerate(t["claims"]):
        ct = _toks(c["statement"]) - {"on", "day", "is", "in", "the", "held", "by", "located"}
        jac = len(et & ct) / max(1, len(et | ct))
        ment = int(re.search(rf"\b{re.escape(c['entity'])}\b", e) is not None)
        vment = int(re.search(rf"\b{re.escape(c['value'])}\b", e) is not None) if c["value"] not in ("injured", "unharmed", "nobody") else 0
        rows.append([c["slot"] - ev, int(c["slot"] >= ev), int(c["slot"] == ev), int(c["slot"] == ev - 1), i,
                     ATTRS.index(c["attr"]), ment, vment, jac])
    return np.array(rows, dtype=float)


POS = [0, 1, 2, 3, 4, 5]
LEX = [5, 6, 7, 8, 1]
MENT = [0, 1, 2, 3, 4, 5, 6, 7]


def _label(g: dict, cid: str) -> str:
    return g["labels"][cid]["label"]


class Attackers:
    NAMES = ["majority_prior", "claim_count_prior", "mention_rule", "positional", "lexical_overlap", "delta_size_oracle",
             "category_then_select", "entity_blind", "template_nn", "triple_aware", "ledger_lookup", "ledger_lookup_priv",
             "world_rule_partial:no_persistence", "world_rule_partial:no_injury_rule", "world_rule_partial:no_preconditions",
             "world_rule_partial:no_travel", "world_rule_partial:none_ablated"]

    def __init__(self, seed: int = 0):
        self.seed = seed
        T, G = load_task("train"), load_gold("train")
        X = np.vstack([claim_feats(t) for t in T])
        y = np.array([_label(g, c["id"]) for t, g in zip(T, G) for c in t["claims"]])
        self.prior_attr = {a: max(set(y[X[:, 5] == i]), key=list(y[X[:, 5] == i]).count) for i, a in enumerate(ATTRS)}
        self.k_dist = np.array([sum(v["label"] != "KEEP" for v in g["labels"].values()) for g in G])
        self.gb = {}
        for name, cols in (("positional", POS), ("lexical_overlap", LEX)):
            self.gb[name] = GradientBoostingClassifier(random_state=seed).fit(X[:, cols], y)
        self.gb_change = GradientBoostingClassifier(random_state=seed).fit(X[:, MENT], (y != "KEEP").astype(int))
        # category classifier on delexicalised evidence text (no gold at inference)
        self.cat_vec = CountVectorizer(ngram_range=(1, 2), min_df=2)
        ycat = [g["meta"]["category"] for g in G]
        self.cat_lr = LogisticRegression(max_iter=3000).fit(self.cat_vec.fit_transform([delex(t["evidence"]) for t in T]), ycat)
        # entity-blind per-claim LR: delexicalised evidence char n-grams + position features
        self.eb_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=3)
        S_ = hstack([csr_matrix(self._eb_dense(X)), self.eb_vec.fit_transform([delex(t["evidence"]) for t in T for _ in t["claims"]])]).tocsr()
        self.eb_lr = LogisticRegression(max_iter=4000).fit(S_, y)
        # template memorisation: (delex evidence, attr, slot relation, mention) -> majority train label
        table: Dict[tuple, Dict[str, int]] = {}
        for t, g, f in zip(T, G, [claim_feats(t) for t in T]):
            d = delex(t["evidence"])
            for c, r in zip(t["claims"], f):
                k = (d, c["attr"], int(np.sign(r[0])), int(r[6]))
                table.setdefault(k, {}).setdefault(_label(g, c["id"]), 0)
                table[k][_label(g, c["id"])] += 1
        self.tpl = {k: max(v, key=v.get) for k, v in table.items()}

    @staticmethod
    def _eb_dense(X: np.ndarray) -> np.ndarray:
        return X[:, MENT]

    # ---------------------------------------------------------------- simple priors
    def majority_prior(self, t: dict) -> Pred:
        return {c["id"]: (self.prior_attr[c["attr"]], "") for c in t["claims"]}

    def claim_count_prior(self, t: dict, rng: np.random.Generator) -> Pred:
        k = int(rng.choice(self.k_dist))
        pick = set(rng.permutation(len(t["claims"]))[:k].tolist())
        return {c["id"]: (("REVISE", "") if i in pick else ("KEEP", "")) for i, c in enumerate(t["claims"])}

    def mention_rule(self, t: dict) -> Pred:
        return rules.mention_rule(t)

    def _gb(self, name: str, t: dict) -> Pred:
        X = claim_feats(t)[:, POS if name == "positional" else LEX]
        lab = self.gb[name].predict(X)
        return {c["id"]: (str(l), "") for c, l in zip(t["claims"], lab)}

    # ---------------------------------------------------------------- category-then-select family
    def _cat_proba(self, t: dict) -> np.ndarray:
        p = self.cat_lr.predict_proba(self.cat_vec.transform([delex(t["evidence"])]))[0]
        return np.array([p[list(self.cat_lr.classes_).index(c)] for c in CATS])

    def _select(self, t: dict, cat: str, k: int) -> Pred:
        out = {c["id"]: ("KEEP", "") for c in t["claims"]}
        score = self.gb_change.predict_proba(claim_feats(t)[:, MENT])[:, 1]
        order = np.argsort(-score)
        if cat == "resolving":
            for i in order[:k]:
                out[t["claims"][i]["id"]] = ("REVISE", "")
        elif cat == "contradictory":
            out[t["claims"][order[0]]["id"]] = ("CONFLICT", "")
        return out

    def category_then_select(self, t: dict) -> Pred:
        cat = CATS[int(np.argmax(self._cat_proba(t)))]
        return self._select(t, cat, 1)

    def delta_size_oracle(self, t: dict, g: dict) -> Pred:
        """DIAGNOSTIC (uses gold n_changed and gold category): upper bound on how much knowing the delta size would help."""
        return self._select(t, g["meta"]["category"], max(1, g["meta"]["n_changed"]))

    def triple_aware(self, tasks: List[dict]) -> Dict[str, Pred]:
        """Exploits 'each story has exactly one resolving / irrelevant / contradictory item' using only item-id grouping."""
        by_story: Dict[str, List[dict]] = {}
        for t in tasks:
            by_story.setdefault(t["item_id"].rsplit("-", 1)[0], []).append(t)
        out = {}
        for sid, ts in by_story.items():
            P = np.log(np.array([self._cat_proba(t) for t in ts]) + 1e-9)
            if len(ts) == 3:
                best = max(itertools.permutations(range(3)), key=lambda perm: sum(P[i, perm[i]] for i in range(3)))
                cats = [CATS[j] for j in best]
            else:
                cats = [CATS[int(np.argmax(P[i]))] for i in range(len(ts))]
            for t, c in zip(ts, cats):
                out[t["item_id"]] = self._select(t, c, 1)
        return out

    # ---------------------------------------------------------------- entity-blind and template memorisation
    def entity_blind(self, t: dict) -> Pred:
        X = claim_feats(t)
        Xs = hstack([csr_matrix(self._eb_dense(X)), self.eb_vec.transform([delex(t["evidence"])] * len(t["claims"]))]).tocsr()
        return {c["id"]: (str(l), "") for c, l in zip(t["claims"], self.eb_lr.predict(Xs))}

    def template_nn(self, t: dict) -> Pred:
        d, F = delex(t["evidence"]), claim_feats(t)
        return {c["id"]: (self.tpl.get((d, c["attr"], int(np.sign(r[0])), int(r[6])), "KEEP"), "") for c, r in zip(t["claims"], F)}

    # ---------------------------------------------------------------- ledger-only solver (NO story replay)
    @staticmethod
    def ledger_lookup(t: dict, privileged: bool = False) -> Pred:
        """Uses ONLY the evidence sentence (train grammar) and the ledger claims' prior values. No story is read."""
        keep = {c["id"]: ("KEEP", "") for c in t["claims"]}
        pe = S._parse_evidence(t["evidence"], S._pools(privileged))
        if pe is None:
            return keep
        claims, day = t["claims"], pe[1]
        out = dict(keep)

        def find(attr, ent, slot):
            return next((c for c in claims if (c["attr"], c["entity"], c["slot"]) == (attr, ent, slot)), None)

        def revise(attr, ent, new, cond=lambda c: True):
            for c in claims:
                if c["attr"] == attr and c["entity"] == ent and c["slot"] >= day and c["value"].lower() != new.lower() and cond(c):
                    out[c["id"]] = ("REVISE", new.lower())

        def near(attr, ent, slot):
            cs = [c for c in claims if c["attr"] == attr and c["entity"] == ent and c["slot"] <= slot]
            return max(cs, key=lambda c: c["slot"]) if cs else None

        if pe[0] == "assert":
            attr, ent, val = pe[2]
            c = find(attr, ent, day)
            if c and c["value"].lower() != val.lower():
                out[c["id"]] = ("CONFLICT", "")
            return out
        kind, g = pe[2]
        a, b, p, L = g.get("a"), g.get("b"), g.get("p"), g.get("L")
        if kind == "move":
            c = find("injured", a, day - 1)
            if c and c["value"] == "injured":
                out[c["id"]] = ("CONFLICT", "")
                return out
            revise("loc", a, L)
            for h in [c for c in claims if c["attr"] == "holder" and c["value"] == a]:
                for pc in claims:
                    if pc["attr"] == "proploc" and pc["entity"] == h["entity"] and pc["slot"] >= day and pc["value"].lower() != L.lower():
                        nh = near("holder", pc["entity"], pc["slot"])
                        if nh and nh["value"] == a:
                            out[pc["id"]] = ("REVISE", L.lower())
        elif kind in ("give", "pickup", "drop"):
            need = {"give": lambda v: v == a, "pickup": lambda v: v == "nobody", "drop": lambda v: v == a}[kind]
            c = find("holder", p, day - 1)
            if c and not need(c["value"]):
                out[c["id"]] = ("CONFLICT", "")
                return out
            new = {"give": b, "pickup": a, "drop": "nobody"}[kind]
            revise("holder", p, new)
            if kind == "drop":
                la = near("loc", a, day)
                if la:
                    revise("proploc", p, la["value"])
        elif kind == "injure":
            revise("injured", a, "injured")
        elif kind == "heal":
            revise("injured", a, "unharmed")
        return out

    # ---------------------------------------------------------------- dispatch
    def predict(self, name: str, tasks: List[dict], golds: Optional[List[dict]] = None) -> Dict[str, Pred]:
        G = {g["item_id"]: g for g in golds} if golds else {}
        rng = np.random.default_rng(self.seed)
        if name == "triple_aware":
            return self.triple_aware(tasks)
        out = {}
        for t in tasks:
            i = t["item_id"]
            if name == "majority_prior":
                out[i] = self.majority_prior(t)
            elif name == "claim_count_prior":
                out[i] = self.claim_count_prior(t, rng)
            elif name == "mention_rule":
                out[i] = self.mention_rule(t)
            elif name in ("positional", "lexical_overlap"):
                out[i] = self._gb(name, t)
            elif name == "delta_size_oracle":
                out[i] = self.delta_size_oracle(t, G[i])
            elif name == "category_then_select":
                out[i] = self.category_then_select(t)
            elif name == "entity_blind":
                out[i] = self.entity_blind(t)
            elif name == "template_nn":
                out[i] = self.template_nn(t)
            elif name == "ledger_lookup":
                out[i] = self.ledger_lookup(t)
            elif name == "ledger_lookup_priv":
                out[i] = self.ledger_lookup(t, privileged=True)
            elif name.startswith("world_rule_partial:"):
                from .symbolic_ablate import predict_ablated
                flag = name.split(":")[1]
                flags = dict(persistence=True, injury_rule=True, preconditions=True, travel=True)
                if flag != "none_ablated":
                    flags[flag.replace("no_", "")] = False
                out[i] = predict_ablated(t, **flags)[0]
            elif name == "always_keep":
                out[i] = rules.always_keep(t)
            elif name == "symbolic":
                out[i] = S.predict(t)[0]
            elif name == "symbolic_privileged_grammar":
                out[i] = S.predict(t, privileged=True)[0]
            else:
                raise ValueError(name)
        return out
