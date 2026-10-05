"""External validation set: REAL execution of filesystem + git command logs (separate from the synthetic benchmark).
Gold comes from actually running the commands in a sandboxed temp dir (no network, empty env, fixed git identity); causal depth is measured
EMPIRICALLY by deleting each earlier command and re-executing. Items use the same task/gold schema as the main benchmark (split name `external`).
Only a restricted command grammar is ever executed (generated here, never model output)."""
from __future__ import annotations
import json, os, random, re, subprocess, tempfile
from collections import defaultdict
from typing import Dict, List, Tuple
from .build import DATA, write

ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null", "LC_ALL": "C",
       "GIT_AUTHOR_NAME": "a", "GIT_AUTHOR_EMAIL": "a@x", "GIT_COMMITTER_NAME": "a", "GIT_COMMITTER_EMAIL": "a@x",
       "GIT_AUTHOR_DATE": "2000-01-01T00:00:00", "GIT_COMMITTER_DATE": "2000-01-01T00:00:00"}
ALLOWED = re.compile(r"^(mkdir -p [\w/]+|cd [\w./]+|touch [\w./]+|echo \w+ >> ?[\w./]+|echo \w+ > ?[\w./]+|rm [\w./]+|git init -q -b main|git add [\w./]+|"
                     r"git commit -q -m \w+|git commit -q --allow-empty -m \w+|git checkout -q -b \w+|git checkout -q \w+)$")


def execute(cmds: List[str]) -> Tuple[str, str]:
    for c in cmds:
        assert ALLOWED.match(c), f"command outside the restricted grammar: {c}"
    d = tempfile.mkdtemp(prefix="ssr_ext_")
    root = os.path.join(d, "work")
    os.mkdir(root)
    r = subprocess.run(["bash", "-c", "\n".join(cmds) + '\necho "__CWD__:$(pwd -P)"\n'], cwd=root, env=dict(ENV, HOME=d), capture_output=True, text=True, timeout=30)
    m = re.search(r"__CWD__:(.*)", r.stdout)
    cwd = os.path.relpath(m.group(1).strip(), os.path.realpath(root)) if m else "?"
    return root, cwd


def git(root: str, *args: str) -> str:
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True, env=dict(ENV, HOME=root), timeout=30)
    return r.stdout.strip() if r.returncode == 0 else ""


def probe(root: str, cwd: str, kind: str, arg: str) -> str:
    p = os.path.join(root, arg) if arg else root
    if kind == "exists":
        return "yes" if os.path.exists(p) else "no"
    if kind == "lastline":
        return open(p).read().strip().splitlines()[-1] if os.path.isfile(p) and open(p).read().strip() else "missing"
    if kind == "lines":
        return str(len(open(p).read().splitlines())) if os.path.isfile(p) else "0"
    if kind == "cwd":
        return "." if cwd == "." else cwd
    if kind == "branch":
        return git(root, "symbolic-ref", "--short", "HEAD") or "none"
    if kind == "commits":
        return git(root, "rev-list", "--count", arg) or "0"
    raise ValueError(kind)


def state(cmds: List[str], claims: List[Tuple[str, str]]) -> Dict[str, str]:
    root, cwd = execute(cmds)
    return {f"{k}:{a}": probe(root, cwd, k, a) for k, a in claims}


QTXT = {"exists": "After all commands, does the path '{a}' exist? (yes/no)", "cwd": "After all commands, what is the current working directory, relative to /work? ('.' means /work itself)",
        "branch": "After all commands, which git branch is checked out? ('none' if there is no repository)", "commits": "How many commits does branch '{a}' have? (0 if it does not exist)",
        "lastline": "What is the last line of '{a}'? ('missing' if the file does not exist or is empty)", "lines": "How many lines does '{a}' have? (0 if missing)"}
DOM = {"exists": ["yes", "no"], "branch": ["main", "dev", "feat", "none"], "commits": [str(i) for i in range(0, 8)], "lines": [str(i) for i in range(0, 8)],
       "lastline": ["one", "two", "three", "missing"]}


def dom(kind, dirs):
    return {"cwd": dirs}.get(kind) or DOM[kind]


# ----------------------------------------------------------------------------- families
def fam_A(rng, chain, filler):
    A, B = rng.sample(["alpha", "beta", "gamma", "delta"], 2)
    pre = [f"mkdir -p {A}/sub", f"mkdir -p {B}/sub"] + ["touch top.txt"] * 0
    pre += [f"touch top{i}.txt" for i in range(filler)]
    tail = ["cd sub", "cd .."][: chain - 1] if chain > 1 else []
    if chain == 3:
        tail = ["cd sub", "cd .."]
    mk = lambda X: pre + [f"cd {X}"] + tail
    ev = "touch note.txt"
    claims = [("exists", f"{A}/note.txt"), ("exists", f"{B}/note.txt"), ("exists", f"{A}/sub/note.txt"), ("exists", f"{B}/sub/note.txt"), ("exists", "note.txt"),
              ("cwd", ""), ("exists", "top0.txt"), ("exists", f"{A}/top0.txt"), ("exists", f"{B}/top0.txt"), ("exists", f"{A}/sub/top0.txt")]
    dirs = [".", A, B, f"{A}/sub", f"{B}/sub"]
    return mk(A), mk(B), len(pre) + 1 + len(tail), ev, claims, dirs, len(pre)


def fam_B(rng, chain, filler):
    X, Y = "dev", "feat"
    base = ["git init -q -b main", "touch f.txt", "git add f.txt", "git commit -q -m c1"] + [f"touch pad{i}.txt" for i in range(filler)]
    tail = ["git commit -q --allow-empty -m c2", "git commit -q --allow-empty -m c3"][: chain - 1]
    mk = lambda br: base + [f"git checkout -q -b {br}"] + tail
    ev = "git commit -q --allow-empty -m e"
    claims = [("branch", ""), ("commits", "main"), ("commits", X), ("commits", Y), ("exists", "f.txt"), ("exists", "pad0.txt"), ("exists", "g.txt"), ("lines", "f.txt")]
    return mk(X), mk(Y), len(base) + 1 + len(tail), ev, claims, ["."], len(base)


def fam_C(rng, chain, filler):
    pre = ["echo one > f.txt"] + [f"touch pad{i}.txt" for i in range(filler)]
    mid = ["echo two >> f.txt", "echo two >> f.txt"][: chain - 1]
    piv_a, piv_b = "rm f.txt", "touch g.txt"
    mk = lambda pv: pre + mid + [pv]
    ev = "echo three >> f.txt"
    claims = [("exists", "f.txt"), ("exists", "g.txt"), ("lines", "f.txt"), ("lastline", "f.txt"), ("exists", "pad0.txt"), ("lines", "g.txt")]
    return mk(piv_a), mk(piv_b), len(pre) + len(mid) + 1, ev, claims, ["."], len(pre)


def build_pairs(seed="ssr-v2/external", n_each=14):
    rng = random.Random(seed)
    out = []
    for fam, f in (("A", fam_A), ("B", fam_B), ("C", fam_C)):
        combos = [(c, fl) for c in (1, 2, 3) for fl in (1, 2, 3, 4)]
        rng.shuffle(combos)
        for chain, filler in combos:
            s1, s2, k, ev, claims, dirs, piv = f(rng, chain, filler)
            full1, full2 = s1[:k] + [ev] + s1[k:], s2[:k] + [ev] + s2[k:]
            cl = [(kk, a) for kk, a in claims]
            p1, p2 = state(s1, cl), state(s2, cl)
            f1, f2 = state(full1, cl), state(full2, cl)
            diff = [x for x in f1 if f1[x] != f2[x]]
            r1 = {x: f1[x] for x in f1 if f1[x] != p1[x]}
            r2 = {x: f2[x] for x in f2 if f2[x] != p2[x]}
            if not diff or r1 == r2:
                continue
            def revision_of(script, kk):            # claims whose answer changes because of the extra command
                with_ev = script[:kk] + [ev] + script[kk:]
                a0, a1 = state(script, cl), state(with_ev, cl)
                return {x: a1[x] for x in a1 if a1[x] != a0[x]}

            def depth(script, kk):                  # empirical: earlier commands whose deletion changes the REVISION (real re-execution)
                base = revision_of(script, kk)
                n = 0
                for i in range(len(script)):
                    sub = [c for j, c in enumerate(script) if j != i]
                    n += revision_of(sub, kk - (1 if i < kk else 0)) != base
                return n
            d1, d2 = depth(s1, k), depth(s2, k)
            if d1 != d2:
                continue
            out.append(dict(fam=fam, S1=s1, S2=s2, k=k, ev=ev, claims=cl, dirs=dirs, p1=p1, p2=p2, f1=f1, f2=f2, depth=d1, chain=chain, filler=filler))
    return out


def to_items(pairs, split="external", seed="ssr-v2/external/assign"):
    rng = random.Random(seed)
    pairs = list(pairs)
    rng.shuffle(pairs)
    T, G, PG = [], [], {}
    for i, p in enumerate(pairs):
        pid = f"{i:04d}"
        order = [("S1", p["S1"], p["p1"], p["f1"]), ("S2", p["S2"], p["p2"], p["f2"])]
        if rng.random() < 0.5:
            order.reverse()
        text = f"One more command was also run, immediately before step {p['k'] + 1}: `{p['ev']}`."
        for member, (orig, script, prior, final) in zip(("A", "B"), order):
            iid = f"{split}-{pid}-{member}"
            ids = {x: f"c{j + 1}" for j, x in enumerate(final)}
            claims = [{"id": ids[f'{kk}:{a}'], "entity": a, "attr": kk, "slot": 0,
                       "question": QTXT[kk].format(a=a), "domain": dom(kk, p["dirs"])} for kk, a in p["claims"]]
            T.append({"item_id": iid, "pair_id": pid, "member": member, "story": [f"Step {j + 1}: {c}" for j, c in enumerate(script)],
                      "evidence": text, "claims": claims, "chars": [], "props": [], "locs": []})
            fin = {ids[x]: final[x] for x in final}
            pri = {ids[x]: prior[x] for x in prior}
            lab = {i2: ("REVISE" if fin[i2] != pri[i2] else "KEEP") for i2 in fin}
            G.append({"item_id": iid, "pair_id": pid, "member": member, "split": split, "prior": pri, "final": fin, "labels": lab, "valid_final": [fin],
                      "meta": {"category": "resolving" if any(v == "REVISE" for v in lab.values()) else "irrelevant", "depth": p["depth"], "anc_depth": p["depth"],
                               "n_events": len(script), "n_sentences": len(script), "n_changed": sum(v == "REVISE" for v in lab.values()), "evidence_slot": p["k"] + 1,
                               "evidence_kind": "command", "narration": "linear", "set_valued": False, "stratum": f"X_D{p['depth']}", "pivot_slot": 0,
                               "pair_cat": p["fam"], "origin": orig}, "world": {"evidence": {}}})
            PG[iid] = pri
    write(DATA, split, T, G, PG)
    return T, G


def replay_exec(t: dict) -> Dict[str, str]:
    """Text-only replay: execute the commands written in the task text (plus the extra command) in the sandbox and read each claim."""
    steps = [re.match(r"Step (\d+): (.*)", s).groups() for s in t["story"]]
    cmds = [c for _, c in steps]
    k = int(re.search(r"before step (\d+)", t["evidence"]).group(1)) - 1
    ev = re.search(r"`(.*)`", t["evidence"]).group(1)
    root, cwd = execute(cmds[:k] + [ev] + cmds[k:])
    return {c["id"]: probe(root, cwd, c["attr"], c["entity"]) for c in t["claims"]}


def main():
    pairs = build_pairs()
    by = defaultdict(list)
    for p in pairs:
        by[p["depth"]].append(p)
    print("candidate pairs by empirical depth:", {d: len(v) for d, v in sorted(by.items())}, "families:", {f: sum(1 for p in pairs if p["fam"] == f) for f in "ABC"})
    sel = []
    for d, v in sorted(by.items()):
        sel += v[:12]
    T, G = to_items(sel)
    from .scorers import score_item
    from .validators import validate_split
    ceil = [score_item(t, g, replay_exec(t))["semantic"] for t, g in zip(T, G)]
    # validators: story differs in exactly one command line, evidence/claims identical, revisions differ, depth equal
    v = validate_split(T, G)
    print("selected pairs:", len(sel), "items:", len(T), "replay-exec ceiling:", sum(ceil) / len(ceil), "validator violations:", v["pairs_with_violations"], list(v["violations"].items())[:2])


if __name__ == "__main__":
    main()
