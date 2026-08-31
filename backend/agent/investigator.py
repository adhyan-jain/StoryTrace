import json
from pydantic import BaseModel, Field
from typing import List, Any
from backend.llm.client import GeminiProvider
from backend.llm.base import LLMRequest
from backend.agent.tools import AgentTools
from backend.story_state.models import CandidateConflict, InvestigationVerdict

class AgentAction(BaseModel):
    tool_name: str = Field(description="Name of the tool to call: get_entity_timeline, get_unit_text, get_state_at_unit, find_attribute_changes, or 'finish'")
    kwargs: str = Field(description="JSON string of arguments for the tool, or final verdict JSON if finish")

class FinalVerdict(BaseModel):
    status: str = Field(description="verified | resolved | uncertain")
    severity: str = Field(description="critical | warning | info -- how serious this is for the reader/editor, independent of status")
    explanation: str
    confidence: float

class InvestigationAgent:
    def __init__(self, provider: GeminiProvider, tools: AgentTools):
        self.provider = provider
        self.tools = tools
        self.max_calls = 6

    def investigate(self, candidate: CandidateConflict) -> InvestigationVerdict:
        # Each step is a JSON object (thought/action/observation/verdict) so the
        # autopsy view can render a real trace instead of parsing free text.
        steps: List[dict] = []
        context = f"Investigating candidate: {candidate.description}\n"
        context += f"Prior: {candidate.prior_evidence_excerpt} (Unit {candidate.prior_evidence_unit_id})\n"
        context += f"Current: {candidate.current_evidence_excerpt} (Unit {candidate.current_evidence_unit_id})\n"

        for step in range(self.max_calls):
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

                if action.tool_name == 'finish':
                    verdict_data = json.loads(action.kwargs)
                    steps.append({"step": "verdict", "verdict": verdict_data})
                    return InvestigationVerdict(
                        id=f"verdict_{candidate.id}",
                        candidate_id=candidate.id,
                        status=verdict_data.get("status", "uncertain"),
                        severity=verdict_data.get("severity", "warning"),
                        explanation=verdict_data.get("explanation", ""),
                        confidence=verdict_data.get("confidence", 0.0),
                        investigation_actions=[json.dumps(s) for s in steps],
                    )

                # Execute tool
                kwargs = json.loads(action.kwargs)
                steps.append({"step": "action", "tool": action.tool_name, "args": kwargs})
                tool_res: Any = None
                if action.tool_name == "get_entity_timeline":
                    tool_res = self.tools.get_entity_timeline(**kwargs)
                elif action.tool_name == "get_unit_text":
                    tool_res = self.tools.get_unit_text(**kwargs)
                elif action.tool_name == "get_state_at_unit":
                    tool_res = self.tools.get_state_at_unit(**kwargs)
                elif action.tool_name == "find_attribute_changes":
                    tool_res = self.tools.find_attribute_changes(**kwargs)

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
        )
