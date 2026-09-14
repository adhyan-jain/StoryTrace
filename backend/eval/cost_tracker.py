"""Cost aggregation for ablation runs.

backend/llm/base.py/client.py/vertexai.py already return per-call token
counts on every LLMResult, but nothing in the codebase turns that into a
cumulative api_calls_total / tokens_used / estimated_cost_usd for a whole
pipeline or baseline run (see Part A, item A5 of the approved plan at
~/.claude/plans/dapper-stargazing-adleman.md) -- this module is that missing
piece, used by every one of the four ablation conditions' run scripts.

Pricing is a hardcoded snapshot (USD per 1M tokens) that must be re-checked
against Google's published Vertex AI pricing page at the time numbers are
cited in the paper/patent -- this is exactly the kind of number this eval's
own CLAUDE.md-style discipline requires to be traceable to a source, not
silently assumed accurate forever.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# USD per 1,000,000 tokens. Snapshot only -- verify against
# https://cloud.google.com/vertex-ai/generative-ai/pricing before citing any
# derived estimated_cost_usd number in the paper or patent disclosure.
_PRICING_USD_PER_1M_TOKENS: dict[str, dict[str, float]] = {
    "gemini-2.5-flash": {"input": 0.30, "output": 2.50},
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00},
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-pro-002": {"input": 1.25, "output": 5.00},
}


def _rate_for(model: str) -> dict[str, float]:
    if model in _PRICING_USD_PER_1M_TOKENS:
        return _PRICING_USD_PER_1M_TOKENS[model]
    # Unknown/newer model name: fail loudly rather than silently costing $0,
    # which would corrupt every downstream cost_per_finding calculation.
    raise KeyError(
        f"No pricing entry for model {model!r} in cost_tracker._PRICING_USD_PER_1M_TOKENS "
        "-- add a verified rate before running a cost-tracked eval against it."
    )


@dataclass
class CostTracker:
    """Accumulate token usage across a run's LLM calls into a per-run cost
    summary. One instance per condition-run (e.g. one per film per
    condition), not shared across films -- ablation_run outputs are per-film."""

    api_calls_total: int = 0
    prompt_tokens_total: int = 0
    completion_tokens_total: int = 0
    _cost_usd: float = field(default=0.0, repr=False)

    def record(self, model: str, prompt_tokens: int, completion_tokens: int) -> None:
        rate = _rate_for(model)
        self.api_calls_total += 1
        self.prompt_tokens_total += prompt_tokens
        self.completion_tokens_total += completion_tokens
        self._cost_usd += (prompt_tokens / 1_000_000) * rate["input"]
        self._cost_usd += (completion_tokens / 1_000_000) * rate["output"]

    def record_result(self, model: str, llm_result) -> None:
        """Convenience wrapper for an LLMResult (backend/llm/base.py) --
        reads its prompt_tokens/completion_tokens fields directly."""
        self.record(model, llm_result.prompt_tokens, llm_result.completion_tokens)

    @property
    def tokens_used(self) -> int:
        return self.prompt_tokens_total + self.completion_tokens_total

    @property
    def estimated_cost_usd(self) -> float:
        return round(self._cost_usd, 6)

    def to_summary_dict(self) -> dict:
        return {
            "api_calls_total": self.api_calls_total,
            "tokens_used": self.tokens_used,
            "prompt_tokens_total": self.prompt_tokens_total,
            "completion_tokens_total": self.completion_tokens_total,
            "estimated_cost_usd": self.estimated_cost_usd,
        }


class TrackedProvider:
    """Transparent proxy around any LLMProvider that records every
    .complete() call's token usage into a CostTracker, without modifying the
    wrapped provider or any of its callers (backend/pipeline/state_extraction.py,
    backend/agent/investigator.py, backend/eval/unconstrained_extractor.py
    all just call `.complete(request, schema)` on whatever provider object
    they were constructed with -- this is that object, swapped in at the
    ablation-runner call site only, per the constraint against editing the
    detector/investigator/extraction modules themselves).
    """

    def __init__(self, provider, tracker: CostTracker):
        self._provider = provider
        self._tracker = tracker

    def complete(self, request, schema):
        result = self._provider.complete(request, schema)
        self._tracker.record_result(result.model, result)
        return result

    def __getattr__(self, name):
        # tier, model, and any other read-only attribute pass through to the
        # wrapped provider unchanged.
        return getattr(self._provider, name)
