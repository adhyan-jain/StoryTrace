#!/usr/bin/env bash
# Full baseline run (sequential; one GPU). Resumable: re-running skips completed calls.
set -euo pipefail
cd "$(dirname "$0")/.."
source venv/bin/activate
SPLITS="test_id test_ood_lex test_ood_ent test_ood_struct test_ood_nonlinear test_ood_length test_ood_distract test_ood_evorder test_challenge"
for MODEL in qwen2.5:7b llama3:latest qwen3:8b; do
  python -m research.ssr_bench.run --model "$MODEL" --systems p5_direct_qa p1_zero_shot_delta p2_explicit_revision p3_regenerate --splits $SPLITS
  python -m research.ssr_bench.run --model "$MODEL" --systems p4_self_consistency --splits test_id
done
