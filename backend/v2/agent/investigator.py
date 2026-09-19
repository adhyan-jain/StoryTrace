"""StoryTrace V2 Calibrated Evidence-Grounded Investigation Agent.

Performs bounded ReAct investigation over ClickHouse MCP tools to adjudicate
candidate conflicts into calibrated two-tier verdicts:
- verified_hard_conflict (direct physical/logical impossibility)
- verified_narrative_anomaly (unbridged jump / unexplained reset)
- resolved (narratively justified transition / flashback / valid travel)
- uncertain (insufficient textual proof)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, field_validator

from backend.v2.agent.tools import AgentToolsV2
from backend.llm.base import LLMProvider, LLMRequest, LLMResult, LLMError, LLMParseError
from backend.v2.story_state.models import (
    CandidateConflictV2, InvestigationVerdictV2, VerdictStatusV2
)

logger = logging.getLogger(__name__)

_VALID_STATUSES_V2 = {
    "verified_hard_conflict", "verified_narrative_anomaly", "resolved", "uncertain"
}
_SEVERITY_SYNONYMS = {
    "critical": "critical", "high": "critical", "severe": "critical",
    "warning": "warning", "medium": "warning", "moderate": "warning",
    "info": "info", "low": "info", "minor": "info",
}
_CONFIDENCE_WORDS = {"high": 0.9, "medium": 0.6, "moderate": 0.6, "low": 0.3}


class AgentActionV2(BaseModel):
    tool_name: str = Field(
        description="Tool to call: get_entity_timeline_v2, get_scene_co_presence, get_spatial_trajectory, find_attribute_changes, get_unit_text, or 'finish'"
    )
    kwargs: dict = Field(
        default_factory=dict,
        description="Tool arguments as JSON object. Empty {} for finish."
    )


class FinalVerdictV2(BaseModel):
    explanation: str = Field(
        description="Detailed step-by-step reasoning grounded in retrieved textual evidence. State reasoning BEFORE choosing status."
    )
    status: Literal["verified_hard_conflict", "verified_narrative_anomaly", "resolved", "uncertain"] = Field(
        description="verified_hard_conflict | verified_narrative_anomaly | resolved | uncertain"
    )
    severity: Literal["critical", "warning", "info"] = Field(
        description="critical | warning | info"
    )
    confidence: float = Field(
        default=1.0,
        description="0.0 to 1.0 confidence score"
    )
    verbatim_evidence_quotes: List[str] = Field(
        default_factory=list,
        description="Exact verbatim quotes from retrieved narrative units supporting this verdict"
    )

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: object) -> object:
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in _VALID_STATUSES_V2:
                return lowered
            # Normalize V1 legacy statuses
            if lowered == "verified":
                return "verified_hard_conflict"
        return v

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v: object) -> object:
        if isinstance(v, str):
            return _SEVERITY_SYNONYMS.get(v.strip().lower(), v)
        return v

    @field_validator("confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                return _CONFIDENCE_WORDS.get(v.strip().lower(), 0.5)
        return v


class FixSuggestionV2(BaseModel):
    sentence: str = Field(description="A single concise sentence to insert between the scenes to resolve the anomaly")


INVESTIGATION_SYSTEM_PROMPT_V2 = """You are a senior screenplay continuity investigator. Your task is to investigate a potential continuity conflict candidate and reach an evidence-grounded, calibrated verdict.

AVAILABLE TOOLS:
1. get_entity_timeline_v2(entity_id, from_sequence, to_sequence)
2. get_scene_co_presence(from_sequence, to_sequence)
3. get_spatial_trajectory(entity_id)
4. find_attribute_changes(entity_id, attribute)
5. get_unit_text(unit_id)
6. finish()

TWO-TIER CALIBRATED VERDICT STANDARDS:
- 'verified_hard_conflict': Direct physical, spatial, or logical impossibility (e.g. deceased entity active, simultaneous presence in two distinct cities, item possessed by two characters at once).
- 'verified_narrative_anomaly': Unbridged spatial/possession leap without narrative explanation or intermediate transit during continuous pacing.
- 'resolved': Legitimate narrative transition (e.g. off-screen transit during substantial elapsed time, valid flashback/dream, disguised identity, medical treatment).
- 'uncertain': Insufficient textual proof to confirm or refute.

CRITICAL RULES:
- Ground every verdict in verbatim quotes retrieved via tools.
- Output your step-by-step reasoning in 'explanation' BEFORE committing to a status.
- Call 'finish' when you have sufficient evidence.
"""


def _mcp_env() -> dict:
    env = os.environ.copy()
    env.setdefault("CLICKHOUSE_HOST", "localhost")
    env.setdefault("CLICKHOUSE_PORT", "8123")
    env.setdefault("CLICKHOUSE_USER", "default")
    env.setdefault("CLICKHOUSE_PASSWORD", "admin")
    env["CLICKHOUSE_DATABASE"] = os.environ.get("CLICKHOUSE_DATABASE") or os.environ.get("CLICKHOUSE_DB", "storytrace")
    env.setdefault("CLICKHOUSE_SECURE", "false")
    return env


def _get_mcp_command() -> str:
    which_cmd = shutil.which("mcp-clickhouse")
    if which_cmd:
        return which_cmd
    venv_cmd = Path(sys.executable).parent / "mcp-clickhouse"
    if venv_cmd.exists():
        return str(venv_cmd)
    return "mcp-clickhouse"


_MCP_SERVER_PARAMS = StdioServerParameters(command=_get_mcp_command(), args=[], env=_mcp_env())


class InvestigationAgentV2:
    def __init__(self, provider: LLMProvider, story_universe_id: str):
        self.provider = provider
        self.story_universe_id = story_universe_id
        self.max_calls = 6
        self.tool_call_log: List[dict] = []

    def investigate(self, candidate: CandidateConflictV2) -> InvestigationVerdictV2:
        return asyncio.run(self.investigate_async(candidate))

    async def investigate_async(self, candidate: CandidateConflictV2) -> InvestigationVerdictV2:
        self.tool_call_log = []
        try:
            async with stdio_client(_MCP_SERVER_PARAMS) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = AgentToolsV2(session, self.story_universe_id, log=self.tool_call_log, candidate=candidate)
                    return await self._run_loop(candidate, tools)
        except Exception as e:
            logger.warning("Investigation session failed for candidate %s: %s", candidate.id, e)
            return InvestigationVerdictV2(
                id=f"verdict_{candidate.id}",
                candidate_id=candidate.id,
                status=VerdictStatusV2.UNCERTAIN,
                severity="warning",
                explanation=f"Investigation session failed: {e}",
                confidence=0.0,
                investigation_actions=[json.dumps({"step": "fatal_error", "message": str(e)})],
                suggested_fix=""
            )

    async def _run_loop(self, candidate: CandidateConflictV2, tools: AgentToolsV2) -> InvestigationVerdictV2:
        steps: List[dict] = []
        seen_calls: Dict[str, int] = {}

        for step_idx in range(self.max_calls):
            prompt = self._build_step_prompt(candidate, steps)
            request = LLMRequest(stage="v2_investigation_step", prompt=prompt, system=INVESTIGATION_SYSTEM_PROMPT_V2, temperature=0.0)

            try:
                res = self.provider.complete(request, AgentActionV2)
                action = res.value
            except Exception as exc:
                steps.append({"step": step_idx, "error": f"Invalid action: {exc}"})
                continue

            call_signature = f"{action.tool_name}:{json.dumps(action.kwargs, sort_keys=True)}"
            seen_calls[call_signature] = seen_calls.get(call_signature, 0) + 1
            if seen_calls[call_signature] >= 2 and action.tool_name != "finish":
                # Force finish on loop
                break

            if action.tool_name == "finish":
                break

            # Execute tool
            observation = await self._execute_tool(action, tools)
            steps.append({
                "step": step_idx,
                "tool": action.tool_name,
                "kwargs": action.kwargs,
                "observation": observation
            })

        # Produce Final Verdict
        final_prompt = self._build_verdict_prompt(candidate, steps)
        request = LLMRequest(stage="v2_investigation_verdict", prompt=final_prompt, system=INVESTIGATION_SYSTEM_PROMPT_V2, temperature=0.0)
        
        try:
            verdict_res = self.provider.complete(request, FinalVerdictV2)
            final_v = verdict_res.value
        except Exception as exc:
            final_v = FinalVerdictV2(
                explanation=f"Final verdict parsing fallback: {exc}",
                status="uncertain",
                severity="warning",
                confidence=0.5
            )

        status_enum = VerdictStatusV2(final_v.status)
        suggested_fix = ""
        if status_enum in (VerdictStatusV2.VERIFIED_HARD_CONFLICT, VerdictStatusV2.VERIFIED_NARRATIVE_ANOMALY):
            suggested_fix = await self._suggest_fix(candidate, final_v)

        return InvestigationVerdictV2(
            id=f"verdict_{candidate.id}",
            candidate_id=candidate.id,
            status=status_enum,
            severity=final_v.severity,
            explanation=final_v.explanation,
            confidence=final_v.confidence,
            investigation_actions=[json.dumps(s) for s in steps],
            suggested_fix=suggested_fix
        )

    async def _execute_tool(self, action: AgentActionV2, tools: AgentToolsV2) -> Any:
        tool_name = action.tool_name
        kwargs = action.kwargs
        try:
            if tool_name == "get_entity_timeline_v2":
                return await tools.get_entity_timeline_v2(**kwargs)
            elif tool_name == "get_scene_co_presence":
                return await tools.get_scene_co_presence(**kwargs)
            elif tool_name == "get_spatial_trajectory":
                return await tools.get_spatial_trajectory(**kwargs)
            elif tool_name == "find_attribute_changes":
                return await tools.find_attribute_changes(**kwargs)
            elif tool_name == "get_unit_text":
                return await tools.get_unit_text(**kwargs)
            else:
                return {"error": f"Unknown tool '{tool_name}'"}
        except Exception as e:
            return {"error": f"Tool execution failed: {e}"}

    def _build_step_prompt(self, candidate: CandidateConflictV2, steps: List[dict]) -> str:
        return f"""Investigate this candidate continuity conflict:
Rule Type: {candidate.rule_type}
Entities: {candidate.entity_ids}
Attribute: {candidate.attribute}
Prior Evidence (Unit {candidate.prior_evidence_unit_id}): "{candidate.prior_evidence_excerpt}"
Current Evidence (Unit {candidate.current_evidence_unit_id}): "{candidate.current_evidence_excerpt}"
Description: {candidate.description}

Steps Taken So Far:
{json.dumps(steps, indent=2) if steps else "None"}

Choose the next tool call or 'finish'."""

    def _build_verdict_prompt(self, candidate: CandidateConflictV2, steps: List[dict]) -> str:
        return f"""Provide your final calibrated verdict for this investigated candidate:
Candidate: {candidate.description}
Prior Unit: {candidate.prior_evidence_unit_id} ("{candidate.prior_evidence_excerpt}")
Current Unit: {candidate.current_evidence_unit_id} ("{candidate.current_evidence_excerpt}")

Evidence Gathered:
{json.dumps(steps, indent=2)}

Emit your FinalVerdictV2 with detailed explanation first, followed by status, severity, confidence, and verbatim quotes."""

    async def _suggest_fix(self, candidate: CandidateConflictV2, verdict: FinalVerdictV2) -> str:
        prompt = f"""Suggest a single sentence to bridge this continuity gap:
Conflict: {candidate.description}
Explanation: {verdict.explanation}
Prior Scene: "{candidate.prior_evidence_excerpt}"
Current Scene: "{candidate.current_evidence_excerpt}" """
        request = LLMRequest(stage="v2_suggest_fix", prompt=prompt, temperature=0.0)
        try:
            res = self.provider.complete(request, FixSuggestionV2)
            return res.value.sentence
        except Exception:
            return ""
