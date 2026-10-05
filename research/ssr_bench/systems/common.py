"""Prompt construction, Ollama calling, and response parsing. Systems see TASK records only (never gold)."""
from __future__ import annotations
import hashlib, json, os, re, time
from typing import Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "prompts")


def read_prompt(name: str) -> str:
    return open(os.path.join(PROMPTS, name + ".txt")).read()


def prompt_hashes() -> Dict[str, str]:
    out = {}
    for fn in sorted(os.listdir(PROMPTS)):
        out[fn] = hashlib.sha256(open(os.path.join(PROMPTS, fn), "rb").read()).hexdigest()
    return out


def norm(v: str) -> str:
    v = v.strip().strip('."\'').lower()
    v = re.sub(r"^(in|to|at|by)\s+", "", v)
    v = re.sub(r"^the\s+", "", v)
    return v.strip()


def fmt_story(t) -> str:
    return "\n".join(t["story"])


def fmt_claims(t) -> str:
    return "\n".join(f'{c["id"]}. {c["statement"]}' for c in t["claims"])


def fmt_example(t, answer: Dict[str, str]) -> str:
    return (f"EXAMPLE\nSTORY\n{fmt_story(t)}\nNEW SENTENCE\n{t['evidence']}\nCLAIMS\n{fmt_claims(t)}\n"
            f"ANSWER\n{json.dumps(dict(sorted(answer.items(), key=lambda kv: int(kv[0][1:]))))}\n")


def build_prompt(system: str, t) -> str:
    rules = read_prompt("rules").strip()
    base = dict(rules=rules, story=fmt_story(t), evidence=t["evidence"], claims=fmt_claims(t))
    if system in ("p1_zero_shot_delta", "p3_regenerate"):
        return read_prompt(system).format(**base)
    if system in ("p2_explicit_revision", "p4_self_consistency"):
        shots = json.load(open(os.path.join(PROMPTS, "fewshot.json")))
        ex = "\n".join(fmt_example(s["task"], s["answer"]) for s in shots)
        return read_prompt("p2_explicit_revision").format(examples=ex, **base)
    if system == "p5_direct_qa":
        return read_prompt(system).format(rules=rules, story=base["story"], evidence=t["evidence"], question=t["probe"]["question"])
    raise ValueError(system)


def schema_for(system: str, t) -> dict:
    if system == "p5_direct_qa":
        return {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}
    ids = [c["id"] for c in t["claims"]]
    return {"type": "object", "properties": {i: {"type": "string"} for i in ids}, "required": ids}


def call_ollama(client, model: str, prompt: str, schema: dict, temperature: float, seed: int, think: Optional[bool]) -> dict:
    kw = dict(model=model, messages=[{"role": "user", "content": prompt}], format=schema,
              options=dict(temperature=temperature, seed=seed, num_ctx=6144, num_predict=500))
    if think is not None:
        kw["think"] = think
    t0 = time.time()
    r = client.chat(**kw)
    return {"content": r["message"]["content"], "prompt_tokens": r.get("prompt_eval_count"), "completion_tokens": r.get("eval_count"),
            "wall_s": round(time.time() - t0, 3)}


def parse_delta(system: str, content: str, t) -> Tuple[Dict[str, Tuple[str, str]], int]:
    """Returns ({claim_id: (label, value)}, n_unparseable_claims). Unparseable -> ('INVALID','')."""
    ids = [c["id"] for c in t["claims"]]
    prior = {c["id"]: norm(c["value"]) for c in t["claims"]}
    try:
        obj = json.loads(content)
        assert isinstance(obj, dict)
    except Exception:
        return {i: ("INVALID", "") for i in ids}, len(ids)
    out, bad = {}, 0
    for i in ids:
        raw = obj.get(i)
        if not isinstance(raw, str):
            out[i] = ("INVALID", ""); bad += 1; continue
        s = raw.strip()
        if system == "p3_regenerate":
            if s.upper().startswith("CONFLICT"):
                out[i] = ("CONFLICT", "")
            elif norm(s) == prior[i]:
                out[i] = ("KEEP", "")
            else:
                out[i] = ("REVISE", norm(s))
            continue
        u = s.upper()
        if u.startswith("KEEP"):
            out[i] = ("KEEP", "")
        elif u.startswith("CONFLICT"):
            out[i] = ("CONFLICT", "")
        elif u.startswith("REVISE"):
            out[i] = ("REVISE", norm(s.split(":", 1)[1] if ":" in s else ""))
        else:
            out[i] = ("INVALID", ""); bad += 1
    return out, bad


def parse_answer(content: str) -> str:
    try:
        return norm(str(json.loads(content).get("answer", "")))
    except Exception:
        return "<unparseable>"
