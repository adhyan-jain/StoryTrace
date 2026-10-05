"""LLM runner. Reads TASK files only. Appends raw responses to research/results/raw/<model>/<system>.jsonl (resumable).

python -m research.ssr_bench.run --model qwen2.5:7b --systems p1_zero_shot_delta p2_explicit_revision --splits dev --stories 3
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, time
import ollama
from .io import load_task
from .systems import common as C

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "raw")
K_SC, T_SC = 5, 0.7
STORIES_PER_SPLIT = {"test_id": 50}      # others: 20 (declared before any test-split run; see PREREGISTRATION addendum)
DEFAULT_STORIES = 20


def pick_stories(split: str, tasks, n: int):
    sids = sorted({t["item_id"].rsplit("-", 1)[0] for t in tasks}, key=lambda s: hashlib.sha256(f"subsample-v1/{s}".encode()).hexdigest())
    keep = set(sids[:n])
    return [t for t in tasks if t["item_id"].rsplit("-", 1)[0] in keep]


def done_keys(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return {json.loads(l)["key"] for l in f if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--systems", nargs="+", required=True)
    ap.add_argument("--splits", nargs="+", required=True)
    ap.add_argument("--stories", type=int, default=None, help="override stories per split (smoke tests only)")
    a = ap.parse_args()
    client = ollama.Client(timeout=600)
    digest = [m for m in client.list()["models"] if m["model"] == a.model][0]["digest"]
    think = False if a.model.startswith("qwen3") else None
    tag = a.model.replace(":", "_").replace("/", "_")
    os.makedirs(os.path.join(RAW, tag), exist_ok=True)
    ph = C.prompt_hashes()
    for system in a.systems:
        path = os.path.join(RAW, tag, f"{system}.jsonl")
        have = done_keys(path)
        n_new = 0
        with open(path, "a") as out:
            for split in a.splits:
                tasks = load_task(split)
                n = a.stories or STORIES_PER_SPLIT.get(split, DEFAULT_STORIES)
                for t in pick_stories(split, tasks, n):
                    samples = range(K_SC) if system == "p4_self_consistency" else [0]
                    for k in samples:
                        key = f"{split}|{t['item_id']}|{k}"
                        if key in have:
                            continue
                        prompt = C.build_prompt(system, t)
                        temp, seed = (T_SC, 1000 + k) if system == "p4_self_consistency" else (0.0, 0)
                        try:
                            r = C.call_ollama(client, a.model, prompt, C.schema_for(system, t), temp, seed, think)
                            err = None
                        except Exception as e:  # recorded, never silently dropped
                            r, err = {"content": "", "prompt_tokens": None, "completion_tokens": None, "wall_s": None}, repr(e)
                        out.write(json.dumps({"key": key, "split": split, "item_id": t["item_id"], "system": system, "model": a.model,
                                              "model_digest": digest, "sample": k, "temperature": temp, "seed": seed,
                                              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                                              "prompt_files": ph, "error": err, **r}) + "\n")
                        out.flush()
                        n_new += 1
        print(f"{a.model} {system}: {n_new} new calls -> {path}", flush=True)


if __name__ == "__main__":
    main()
