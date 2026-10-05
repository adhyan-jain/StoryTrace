"""Evaluate every non-LLM attacker on every test split (full splits). CPU only.
Writes research/results/adv/attacker_results.json (summaries + CIs) and attacker_items.json (per-item label errors)."""
from __future__ import annotations
import json, os, sys, time
from ..io import TEST_SPLITS
from .attackers_adv import Attackers
from .common import ADV, evaluate, load_split, summary_with_ci

REFS = ["always_keep", "symbolic", "symbolic_privileged_grammar"]


def main(data_dir=None, tag="orig", splits=None, names=None, b=500):
    A = Attackers()
    names = names or (Attackers.NAMES + REFS)
    splits = splits or TEST_SPLITS
    res, items = {}, {}
    for sp in splits:
        T, G = load_split(sp, data_dir)
        for n in names:
            if n == "symbolic_privileged_grammar" and sp != "test_ood_lex" and tag == "orig":
                continue
            t0 = time.time()
            ev = evaluate(A.predict(n, T, G), T, G)
            res.setdefault(n, {})[sp] = summary_with_ci(ev, b=b)
            items.setdefault(n, {})[sp] = {"label_ok": ev["label_ok"], "claim_err": ev["claim_err"]}
            print(f"{tag} {sp:20s} {n:36s} EM={res[n][sp]['delta_exact_match'][0]:.3f} labelEM={res[n][sp]['label_em']:.3f} "
                  f"f1={res[n][sp]['claim_macro_f1']:.3f} ({time.time() - t0:.1f}s)", flush=True)
    os.makedirs(ADV, exist_ok=True)
    json.dump(res, open(os.path.join(ADV, f"attacker_results_{tag}.json"), "w"))
    json.dump(items, open(os.path.join(ADV, f"attacker_items_{tag}.json"), "w"))


if __name__ == "__main__":
    main()
