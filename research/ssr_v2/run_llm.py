"""V2 LLM runner (Ollama only; NOT to be started before G9 passes and the user approves GPU time).
Resumable. One model at a time; waits while the GPU is busy; requires 100% GPU placement (else the model is skipped, nothing analysed).
Records per call: model digest, prompt sha256, prompt/completion tokens, wall seconds, GPU utilisation before the call, retries, error.
  python -m research.ssr_v2.run_llm --stage A [--models ...] [--limit N]
Stage A (core): K1, K2, K4, PG, S0 on test_main (K2 only on pairs where neither member is blocked) + set_valued for K1 and PG.
Stage B: K1-fs, K3a, K3b, K1-delta (100-item subsample) on test_main; transforms are run by a separate invocation on results/v2/transforms."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, time
import ollama
from . import prompts as P
from .build import DATA

RES = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results", "v2")
RAW = os.path.join(RES, "raw")
MODELS = ["qwen2.5:7b", "llama3:latest", "qwen3:8b", "mistral:7b"]
STAGES = {"A": [("K1", "test_main"), ("K2", "test_main"), ("K4", "test_main"), ("PG", "test_main"), ("S0", "test_main"), ("K1", "set_valued"), ("PG", "set_valued")],
          "B": [("K1-fs", "test_main"), ("K3a", "test_main"), ("K3b", "test_main"), ("K1-delta", "test_main_sub100")],
          "T": [("K1", f"tf:{n}") for n in ("entity_same_pool", "entity_cross_pool", "narration_shuffle", "evidence_paraphrase", "lexical_story", "novel_templates", "irrelevant_context", "claim_order_intro")],
          "E": [("K1", "external"), ("PG", "external"), ("S0", "external")]}


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def gpu():
    r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True)
    u, m = [int(x) for x in r.stdout.strip().split(",")]
    loaded = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.strip().splitlines()[1:]
    return u, m, loaded


def wait_free(who):
    waited = False
    while True:
        u, m, loaded = gpu()
        if u < 15 and m < 1500 and not loaded:
            if waited:
                log("GPU free, continuing")
            return
        if not waited:
            log(f"GPU busy (util {u}%, {m} MiB, loaded={len(loaded)}); waiting before {who}")
        waited = True
        time.sleep(60)


def fits(model):
    for l in subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout.strip().splitlines()[1:]:
        if l.startswith(model):
            return "100% GPU" in l, l
    return False, "(not listed)"


def load(name):
    if name.startswith("tf:"):
        d = os.path.join(DATA, "transforms", name[3:])
        T = [json.loads(l) for l in open(os.path.join(d, "test_main_sub50.task.jsonl"))]
        G = {json.loads(l)["item_id"]: json.loads(l) for l in open(os.path.join(d, "test_main_sub50.gold.jsonl"))}
        return T, G, json.load(open(os.path.join(d, "test_main_sub50.pgprior.json")))
    base = name.replace("_sub100", "")
    T = [json.loads(l) for l in open(os.path.join(DATA, f"{base}.task.jsonl"))]
    G = {json.loads(l)["item_id"]: json.loads(l) for l in open(os.path.join(DATA, f"{base}.gold.jsonl"))}
    PG = json.load(open(os.path.join(DATA, f"{base}.pgprior.json")))
    if name.endswith("_sub100"):
        keep = sorted({t["pair_id"] for t in T})[:50]
        T = [t for t in T if t["pair_id"] in keep]
    return T, G, PG


def shots():
    T, G, _ = load("train")
    pick, want = [], [("resolving", 1), ("blocked", 2), ("resolving", 3)]
    for cat, d in want:
        for t in sorted(T, key=lambda x: x["item_id"]):
            g = G[t["item_id"]]
            if g["meta"]["category"] == cat and g["meta"]["depth"] == d and g["meta"]["n_events"] <= 9 and t["item_id"] not in [p[0] for p in pick]:
                pick.append((t["item_id"], P.example_text(t, g["final"])))
                break
    return [p[1] for p in pick]


def eligible(cond, t, G):
    if cond != "K2":
        return True
    # K2 states no world laws: only pairs where neither member is blocked
    pid = t["pair_id"]
    return all(g["meta"]["category"] != "blocked" for g in G.values() if g["pair_id"] == pid and g["split"] == G[t["item_id"]]["split"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["A", "B", "T", "E"], required=True)
    ap.add_argument("--models", nargs="+", default=MODELS)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--split-override", default=None, help="run every condition on this split instead (dev smoke); raw goes to raw_<split>")
    a = ap.parse_args()
    raw_root = RAW + (f"_{a.split_override}" if a.split_override else "")
    client = ollama.Client(timeout=900)
    sh = shots()
    ph = P.prompt_hashes()
    skipped = {}
    for model in a.models:
        digest = [m for m in client.list()["models"] if m["model"] == model][0]["digest"]
        think = False if model.startswith("qwen3") else None
        tag = model.replace(":", "_")
        wait_free(model)
        checked = False
        for cond, split in [(c, a.split_override or sp) for c, sp in STAGES[a.stage]]:
            T, G, PG = load(split)
            T = [t for t in T if eligible(cond, t, G)][: a.limit]
            path = os.path.join(raw_root, cond, f"{split.replace(':', '_')}__{tag}.jsonl")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            have = {json.loads(l)["key"] for l in open(path)} if os.path.exists(path) else set()
            with open(path, "a") as out:
                for t in T:
                    key = f"{cond}|{t['item_id']}"
                    if key in have:
                        continue
                    prompt = P.build_prompt(cond, t, prior=PG.get(t["item_id"]) if cond == "PG" else None, shots=sh if cond == "K1-fs" else None)
                    util = gpu()[0]
                    err, r, tries = None, {"content": "", "prompt_eval_count": None, "eval_count": None}, 0
                    t0 = time.time()
                    for tries in range(3):
                        try:
                            kw = dict(model=model, messages=[{"role": "user", "content": prompt}], format=P.schema_for(cond, t),
                                      options=dict(temperature=0.0, seed=0, num_ctx=6144, num_predict=500))
                            if think is not None:
                                kw["think"] = think
                            resp = client.chat(**kw)
                            r = {"content": resp["message"]["content"], "prompt_eval_count": resp.get("prompt_eval_count"), "eval_count": resp.get("eval_count")}
                            err = None
                            break
                        except Exception as e:
                            err = repr(e)
                    wall = round(time.time() - t0, 3)
                    if not checked:
                        ok, line = fits(model)
                        log(f"{model} placement: {line}")
                        if not ok:
                            skipped[model] = line
                            subprocess.run(["ollama", "stop", model])
                            break
                        checked = True
                    out.write(json.dumps({"key": key, "cond": cond, "split": split, "item_id": t["item_id"], "model": model, "model_digest": digest,
                                          "temperature": 0.0, "seed": 0, "num_ctx": 6144, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                                          "prompt_hashes": ph, "prompt_tokens": r["prompt_eval_count"], "completion_tokens": r["eval_count"], "wall_s": wall,
                                          "gpu_util_before": util, "retries": tries if err is None else tries + 1, "error": err, "content": r["content"]}) + "\n")
                    out.flush()
            if model in skipped:
                break
            log(f"{model} {cond}/{split}: done")
        subprocess.run(["ollama", "stop", model], capture_output=True)
        log(f"{model}: finished, unloaded")
    json.dump(skipped, open(os.path.join(RES, f"run_llm_skipped_stage{a.stage}.json"), "w"))
    log("ALL DONE; skipped:", skipped)


if __name__ == "__main__":
    main()
