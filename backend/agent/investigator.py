import asyncio
import json
import os
from typing import Any, List, Literal

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field, field_validator

from backend.agent.tools import AgentTools
from backend.llm.base import LLMRequest
from backend.story_state.models import CandidateConflict, InvestigationVerdict


class AgentAction(BaseModel):
    tool_name: str = Field(
        description="Name of the tool to call: get_entity_timeline, get_unit_text, get_state_at_unit, find_attribute_changes, or 'finish'"
    )
    # A real JSON object field, not "a JSON string" -- the model previously
    # had to hand-encode-and-escape a nested JSON string inside this string
    # field, which it got wrong often enough (a stray unescaped quote/
    # apostrophe in free text, or literally returning an object instead of
    # its string encoding) to be a recurring source of "invalid AgentAction"/
    # JSON-parse failures. A real object field sidesteps the entire class of
    # self-escaping mistakes.
    kwargs: dict = Field(default_factory=dict, description="Arguments for the tool, as a JSON object. Empty {} for finish.")


_SEVERITY_SYNONYMS = {
    "critical": "critical", "high": "critical", "severe": "critical",
    "warning": "warning", "medium": "warning", "moderate": "warning",
    "info": "info", "low": "info", "minor": "info",
}
_CONFIDENCE_WORDS = {"high": 0.9, "medium": 0.6, "moderate": 0.6, "low": 0.3}
_VALID_STATUSES = {"verified", "resolved", "uncertain"}


class FinalVerdict(BaseModel):
    """Field validators normalize model output that was empirically observed
    to drift from the exact expected vocabulary/type, instead of discarding
    an otherwise-real conclusion over a cosmetic mismatch:
    - status/severity capitalized ("Verified" instead of "verified") -- the
      single most common rejection cause on the RI novel
    - severity given as "medium"/"high"/"low" rather than warning/critical/info
    - confidence given as a word ("high") rather than a number
    Only known-equivalent variants are smoothed over; anything else still
    fails validation and the caller falls back safely."""

    status: Literal["verified", "resolved", "uncertain"] = Field(
        description="verified | resolved | uncertain"
    )
    severity: Literal["critical", "warning", "info"] = Field(
        description="critical | warning | info -- how serious this is for the reader/editor, independent of status"
    )
    explanation: str
    confidence: float

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: object) -> object:
        if isinstance(v, str):
            lowered = v.strip().lower()
            if lowered in _VALID_STATUSES:
                return lowered
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
                return _CONFIDENCE_WORDS.get(v.strip().lower(), v)
        return v


class FixSuggestion(BaseModel):
    sentence: str = Field(description="A single sentence to insert between the two scenes that resolves the gap")


FIX_SYSTEM_PROMPT = """
You are a screenplay doctor. Given a continuity conflict between two scenes,
suggest a single sentence that could be inserted between them to resolve the
conflict naturally.

The sentence must:
- Sound like it belongs in the screenplay/novel's style
- Directly establish the missing transition
- Be concise (one sentence maximum)
- Not introduce new characters or plot elements

Return only the suggested sentence in the "sentence" field. No explanation, no preamble.
"""


def _mcp_env() -> dict:
    """mcp-clickhouse reads CLICKHOUSE_DATABASE; backend/clickhouse/client.py
    (and this project's .env) uses CLICKHOUSE_DB -- keep both in sync so the
    MCP server connects to the same database as the rest of the pipeline."""
    env = os.environ.copy()
    env.setdefault("CLICKHOUSE_HOST", "localhost")
    env.setdefault("CLICKHOUSE_PORT", "8123")
    env.setdefault("CLICKHOUSE_USER", "default")
    env.setdefault("CLICKHOUSE_PASSWORD", "admin")
    env["CLICKHOUSE_DATABASE"] = os.environ.get("CLICKHOUSE_DATABASE") or os.environ.get("CLICKHOUSE_DB", "storytrace")
    env.setdefault("CLICKHOUSE_SECURE", "false")
    return env


_MCP_SERVER_PARAMS = StdioServerParameters(command="mcp-clickhouse", args=[], env=_mcp_env())


class InvestigationAgent:
    """ReAct-style loop over the Investigation Agent's four ClickHouse tools.

    Every tool call is a real MCP `run_query` call against a `mcp-clickhouse`
    stdio server (not a direct clickhouse_connect client) -- one MCP session
    is opened per investigation and reused across all tool calls within it,
    then closed.
    """

    def __init__(self, provider, story_universe_id: str):
        self.provider = provider
        self.story_universe_id = story_universe_id
        self.max_calls = 6
        self.tool_call_log: List[dict] = []

    def investigate(self, candidate: CandidateConflict) -> InvestigationVerdict:
        """Sync entry point for callers with no running event loop (e.g. a
        FastAPI BackgroundTasks job). Callers already inside an event loop
        (the CLI pipeline scripts) must use `investigate_async` instead --
        asyncio.run() cannot be nested inside a running loop."""
        return asyncio.run(self.investigate_async(candidate))

    async def investigate_async(self, candidate: CandidateConflict) -> InvestigationVerdict:
        self.tool_call_log = []
        async with stdio_client(_MCP_SERVER_PARAMS) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = AgentTools(session, self.story_universe_id, log=self.tool_call_log)
                return await self._run_loop(candidate, tools)

    async def _run_loop(self, candidate: CandidateConflict, tools: AgentTools) -> InvestigationVerdict:
        steps: List[dict] = []
        # entity_id/attribute are the literal database keys the tools below
        # filter on -- the agent has no other way to learn them. Without this
        # line, every get_entity_timeline/get_state_at_unit/find_attribute_changes
        # call the agent makes is a guess at the entity_id from prose context
        # alone, which doesn't match the real (fully id_scope-prefixed) key
        # stored in state_events/entities. A real 501-chapter/276-unit run
        # confirmed this empirically: 100% of investigations returned 0 rows
        # from every tool call and fell through to "uncertain, 0% confidence,
        # max tool calls reached" -- the agent was never once able to find
        # the data that was actually there.
        context = f"Investigating candidate: {candidate.description}\n"
        context += f"Entity ID (use this exact string in tool calls): {candidate.entity_id}\n"
        context += f"Attribute (use this exact string in tool calls): {candidate.attribute}\n"
        context += f"Prior: {candidate.prior_evidence_excerpt} (Unit {candidate.prior_evidence_unit_id})\n"
        context += f"Current: {candidate.current_evidence_excerpt} (Unit {candidate.current_evidence_unit_id})\n"

        for _ in range(self.max_calls):
            prompt = f"""
            {context}

            You are the Investigation Agent.
            Tools available:
            - get_entity_timeline: args {{"entity_id": str, "from_sequence": int, "to_sequence": int}}
            - get_unit_text: args {{"unit_id": str}}
            - get_state_at_unit: args {{"entity_id": str, "sequence_number": int}}
            - find_attribute_changes: args {{"entity_id": str, "attribute": str}}

            Decide next action. If you have enough evidence to resolve (found a bridge) or verify (no bridge), call 'finish' with empty kwargs ({{}}) -- you'll be asked for the verdict itself in a follow-up.
            """

            req = LLMRequest(stage="investigation", prompt=prompt)
            try:
                res = self.provider.complete(req, AgentAction)
                action = res.value

                if action.tool_name == "finish":
                    # Getting the verdict via its own schema-validated call
                    # (instead of asking the model to hand-nest an
                    # already-escaped FinalVerdict JSON string inside
                    # AgentAction.kwargs: str) reuses the robust top-level
                    # JSON extraction/repair pipeline every other structured
                    # call in this codebase goes through (backend/llm/base.py's
                    # extract_json/heal_json), rather than a bare json.loads()
                    # with zero tolerance for the model mis-escaping a quote
                    # or apostrophe inside its own explanation text -- a real,
                    # frequent failure on the RI novel ("Expecting ','
                    # delimiter" from a single bad escape deep in the string).
                    verdict_req = LLMRequest(
                        stage="investigation_verdict",
                        prompt=f"{context}\n\nYou have decided to conclude. Provide your final verdict now.",
                    )
                    try:
                        verdict = self.provider.complete(verdict_req, FinalVerdict).value
                    except Exception as e:
                        steps.append({"step": "error", "message": f"invalid FinalVerdict: {e}"})
                        break
                    steps.append({"step": "verdict", "verdict": verdict.model_dump()})
                    suggested_fix = ""
                    if verdict.status == "verified":
                        suggested_fix = await self._suggest_fix(candidate)
                    return InvestigationVerdict(
                        id=f"verdict_{candidate.id}",
                        candidate_id=candidate.id,
                        status=verdict.status,
                        severity=verdict.severity,
                        explanation=verdict.explanation,
                        confidence=verdict.confidence,
                        investigation_actions=[json.dumps(s) for s in steps],
                        suggested_fix=suggested_fix,
                    )

                steps.append({"step": "action", "tool": action.tool_name, "args": action.kwargs})
                tool_fn = getattr(tools, action.tool_name, None)
                tool_res: Any = await tool_fn(**action.kwargs) if tool_fn else {"error": f"unknown tool {action.tool_name}"}

                steps.append({"step": "observation", "tool": action.tool_name, "result": tool_res})
                context += f"\nObservation from {action.tool_name}: {tool_res}\n"

            except Exception as e:
                steps.append({"step": "error", "message": str(e)})
                break

        return InvestigationVerdict(
            id=f"verdict_{candidate.id}",
            candidate_id=candidate.id,
            status="uncertain",
            severity="warning",
            explanation="Max tool calls reached without conclusion.",
            confidence=0.0,
            investigation_actions=[json.dumps(s) for s in steps],
            suggested_fix="",
        )

    async def _suggest_fix(self, candidate: CandidateConflict) -> str:
        """Real LLM call (Gemini or Ollama, whichever provider the agent is
        running on) asking for one sentence that would bridge the gap. Only
        invoked for a `verified` verdict."""
        prompt = f"""
        Conflict: {candidate.entity_id}'s {candidate.attribute} changes with no explanation.

        Prior scene excerpt:
        "{candidate.prior_evidence_excerpt}"

        Current scene excerpt:
        "{candidate.current_evidence_excerpt}"

        Suggest one sentence to insert between these scenes that would
        resolve this continuity gap naturally.
        """
        if getattr(self.provider, "tier", "") == "api":
            # Gemini tier: route through the real google-adk Agent/Runner.
            try:
                from backend.agent.adk_runner import suggest_fix_via_adk

                sentence = await suggest_fix_via_adk(self.provider.model, FIX_SYSTEM_PROMPT, prompt)
                if sentence:
                    return sentence
            except Exception:
                pass  # fall through to the plain provider call below

        req = LLMRequest(stage="suggest_fix", prompt=prompt, system=FIX_SYSTEM_PROMPT)
        try:
            res = self.provider.complete(req, FixSuggestion)
            return res.value.sentence
        except Exception:
            return ""
