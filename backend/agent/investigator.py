import asyncio
import json
import os
from typing import Any, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel, Field

from backend.agent.tools import AgentTools
from backend.llm.base import LLMRequest
from backend.story_state.models import CandidateConflict, InvestigationVerdict


class AgentAction(BaseModel):
    tool_name: str = Field(
        description="Name of the tool to call: get_entity_timeline, get_unit_text, get_state_at_unit, find_attribute_changes, or 'finish'"
    )
    kwargs: str = Field(description="JSON string of arguments for the tool, or final verdict JSON if finish")


class FinalVerdict(BaseModel):
    status: str = Field(description="verified | resolved | uncertain")
    severity: str = Field(description="critical | warning | info -- how serious this is for the reader/editor, independent of status")
    explanation: str
    confidence: float


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
        context = f"Investigating candidate: {candidate.description}\n"
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

            Decide next action. If you have enough evidence to resolve (found a bridge) or verify (no bridge), call 'finish' with kwargs containing FinalVerdict JSON (status, severity, explanation, confidence).
            """

            req = LLMRequest(stage="investigation", prompt=prompt)
            try:
                res = self.provider.complete(req, AgentAction)
                action = res.value

                if action.tool_name == "finish":
                    verdict_data = json.loads(action.kwargs)
                    steps.append({"step": "verdict", "verdict": verdict_data})
                    status = verdict_data.get("status", "uncertain")
                    suggested_fix = ""
                    if status == "verified":
                        suggested_fix = await self._suggest_fix(candidate)
                    return InvestigationVerdict(
                        id=f"verdict_{candidate.id}",
                        candidate_id=candidate.id,
                        status=status,
                        severity=verdict_data.get("severity", "warning"),
                        explanation=verdict_data.get("explanation", ""),
                        confidence=verdict_data.get("confidence", 0.0),
                        investigation_actions=[json.dumps(s) for s in steps],
                        suggested_fix=suggested_fix,
                    )

                kwargs = json.loads(action.kwargs)
                steps.append({"step": "action", "tool": action.tool_name, "args": kwargs})
                tool_fn = getattr(tools, action.tool_name, None)
                tool_res: Any = await tool_fn(**kwargs) if tool_fn else {"error": f"unknown tool {action.tool_name}"}

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
