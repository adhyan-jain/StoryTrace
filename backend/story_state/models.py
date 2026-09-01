from pydantic import BaseModel
from typing import List, Optional

class StateEvent(BaseModel):
    id: str
    story_universe_id: str
    entity_id: str
    attribute: str
    value: str
    unit_id: str
    sequence_number: int
    page_ref: int
    raw_excerpt: str
    establishment_type: str
    confidence: float

class CandidateConflict(BaseModel):
    id: str
    story_universe_id: str
    entity_id: str
    attribute: str
    prior_evidence_unit_id: str
    prior_evidence_excerpt: str
    current_evidence_unit_id: str
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
    suggested_fix: str = ""
