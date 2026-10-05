#!/usr/bin/env bash
# Addendum B: mistral:7b, queued behind run_baselines.sh. Resumable.
set -euo pipefail
cd "$(dirname "$0")/.."
while pgrep -f "research/run_baselines.sh" >/dev/null; do sleep 60; done
source venv/bin/activate
SPLITS="test_id test_ood_lex test_ood_ent test_ood_struct test_ood_nonlinear test_ood_length test_ood_distract test_ood_evorder test_challenge"
MODEL=mistral:7b
python -m research.ssr_bench.run --model "$MODEL" --systems p5_direct_qa p1_zero_shot_delta p2_explicit_revision p3_regenerate --splits $SPLITS
python -m research.ssr_bench.run --model "$MODEL" --systems p4_self_consistency --splits test_id
