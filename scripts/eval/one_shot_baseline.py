"""Condition D (ablation): one-shot LLM baseline -- the naive "just ask an
LLM to find continuity errors" approach, with no deterministic detection, no
controlled vocabulary, and no investigation agent.

Per the user's explicit decision (see ~/.claude/plans/dapper-stargazing-adleman.md,
item A1): this uses the literal "Gemini 1.5 Pro" model named in the original
spec, NOT the gemini-2.5-flash Condition A runs on -- this is a real
model-version confound versus Condition A and MUST be disclosed as such in
the paper's Limitations section and the patent disclosure's experimental-
evidence section, not presented as an apples-to-apples comparison.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from backend.eval.cost_tracker import CostTracker  # noqa: E402
from backend.llm.base import LLMError, LLMRequest  # noqa: E402
from backend.llm.vertexai import VertexAIProvider  # noqa: E402

BASELINE_MODEL = "gemini-1.5-pro"
MAX_CHARS = 50_000

BASELINE_PROMPT = """You are a professional script supervisor. Read this screenplay and
identify every continuity error you can find.

For each error, return a JSON object with:
- entity: the character or prop name
- attribute: what attribute is inconsistent (clothing, possession, injury, location)
- prior_scene: approximate scene number or description where state was established
- current_scene: approximate scene number where state contradicts
- prior_excerpt: the exact sentence establishing prior state
- current_excerpt: the exact sentence contradicting it
- explanation: why this is a continuity error

Return a JSON array of errors. Return only JSON, no preamble.

SCREENPLAY:
{screenplay_text}
"""


class BaselineFinding(BaseModel):
    entity: str
    attribute: str
    prior_scene: str
    current_scene: str
    prior_excerpt: str
    current_excerpt: str
    explanation: str


class BaselineFindings(BaseModel):
    findings: list[BaselineFinding] = Field(default_factory=list)


def run_one_shot_baseline(
    screenplay_path: str,
    story_universe_id: str,
    cost_tracker: CostTracker | None = None,
) -> dict:
    """Runs the single-call one-shot baseline against one screenplay.

    Returns the standard per-condition summary dict (see
    scripts/eval/run_ablation.py's output schema) plus the raw findings list.
    Truncation to MAX_CHARS chars is logged in the returned dict as
    `truncated`/`original_char_count` so it can be reported as a per-film
    covariate (per plan item A1) rather than silently applied.
    """
    text = Path(screenplay_path).read_text(encoding="utf-8", errors="ignore")
    original_char_count = len(text)
    truncated = original_char_count > MAX_CHARS
    if truncated:
        text = text[:MAX_CHARS]

    provider = VertexAIProvider(model_name=BASELINE_MODEL)
    tracker = cost_tracker if cost_tracker is not None else CostTracker()

    request = LLMRequest(
        stage="one_shot_baseline",
        prompt=BASELINE_PROMPT.format(screenplay_text=text),
        temperature=0.0,
        max_tokens=8192,
    )

    findings: list[dict] = []
    error = None
    try:
        result = provider.complete(request, BaselineFindings)
        tracker.record_result(BASELINE_MODEL, result)
        findings = [f.model_dump() for f in result.value.findings]
    except LLMError as exc:
        error = str(exc)
    except Exception as exc:  # noqa: BLE001 -- mirrors unconstrained_extractor.py's
        # broad fallback: a malformed-response ValidationError, network
        # timeout, or missing-credentials error must not crash the whole
        # ablation run (run_ablation.py depends on this returning a result
        # dict, not raising, so Conditions A/B/C's already-written output
        # isn't lost to an uncaught Condition D failure).
        error = f"{type(exc).__name__}: {exc}"

    return {
        "film": story_universe_id,
        "condition": "D",
        "model": BASELINE_MODEL,
        "candidates_generated": None,  # not applicable -- no detection phase
        "conflicts_surfaced": len(findings),
        "truncated": truncated,
        "original_char_count": original_char_count,
        "chars_sent": len(text),
        "error": error,
        "findings": findings,
        **tracker.to_summary_dict(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screenplay_path", help="Path to cleaned screenplay .txt (see scripts/eval/fetch_stage_screenplay.py)")
    parser.add_argument("film_slug", help="e.g. eval_aliens -- used as story_universe_id and output filename stem")
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "data" / "eval"))
    args = parser.parse_args()

    result = run_one_shot_baseline(args.screenplay_path, args.film_slug)

    out_path = Path(args.out_dir) / f"{args.film_slug}_baseline_findings.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(
        f"{args.film_slug}: {result['conflicts_surfaced']} findings, "
        f"{result['api_calls_total']} api call(s), "
        f"${result['estimated_cost_usd']:.4f}, "
        f"truncated={result['truncated']} ({result['original_char_count']} chars) "
        f"-> {out_path}"
    )
    if result["error"]:
        print(f"ERROR: {result['error']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
