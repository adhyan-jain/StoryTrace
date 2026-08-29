import json
from pydantic import BaseModel, Field
from typing import List, Any
from backend.llm.client import GeminiProvider
from backend.llm.base import LLMRequest
from backend.agent.tools import AgentTools
from backend.story_state.models import CandidateConflict, InvestigationVerdict

class AgentAction(BaseModel):
    tool_name: str = Field(description="Name of the tool to call: get_entity_timeline, get_scene_text, get_state_at_scene, or 'finish'")
    kwargs: str = Field(description="JSON string of arguments for the tool, or final verdict JSON if finish")

class FinalVerdict(BaseModel):
    status: str = Field(description="verified | resolved | uncertain")
    explanation: str
    confidence: float

class InvestigationAgent:
    def __init__(self, provider: GeminiProvider, tools: AgentTools):
        self.provider = provider
        self.tools = tools
        self.max_calls = 6

    def investigate(self, candidate: CandidateConflict) -> InvestigationVerdict:
        actions_taken = []
        context = f"Investigating candidate: {candidate.description}\n"
        context += f"Prior: {candidate.prior_evidence_excerpt} (Scene {candidate.prior_evidence_scene_id})\n"
        context += f"Current: {candidate.current_evidence_excerpt} (Scene {candidate.current_evidence_scene_id})\n"

        for step in range(self.max_calls):
            prompt = f"""
            {context}
            
            You are the Investigation Agent. 
            Tools available:
            - get_entity_timeline: args {{"entity_id": str, "from_scene": int, "to_scene": int}}
            - get_scene_text: args {{"scene_number": int}}
            - get_state_at_scene: args {{"entity_id": str, "scene_number": int}}
            
            Decide next action. If you have enough evidence to resolve (found a bridge) or verify (no bridge), call 'finish' with kwargs containing FinalVerdict JSON.
            """
            
            req = LLMRequest(stage="investigation", prompt=prompt)
            try:
                res = self.provider.complete(req, AgentAction)
                action = res.value
                
                actions_taken.append(f"Called {action.tool_name} with {action.kwargs}")
                
                if action.tool_name == 'finish':
                    verdict_data = json.loads(action.kwargs)
                    return InvestigationVerdict(
                        id=f"verdict_{candidate.id}",
                        candidate_id=candidate.id,
                        status=verdict_data.get("status", "uncertain"),
                        severity="warning",
                        explanation=verdict_data.get("explanation", ""),
                        confidence=verdict_data.get("confidence", 0.0),
                        investigation_actions=actions_taken
                    )
                
                # Execute tool
                kwargs = json.loads(action.kwargs)
                tool_res = ""
                if action.tool_name == "get_entity_timeline":
                    tool_res = str(self.tools.get_entity_timeline(**kwargs))
                elif action.tool_name == "get_scene_text":
                    tool_res = str(self.tools.get_scene_text(**kwargs))
                elif action.tool_name == "get_state_at_scene":
                    tool_res = str(self.tools.get_state_at_scene(**kwargs))
                    
                context += f"\nObservation from {action.tool_name}: {tool_res}\n"
                
            except Exception as e:
                actions_taken.append(f"Error: {str(e)}")
                break

        return InvestigationVerdict(
            id=f"verdict_{candidate.id}",
            candidate_id=candidate.id,
            status="uncertain",
            severity="warning",
            explanation="Max tool calls reached without conclusion.",
            confidence=0.0,
            investigation_actions=actions_taken
        )
