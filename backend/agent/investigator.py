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
    fails validation and the caller falls back safely.

    Field order matters here and is deliberate: `explanation` is declared
    BEFORE `status`/`severity`/`confidence`. A real eval run on qwen2.5:7b
    (via Ollama's JSON mode, which has no true constrained decoding) showed
    the model emitting an `explanation` that plainly argued for "resolved"
    ("this meets the criteria for a valid bridge") while `status` still came
    out "verified" -- the two fields were generated independently with no
    real reasoning-then-conclusion link between them, because `status` was
    asked for FIRST, before the model had "thought out loud" via the
    explanation text. Putting `explanation` first lets the model's own
    free-text reasoning happen before it has to commit to the enum, so the
    enum can actually follow from the reasoning instead of preceding it."""

    explanation: str
    status: Literal["verified", "resolved", "uncertain"] = Field(
        description="verified | resolved | uncertain -- MUST follow logically from the explanation above, not be decided independently of it"
    )
    severity: Literal["critical", "warning", "info"] = Field(
        description="critical | warning | info -- how serious this is for the reader/editor, independent of status"
    )
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

# Shared between the per-step action prompt AND the final verdict prompt --
# a real bug found via eval: this used to live ONLY in the action prompt, so
# by the time the model was asked to actually COMMIT to a verdict, these
# criteria had fallen out of its immediate context and it fell back to its
# own generic (and inconsistent) judgment even after retrieving the exact
# bridging text via a tool call. Verdicts must be judged against the same
# rules that were used to decide whether to keep investigating.
_BRIDGE_CRITERIA = """
What counts as a valid bridge (resolves the candidate, not a real conflict):
- Injury healing: an explicit treatment/medical event (paramedic, bandage,
  gauze, field kit, wrapped, cleaned, treated) is BY ITSELF a sufficient
  bridge -- do not also require an explicit "days later"/time-skip phrase on
  top of it. IMPORTANT: this is true even when the treatment is described in
  the SAME unit as the "prior" (injured) evidence itself. For example, if the
  prior excerpt already shows a wound being cleaned/wrapped/bandaged by a
  paramedic, that IS the bridge, and the verdict MUST be 'resolved'.
  Do not second-guess this: if you can see medical treatment words in the
  prior excerpt or prior unit text (paramedic, gauze, bandage, wrapped,
  cleaned, field kit), verdict = 'resolved'. Period.
  Only fall back to 'uncertain' when NO treatment event exists anywhere --
  neither in the prior excerpt, nor in the prior unit text, nor in any
  intervening unit -- AND no explicit time-lapse is narrated.
  Merely not being mentioned again, with neither treatment nor a time lapse,
  is NOT a bridge and yields 'uncertain'.
- Possession reappearing: the item being explicitly returned, reissued, or
  handed back (e.g. "returned it the next morning"), not just picked back up
  with no explanation.
- Location change: an explicit travel/transit scene, a clearly narrated time
  skip, or the character being told/shown to have moved. Two locations
  simply appearing in sequence with nothing narrated in between is NOT a
  bridge -- that is exactly the kind of unexplained jump this system exists
  to catch, so when in doubt on location, prefer 'verified' or 'uncertain'
  over 'resolved'.
  CRITICAL FOR CITY CHANGES: A location.city change (e.g. Chicago → New York)
  is a VERIFIED conflict unless you can find explicit travel narration (e.g.
  "Cole flew to New York", "took the overnight train", "drove up"). If the
  character simply appears in the new city with no travel mentioned, verdict
  MUST be 'verified'. Default answer for city changes = 'verified'.

QUICK-DECISION RULE: Before calling any tools, scan the prior excerpt shown
in context above. If it already contains medical/treatment words (paramedic,
gauze, bandage, wrapped, cleaned, field kit) for an injury candidate, you
ALREADY have enough to conclude 'resolved'. Call 'finish' immediately with
that verdict -- no additional tool calls needed for this case.
"""


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
        # Was 6. The per-step prompt grew a real "what counts as a bridge"
        # section (see _run_loop) that gives the model more to weigh each
        # turn -- a real eval run hit "max tool calls reached" on a
        # candidate that a prior run (with the shorter prompt) resolved
        # cleanly. A couple of extra calls costs little against the 638s/860s
        # eval wall-clock already dominated by LLM latency, and directly
        # trades against the exact failure mode just observed.
        self.max_calls = 8
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
                tools = AgentTools(session, self.story_universe_id, log=self.tool_call_log, candidate=candidate)
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

        # Smaller local models (e.g. qwen2.5:7b via Ollama) were observed
        # calling the exact same tool with the exact same args repeatedly --
        # e.g. get_unit_text on the same unit_id 7 times in a row -- burning
        # the entire max_calls budget without ever reaching 'finish'. Detect
        # an exact repeat, skip re-executing it (the observation is already
        # in context, nothing new to learn), and tell the model directly so
        # it doesn't just keep guessing the same dead end.
        seen_calls: set[tuple] = set()
        repeat_streak = 0

        async def finalize() -> InvestigationVerdict:
            verdict_req = LLMRequest(
                stage="investigation_verdict",
                prompt=f"{context}\n{_BRIDGE_CRITERIA}\nYou have decided to conclude. Provide your final verdict now, judged strictly against the bridge criteria above.",
            )
            try:
                verdict = self.provider.complete(verdict_req, FinalVerdict).value
            except Exception as e:
                steps.append({"step": "error", "message": f"invalid FinalVerdict: {e}"})
                return InvestigationVerdict(
                    id=f"verdict_{candidate.id}",
                    candidate_id=candidate.id,
                    status="uncertain",
                    severity="warning",
                    explanation="Could not obtain a valid final verdict from the model.",
                    confidence=0.0,
                    investigation_actions=[json.dumps(s) for s in steps],
                    suggested_fix="",
                )
            steps.append({"step": "verdict", "verdict": verdict.model_dump()})
            suggested_fix = ""
            if verdict.status == "verified":
                try:
                    suggested_fix = await self._suggest_fix(candidate)
                except Exception:
                    # _suggest_fix already catches its own internal errors,
                    # but a real run hit a google-adk exception (429
                    # RESOURCE_EXHAUSTED) that escaped its try/except and
                    # crashed the whole investigation -- suggested_fix is a
                    # nice-to-have UI extra, never worth losing an otherwise-
                    # correct verdict over.
                    suggested_fix = ""
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

        for _ in range(self.max_calls):
            prompt = f"""
            {context}

            You are the Investigation Agent.
            Tools available:
            - get_entity_timeline: args {{"entity_id": str, "from_sequence": int, "to_sequence": int}}
            - get_unit_text: args {{"unit_id": str}}
            - get_state_at_unit: args {{"entity_id": str, "sequence_number": int}}
            - find_attribute_changes: args {{"entity_id": str, "attribute": str}}

            Before concluding there is no bridge, you MUST check the actual narrative
            text, not just the two excerpts above: call get_unit_text on the prior and
            current unit themselves, AND call find_attribute_changes (or
            get_entity_timeline) for this entity/attribute to see every recorded step in
            between -- a bridging event (e.g. an item being returned) is often its own
            intervening step that this candidate's prior/current excerpts don't show you,
            because the candidate only shows the two ENDPOINTS of the suspicious jump.

            {_BRIDGE_CRITERIA}

            Decide next action. If you have enough evidence to resolve (found a bridge) or verify (no bridge), call 'finish' with empty kwargs ({{}}) -- you'll be asked for the verdict itself in a follow-up.
            """

            req = LLMRequest(stage="investigation", prompt=prompt)
            try:
                res = self.provider.complete(req, AgentAction)
                action = res.value
            except Exception as e:
                # Malformed/unparseable AgentAction from the model itself --
                # nothing to retry against, so this iteration is simply
                # wasted (bounded by max_calls, same as everything else).
                steps.append({"step": "error", "message": f"invalid AgentAction: {e}"})
                context += f"\nYour previous response could not be parsed as a valid action: {e}\n"
                continue

            try:
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
                    return await finalize()

                call_key = (action.tool_name, tuple(sorted(action.kwargs.items())))
                if call_key in seen_calls:
                    repeat_streak += 1
                    steps.append({"step": "repeat_skipped", "tool": action.tool_name, "args": action.kwargs})
                    context += (
                        f"\nYou already called {action.tool_name}({action.kwargs}) earlier -- "
                        "that observation is already above, calling it again will not reveal "
                        "anything new. Either try a DIFFERENT tool/arguments, or call 'finish' "
                        "now and give your verdict with the evidence you already have.\n"
                    )
                    if repeat_streak >= 2:
                        # Two identical repeats in a row means the model is
                        # stuck, not exploring -- stop burning the remaining
                        # call budget on more of the same and force a verdict
                        # from whatever evidence was actually gathered.
                        return await finalize()
                    continue
                repeat_streak = 0
                seen_calls.add(call_key)

                steps.append({"step": "action", "tool": action.tool_name, "args": action.kwargs})
                tool_fn = getattr(tools, action.tool_name, None)
                tool_res: Any = await tool_fn(**action.kwargs) if tool_fn else {"error": f"unknown tool {action.tool_name}"}

                steps.append({"step": "observation", "tool": action.tool_name, "result": tool_res})
                context += f"\nObservation from {action.tool_name}: {tool_res}\n"

            except Exception as e:
                # A bad tool call (most commonly a hallucinated/mismatched
                # kwarg name, e.g. get_state_at_unit(unit_id=...) borrowed
                # from the sibling get_unit_text(unit_id) signature) used to
                # `break` here, discarding the rest of the call budget on a
                # single mistake the model could otherwise self-correct from.
                # Feeding the error back as an observation and continuing
                # lets it retry with corrected arguments, same as any other
                # tool observation -- max_calls is still the real backstop.
                steps.append({"step": "error", "tool": action.tool_name, "message": str(e)})
                context += (
                    f"\nYour call to {action.tool_name} failed: {e}. "
                    "Check the tool's exact argument names above and try again.\n"
                )
                continue

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
