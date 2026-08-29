from pydantic import BaseModel, Field
from typing import List
from backend.ingestion.models import Scene
from backend.llm.base import LLMRequest
from backend.llm.client import GeminiProvider

class StateEventOutput(BaseModel):
    entity_id: str = Field(description="Unique ID for the character, prop, or location")
    attribute: str = Field(description="One of: presence, location, possession, injury, clothing")
    value: str = Field(description="The value of the state, e.g., 'lost', 'acquired', 'injured', 'healed'")
    page_ref: int = Field(description="The page number where this occurs")
    raw_excerpt: str = Field(description="The exact text from the screenplay supporting this state")
    establishment_type: str = Field(description="How it is established, e.g., 'dialogue', 'action'")
    confidence: float = Field(description="Confidence score from 0.0 to 1.0")

class SceneStateExtraction(BaseModel):
    events: List[StateEventOutput]

def extract_state_events_for_scene(scene: Scene, provider: GeminiProvider) -> List[StateEventOutput]:
    prompt = f"""
    Analyze the following scene and extract all state events regarding:
    - Character presence
    - Character location
    - Named prop possession/acquisition/loss/transfer
    - Injuries
    - Explicit clothing changes

    Scene Number: {scene.number}
    Page Range: {scene.page_start} - {scene.page_end}
    Heading: {scene.heading}

    Scene Text:
    {scene.raw_text}
    """

    request = LLMRequest(
        stage="state_extraction",
        prompt=prompt,
        system="You are an expert screenplay continuity analyst. Only extract facts directly supported by the screenplay text. Do not hallucinate state. If uncertain, omit."
    )

    result = provider.complete(request, SceneStateExtraction)
    return result.value.events
