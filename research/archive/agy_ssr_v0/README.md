# SUPERSEDED — AGY "Selective State Revision" v0 (archived, do not use)

Everything in this directory was produced by a previous agent and is kept **unchanged** for audit purposes only.
The "LLM" baselines and the "SSR Engine" read the gold labels / gold intervention class. No language model is ever called.
The 700-item benchmark is 7 items with names substituted. Several cited references have wrong venues or authors.

See `docs/BENCHMARK_FAILURE_AUDIT.md` for the full findings. Reproduce them with:

```bash
python research/archive/agy_ssr_v0/forensics.py   # output: forensics_output.txt
```

No number, label, citation or code path in this directory may be reused in the new benchmark (`research/ssr_bench/`).
