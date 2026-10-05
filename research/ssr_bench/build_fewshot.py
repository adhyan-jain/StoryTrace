"""Builds the frozen 3-shot examples for P2/P4 from the TRAIN split (outside systems/: it reads gold)."""
import json, os
from .io import load_gold, load_task
from .systems.common import PROMPTS


def answer(t, g):
    out = {}
    for c in t["claims"]:
        l = g["labels"][c["id"]]
        out[c["id"]] = "KEEP" if l["label"] == "KEEP" else ("CONFLICT" if l["label"] == "CONFLICT" else f"REVISE: {l['value']}")
    return out


def main():
    T, G = load_task("train"), load_gold("train")
    want = [lambda g: g["meta"]["category"] == "resolving" and g["meta"]["scope_bounded"] and g["meta"]["n_changed"] == 2,
            lambda g: g["meta"]["category"] == "contradictory" and g["meta"]["evidence_kind"].startswith("event"),
            lambda g: g["meta"]["category"] == "irrelevant" and g["meta"]["evidence_kind"] == "event:move"]
    shots = []
    for w in want:
        for t, g in zip(T, G):
            if w(g):
                shots.append({"task": t, "answer": answer(t, g)})
                break
    assert len(shots) == 3
    json.dump(shots, open(os.path.join(PROMPTS, "fewshot.json"), "w"), indent=1, sort_keys=True)
    print("fewshot items:", [s["task"]["item_id"] for s in shots])


if __name__ == "__main__":
    main()
