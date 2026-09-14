"""Cross-domain generalization test (spec W3.4): runs Condition A only
against 5 chapters of Reverend Insanity (data/processed/ri_parsed.json,
already in the repo as pre-parsed NarrativeUnit-shaped records -- no
download needed) to check whether StoryTrace generalizes beyond screenplay
format to long-form prose fiction.

Writes data/eval/generalization_test.json with the run's findings plus a
`manual_notes` field left for the user to fill in after reading the
findings -- "does this generalize" is a qualitative judgment call this
script cannot make on its own.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.eval.cost_tracker import CostTracker  # noqa: E402
from backend.ingestion.models import NarrativeUnit  # noqa: E402
from scripts.eval.run_ablation import _run_condition_a_or_b  # noqa: E402

RI_PARSED_PATH = REPO_ROOT / "data" / "processed" / "ri_parsed.json"
OUT_PATH = REPO_ROOT / "data" / "eval" / "generalization_test.json"
STORY_UNIVERSE_ID = "eval_ri_generalization"
N_CHAPTERS = 5


async def main() -> None:
    raw_units = json.loads(RI_PARSED_PATH.read_text(encoding="utf-8"))[:N_CHAPTERS]
    units = [
        NarrativeUnit(
            unit_id=f"{STORY_UNIVERSE_ID}_unit_{i + 1}",
            story_universe_id=STORY_UNIVERSE_ID,
            document_id=STORY_UNIVERSE_ID,
            unit_type=u.get("unit_type", "passage"),
            sequence_number=i + 1,
            title=u.get("title", f"Chapter {i + 1}"),
            page_start=u.get("page_start", 1),
            page_end=u.get("page_end", 1),
            raw_text=u["raw_text"],
        )
        for i, u in enumerate(raw_units)
    ]

    tracker = CostTracker()
    result = await _run_condition_a_or_b(units, STORY_UNIVERSE_ID, "A", tracker)

    out = {
        "source": str(RI_PARSED_PATH.relative_to(REPO_ROOT)),
        "domain": "long-form web novel (not a screenplay)",
        "chapters_used": N_CHAPTERS,
        "story_universe_id": STORY_UNIVERSE_ID,
        **result,
        **tracker.to_summary_dict(),
        "manual_notes": "TODO (human): read the findings above against the "
                         "source chapters and record whether StoryTrace's "
                         "detections/verdicts hold up outside screenplay "
                         "format, or are screenplay-format-specific "
                         "artifacts (e.g. scene-header-driven unit "
                         "boundaries) -- this judgment cannot be automated.",
    }
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"{result['candidates_generated']} candidates, {result['conflicts_surfaced']} surfaced -> {OUT_PATH}")
    print("Fill in 'manual_notes' in that file after reviewing the findings.")


if __name__ == "__main__":
    asyncio.run(main())
