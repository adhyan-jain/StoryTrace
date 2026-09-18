from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class TemporalAnchor(str, Enum):
    CONTINUOUS = "CONTINUOUS"
    MOMENTS_LATER = "MOMENTS_LATER"
    SAME_DAY = "SAME_DAY"
    NEXT_DAY = "NEXT_DAY"
    DAYS_LATER = "DAYS_LATER"
    MONTHS_LATER = "MONTHS_LATER"
    YEARS_LATER = "YEARS_LATER"
    FLASHBACK = "FLASHBACK"
    DREAM_SEQUENCE = "DREAM_SEQUENCE"

class VerdictStatusV2(str, Enum):
    VERIFIED_HARD_CONFLICT = "verified_hard_conflict"
    VERIFIED_NARRATIVE_ANOMALY = "verified_narrative_anomaly"
    RESOLVED = "resolved"
    UNCERTAIN = "uncertain"

class StateEventV2(BaseModel):
    id: str
    story_universe_id: str
    entity_id: str
    attribute: str
    value: str
    unit_id: str
    sequence_number: int
    page_ref: int
    raw_excerpt: str
    establishment_type: str = "direct_action"
    confidence: float = 1.0
    hier_setting_type: str = ""      # INT, EXT, INT/EXT
    hier_environment: str = ""       # e.g. POLICE_STATION, WAREHOUSE, APARTMENT
    hier_specific_room: str = ""     # e.g. INTERROGATION_ROOM, KITCHEN, ROOF
    hier_city_region: str = ""       # e.g. NEW_YORK, PARIS, BOSTON
    time_anchor: str = "CONTINUOUS"  # CONTINUOUS, MOMENTS_LATER, DAY, NIGHT, FLASHBACK
    related_entity_id: str = ""      # e.g. character_b in transfer / holding

class SceneCoPresence(BaseModel):
    id: str
    story_universe_id: str
    unit_id: str
    sequence_number: int
    entity_ids: List[str] = Field(default_factory=list)
    setting_type: str = ""
    environment: str = ""
    specific_room: str = ""
    time_of_day: str = ""
    time_anchor: str = "CONTINUOUS"

class CandidateConflictV2(BaseModel):
    id: str
    story_universe_id: str
    rule_type: str                  # possession_machine, co_presence_collision, continuous_spatial_jump, physical_inversion, epistemic_rupture
    entity_ids: List[str] = Field(default_factory=list)
    attribute: str
    prior_evidence_unit_id: str
    prior_evidence_excerpt: str
    current_evidence_unit_id: str
    current_evidence_excerpt: str
    description: str
    severity_hint: str = "warning"

class InvestigationVerdictV2(BaseModel):
    id: str
    candidate_id: str
    status: VerdictStatusV2
    severity: str                   # critical, warning, info
    explanation: str
    confidence: float
    investigation_actions: List[str] = Field(default_factory=list)
    suggested_fix: str = ""
