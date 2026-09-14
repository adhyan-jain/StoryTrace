"""Condition B (ablation): pipeline-only investigator.

A drop-in replacement for backend.agent.investigator.InvestigationAgent that
performs NO tool calls and NO LLM call -- it flags every candidate conflict
the SQL detector produced as "verified" without investigation. This isolates
what the bounded Investigation Agent (Condition A) actually contributes: the
expectation is high recall (nothing is filtered) but low precision relative
to Condition A, since candidates the agent would have "resolved" (found a
narrative bridge for) are instead all reported as real conflicts.

Same call surface as InvestigationAgent (investigate / investigate_async) so
scripts/eval/run_ablation.py can swap it in without touching detector or
pipeline wiring, per the constraint against modifying
backend/agent/investigator.py or backend/candidate_detection/detector.py.
"""

import asyncio

from backend.story_state.models import CandidateConflict, InvestigationVerdict

# Mirrors the vocabulary enforced in backend/pipeline/state_extraction.py:
# possession.* and injury.* changes are explicit, discrete state transitions
# (a prop is lost or a character is hurt) -- treated as higher severity by
# default than location, which is more often incidental scene-setting.
_HIGH_SEVERITY_PREFIXES = ("possession.", "injury.")


class PipelineOnlyInvestigator:
    def __init__(self, provider=None, story_universe_id: str = ""):
        # provider/story_universe_id accepted only to match InvestigationAgent's
        # constructor signature so callers can swap classes without branching.
        self.provider = provider
        self.story_universe_id = story_universe_id
        self.tool_call_log: list[dict] = []

    def _assign_severity(self, attribute: str) -> str:
        return "critical" if attribute.startswith(_HIGH_SEVERITY_PREFIXES) else "warning"

    def investigate(self, candidate: CandidateConflict) -> InvestigationVerdict:
        return asyncio.run(self.investigate_async(candidate))

    async def investigate_async(self, candidate: CandidateConflict) -> InvestigationVerdict:
        return InvestigationVerdict(
            id=f"verdict_{candidate.id}",
            candidate_id=candidate.id,
            status="verified",
            severity=self._assign_severity(candidate.attribute),
            explanation="Pipeline-only mode (Condition B): candidate flagged without investigation.",
            confidence=0.5,
            investigation_actions=[],
            suggested_fix="",
        )
