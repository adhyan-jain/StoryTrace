"""Forensic audit of the AGY 'Selective State Revision' benchmark (src/, scripts/reproduce_all.py).

Each section prints evidence for one question in docs/BENCHMARK_FAILURE_AUDIT.md.
Run:  python research/archive/agy_ssr_v0/forensics.py   (chdirs into this archive directory itself)
"""
import ast
import copy
import inspect
import json
import os
import pathlib
import re
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ".")
from src.simulator.generator import StorySimulator, CHARACTERS, PROPS, LOCATIONS
from src.baselines.harness import BaselineHarness
from src.method.ssr_engine import SelectiveStateRevisionEngine
from src.evaluation.metrics import compute_revision_metrics
import scripts.reproduce_all as rep

TYPES = rep.INTERVENTION_TYPES
SYSTEMS = {
    "B1_SingleAnswer": BaselineHarness.run_b1_single_answer,
    "B2_Deterministic": BaselineHarness.run_b2_deterministic,
    "B3_ConstrainedLLM": BaselineHarness.run_b3_constrained_llm,
    "Proposed_SSR_Engine": SelectiveStateRevisionEngine().revise,
}


def episodes(n=100, seed=2026):
    sim = StorySimulator(seed=seed)
    return [sim.generate_episode(f"ep_{i}") for i in range(n)]


def hr(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def roles(e):
    st = e.initial_state
    c1 = next(c for (c, a), cl in st.claims.items() if a.startswith("possession") and cl.value == "held")
    c2 = next(c for c in st.entities if c != c1)
    return c1, c2, next(iter(st.props)), st.get_claim(c1, "location").value, st.get_claim(c2, "location").value


def delex(s, e):
    c1, c2, prop, l1, l2 = roles(e)
    for src, dst in ((c1, "<C1>"), (c2, "<C2>"), (prop, "<PROP>"), (l1, "<L1>"), (l2, "<L2>")):
        s = re.sub(rf"\b{re.escape(src)}\b", dst, s)
    return s


# ---------------------------------------------------------------- Q1
hr("Q1. What does each system receive? (function signatures)")
for name, fn in SYSTEMS.items():
    print(f"{name:22s} {inspect.signature(fn)}")
print("NarrativeEpisode.interventions[type] keys:", sorted(episodes(1)[0].interventions["RESOLVING"].keys()))


# ---------------------------------------------------------------- Q2
hr("Q2. Which intervention fields does each system actually READ? (instrumented dict)")


class Spy(dict):
    def __init__(self, d, log):
        super().__init__(d)
        self._log = log

    def __getitem__(self, k):
        self._log.add(k)
        return super().__getitem__(k)

    def get(self, k, default=None):
        self._log.add(k)
        return super().get(k, default)


ep0 = episodes(1)[0]
for name, fn in SYSTEMS.items():
    log = set()
    for t in TYPES:
        e = copy.deepcopy(ep0)
        e.interventions[t] = Spy(e.interventions[t], log)
        fn(e, t)
    print(f"{name:22s} reads {sorted(log)}  -> reads gold 'labels': {'labels' in log}")


# ---------------------------------------------------------------- Q3
hr("Q3. Causal test: corrupt ONLY the gold labels (evidence text unchanged)")
SWAP = {"KEEP": "REVISE", "REVISE": "KEEP", "CONFLICT": "INVALIDATE", "INVALIDATE": "CONFLICT"}
for name, fn in SYSTEMS.items():
    changed = followed = total = 0
    for e in episodes(20):
        for t in TYPES:
            clean = fn(e, t)
            e2 = copy.deepcopy(e)
            e2.interventions[t]["labels"] = {k: SWAP[v] for k, v in e2.interventions[t]["labels"].items()}
            pert = fn(e2, t)
            for k in clean:
                total += 1
                if pert[k] != clean[k]:
                    changed += 1
                    if pert[k] == e2.interventions[t]["labels"][k]:
                        followed += 1
    print(f"{name:22s} predictions changed: {changed}/{total} ({changed / total:.0%}); "
          f"of those, changed TO the corrupted gold: {followed}")


# ---------------------------------------------------------------- Q4
hr("Q4. Causal test: identical evidence+labels, only the intervention_type string differs")
for name, fn in SYSTEMS.items():
    diff = total = 0
    for e in episodes(20):
        for t in TYPES:
            for t_fake in ("IRRELEVANT", "CONTRADICTORY", "ENTITY_DISAMBIGUATING"):
                if t_fake == t:
                    continue
                e2 = copy.deepcopy(e)
                e2.interventions[t_fake] = e2.interventions[t]
                total += 1
                diff += fn(e, t) != fn(e2, t_fake)
    print(f"{name:22s} output changed: {diff}/{total} ({diff / total:.0%})")


# ---------------------------------------------------------------- Q5
hr("Q5. Distinct examples after replacing entity names with role placeholders")
eps = episodes(100)
items = set()
texts = {t: set() for t in TYPES}
pats = {t: set() for t in TYPES}
bases = set()
for e in eps:
    c1, c2, *_ = roles(e)
    rmap = {c1: "C1", c2: "C2"}
    base = " ".join(delex(s, e) for s in e.base_text)
    bases.add(base)
    for t in TYPES:
        it = e.interventions[t]
        txt = delex(it["text"], e)
        lab = tuple(sorted((rmap[k[0]], k[1].split(".")[0], v) for k, v in it["labels"].items()))
        items.add((base, t, txt, lab))
        texts[t].add(txt)
        pats[t].add(lab)
print(f"episodes={len(eps)}  intervention items={len(eps) * len(TYPES)}  "
      f"distinct base stories={len(bases)}  distinct delexicalised items={len(items)}")
for t in TYPES:
    print(f"  {t:22s} distinct texts={len(texts[t])} distinct gold patterns={len(pats[t])} | {next(iter(texts[t]))}")
print("Name pools:", len(CHARACTERS), "characters,", len(PROPS), "props,", len(LOCATIONS), "locations")


# ---------------------------------------------------------------- Q6
hr("Q6. Metrics on 1 episode (n=7) vs 100 episodes (n=700)")
for name, fn in SYSTEMS.items():
    out = []
    for n in (1, 100):
        P, G = [], []
        for e in episodes(n):
            for t in TYPES:
                P.append(fn(e, t))
                G.append(e.interventions[t]["labels"])
        out.append(compute_revision_metrics(P, G))
    same = all(abs(out[0][k] - out[1][k]) < 1e-12 for k in out[0])
    em = out[1]["delta_exact_match"]
    print(f"{name:22s} identical: {same}  EM={em:.4f} = {round(em * 7)}/7")


# ---------------------------------------------------------------- Q7
hr("Q7. Do the reported numbers reproduce exactly?")
reported = json.load(open("results/benchmark_summary.json"))
for name, fn in SYSTEMS.items():
    P, G = [], []
    for e in episodes(100):
        for t in TYPES:
            P.append(fn(e, t))
            G.append(e.interventions[t]["labels"])
    m = compute_revision_metrics(P, G)
    print(f"{name:22s} reproduces: {all(abs(m[k] - reported[name][k]) < 1e-9 for k in m)}")


# ---------------------------------------------------------------- Q8
hr("Q8. Any train/dev/test split?")
src = pathlib.Path("scripts/reproduce_all.py").read_text() + pathlib.Path("src/simulator/generator.py").read_text()
print("tokens matching split|train|test|dev|held_out:", re.findall(r"\b(split|train|test|dev|held[_ ]?out)\b", src, re.I))


# ---------------------------------------------------------------- Q9
hr("Q9. Shared logic between gold and systems")
for nm, s in (("SSR.revise", inspect.getsource(SelectiveStateRevisionEngine.revise)),
              ("B3", inspect.getsource(BaselineHarness.run_b3_constrained_llm)),
              ("B1", inspect.getsource(BaselineHarness.run_b1_single_answer)),
              ("B2", inspect.getsource(BaselineHarness.run_b2_deterministic))):
    body = s.split('"""', 2)[-1]
    print(f"{nm:10s} iterates inter['labels']: {'inter[\"labels\"]' in body}; "
          f"emits g_label: {'= g_label' in body or '\"CONFLICT\" in g_label' in body}; "
          f"branches on intervention_type: {bool(re.search(r'if .*intervention_type', body))}")
gen_src = inspect.getsource(StorySimulator.generate_episode)
print("Gold labels derived by simulating events? set_claim used after interventions begin:",
      "set_claim" in gen_src.split("# Generate 7")[1])


# ---------------------------------------------------------------- Q10
hr("Q10. Gold-label semantics on one episode")
e = episodes(1)[0]
print("prior state:", {f"{k[0]}.{k[1]}": c.value for k, c in e.initial_state.claims.items()})
print("base text:", " ".join(e.base_text))
for t in ("CONTRADICTORY", "TEMPORAL_RESOLVING", "ALTERNATIVE_RESOLVING", "ENTITY_DISAMBIGUATING"):
    nz = {f"{k[0]}.{k[1]}": v for k, v in e.interventions[t]["labels"].items() if v != "KEEP"}
    print(f"[{t}] evidence: {e.interventions[t]['text']}\n    gold non-KEEP: {nz}")


# ---------------------------------------------------------------- Q11
hr("Q11. Does any 'LLM' system call a model?")
for f in ("src/baselines/harness.py", "src/method/ssr_engine.py", "scripts/reproduce_all.py"):
    tree = ast.parse(pathlib.Path(f).read_text())
    mods = sorted({a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names} |
                  {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module})
    print(f"{f:32s} imports: {mods}")
