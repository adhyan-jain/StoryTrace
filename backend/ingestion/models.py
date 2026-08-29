from pydantic import BaseModel, Field

class NarrativeUnit(BaseModel):
    unit_id: str = Field(description="Unique identifier for the unit")
    story_universe_id: str = Field(description="ID of the broader universe")
    document_id: str = Field(description="ID of the document (screenplay/novel)")
    unit_type: str = Field(description="'scene', 'chapter', or 'passage'")
    sequence_number: int = Field(description="Absolute ordering number")
    title: str = Field(description="Heading or chapter title")
    page_start: int = Field(description="Starting page number")
    page_end: int = Field(description="Ending page number")
    raw_text: str = Field(description="Exact text content")
