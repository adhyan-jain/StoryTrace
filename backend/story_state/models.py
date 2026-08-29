from pydantic import BaseModel
from typing import List, Optional

class StateEvent(BaseModel):
    id: str
    screenplay_id: str
    entity_id: str
    attribute: str
    value: str
    scene_id: str
    scene_number: int
    page_ref: int
    raw_excerpt: str
    establishment_type: str
    confidence: float

class CandidateConflict(BaseModel):
    id: str
    screenplay_id: str
    entity_id: str
    prior_evidence_scene_id: str
    prior_evidence_excerpt: str
    current_evidence_scene_id: str
    current_evidence_excerpt: str
    description: str

class InvestigationVerdict(BaseModel):
    id: str
    candidate_id: str
    status: str
    severity: str
    explanation: str
    confidence: float
    investigation_actions: List[str]
