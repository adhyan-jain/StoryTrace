"""GPU runner for the transformed sets (Addendum C Step 5): p2_explicit_revision x 4 models, Ollama only.
- Waits while the GPU is busy (shared machine); one model at a time; unloads each model when done.
- Rule B.1: after the first call `ollama ps` must show 100% GPU; otherwise the model is stopped and skipped (nothing analysed).
- Resumable. Raw records: research/results/adv/raw/<set>/<model>/p2_explicit_revision.jsonl (same fields as run.py).
Reads TASK files only (results/adv/data/<set>/test_id.task.jsonl).
  python -m research.ssr_bench.adv.run_llm [--models ...] [--sets ...] [--limit N]
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, time
import ollama
from ..io import load_task
from ..systems import common as C
from .common import ADV, ADV_DATA

SETS = ["identity", "entity_permute_same_pool", "claim_order_random", "lexical_paraphrase", "entity_permute_cross_pool",
        "story_order_shuffled", "novel_templates", "matched_pairs"]
MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
SYSTEM = "p2_explicit_revision"
RAWDIR = os.path.join(ADV, "raw")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def gpu_state():
    r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True)
    u, m = [int(x) for x in r.stdout.strip().split(",")]
    loaded = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.strip().splitlines()[1:]
    return u, m, loaded


def wait_free(who):
    waited = False
    while True:
        u, m, loaded = gpu_state()
        if u < 15 and m < 1500 and not loaded:
            if waited:
                log("GPU free, continuing")
            return
        if not waited:
            log(f"GPU busy (util {u}%, {m} MiB, loaded={len(loaded)}); waiting before {who}")
        waited = True
        time.sleep(60)


def fits_gpu(model):
    out = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.strip().splitlines()[1:]
    for l in out:
        if l.startswith(model):
            return "100% GPU" in l, l
    return False, "(model not listed)"


def done_keys(path):
    if not os.path.exists(path):
        return set()
    return {json.loads(l)["key"] for l in open(path) if l.strip()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--sets", nargs="+", default=SETS)
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    client = ollama.Client(timeout=600)
    ph = C.prompt_hashes()
    skipped = {}
    for model in a.models:
        digest = [m for m in client.list()["models"] if m["model"] == model][0]["digest"]
        think = False if model.startswith("qwen3") else None
        tag = model.replace(":", "_").replace("/", "_")
        wait_free(model)
        checked, n_new = False, 0
        for s in a.sets:
            tasks = load_task("test_id", os.path.join(ADV_DATA, s))[: a.limit]
            path = os.path.join(RAWDIR, s, tag, f"{SYSTEM}.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            have = done_keys(path)
            with open(path, "a") as out:
                for t in tasks:
                    key = f"{s}|{t['item_id']}|0"
                    if key in have:
                        continue
                    prompt = C.build_prompt(SYSTEM, t)
                    try:
                        r = C.call_ollama(client, model, prompt, C.schema_for(SYSTEM, t), 0.0, 0, think)
                        err = None
                    except Exception as e:
                        r, err = {"content": "", "prompt_tokens": None, "completion_tokens": None, "wall_s": None}, repr(e)
                    if not checked:
                        ok, line = fits_gpu(model)
                        log(f"{model} placement: {line}")
                        if not ok:
                            skipped[model] = line
                            subprocess.run(["ollama", "stop", model])
                            break
                        checked = True
                    out.write(json.dumps({"key": key, "set": s, "split": "test_id", "item_id": t["item_id"], "system": SYSTEM, "model": model,
                                          "model_digest": digest, "sample": 0, "temperature": 0.0, "seed": 0,
                                          "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(), "prompt_files": ph, "error": err, **r}) + "\n")
                    out.flush()
                    n_new += 1
            if model in skipped:
                break
            log(f"{model} {s}: done ({n_new} new calls so far)")
        subprocess.run(["ollama", "stop", model], capture_output=True)
        log(f"{model}: finished, unloaded")
    json.dump(skipped, open(os.path.join(ADV, "run_llm_skipped.json"), "w"))
    log("ALL DONE; skipped models:", skipped)


if __name__ == "__main__":
    main()
