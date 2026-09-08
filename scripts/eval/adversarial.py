"""Adversarial extraction baseline: reruns extraction on the first few units
with a deliberately unconstrained prompt, to quantify how much the real
system prompt's controlled vocabulary + few-shot examples actually matter.

Never touches ClickHouse or the eval story_universe_id's real rows -- both
passes run in-memory only (extract_state_events is called directly, its
output is never written via write_state_events), so this can run before or
after the main eval without affecting it.
"""

from __future__ import annotations

import backend.pipeline.state_extraction as state_extraction
from backend.pipeline.entity_resolution import EntityRegistry
from data.eval.golden_dataset import GoldenDataset
from scripts.eval.engine import compute_metrics, match_state_event

BAD_PROMPT_OVERRIDE = """
Extract any facts you find. Return them as JSON.
Don't worry about format.
"""

_N_UNITS = 5


async def _run_extraction_pass(golden: GoldenDataset, provider, units) -> float:
    registry = EntityRegistry(f"{golden.story_universe_id}_adversarial")
    relevant_golden = [g for g in golden.state_events if g.sequence_number <= _N_UNITS]

    extracted = []
    for unit in units:
        events = await state_extraction.extract_state_events(unit, golden.story_universe_id, provider, registry)
        extracted.extend(events)

    id_to_name = {ent.id: ent.name for ent in registry.get_all()}
    predicted = [
        {
            "entity_name": id_to_name.get(e.entity_id, e.entity_id),
            "attribute": e.attribute,
            "value": e.value,
            "sequence_number": e.sequence_number,
            "raw_excerpt": e.raw_excerpt,
        }
        for e in extracted
    ]

    metrics = compute_metrics(
        phase="extraction_adversarial",
        predicted=predicted,
        golden=relevant_golden,
        match_fn=lambda pred, gold: match_state_event(pred, gold, tolerance_sequences=1),
    )
    return metrics.f1


async def run_adversarial_baseline(golden: GoldenDataset, provider) -> dict:
    """Runs extraction on the first _N_UNITS units twice: once with the real
    (engineered) prompt, once with BAD_PROMPT_OVERRIDE monkey-patched in.
    Restores the original prompt in a finally block regardless of outcome."""
    from scripts.eval.run_eval import load_units

    units = load_units(golden)[:_N_UNITS]

    engineered_f1 = await _run_extraction_pass(golden, provider, units)

    original_prompt = state_extraction.SYSTEM_PROMPT
    try:
        state_extraction.SYSTEM_PROMPT = BAD_PROMPT_OVERRIDE
        baseline_f1 = await _run_extraction_pass(golden, provider, units)
    finally:
        state_extraction.SYSTEM_PROMPT = original_prompt

    return {"baseline_f1": baseline_f1, "engineered_f1": engineered_f1, "units_tested": len(units)}
