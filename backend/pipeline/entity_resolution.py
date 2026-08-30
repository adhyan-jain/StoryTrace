from pydantic import BaseModel
from typing import List, Dict

class Entity(BaseModel):
    id: str
    story_universe_id: str
    type: str
    name: str
    aliases: List[str]

class EntityRegistry:
    def __init__(self, story_universe_id: str):
        self.story_universe_id = story_universe_id
        self.entities: Dict[str, Entity] = {}

    def normalize_name(self, name: str) -> str:
        return name.strip().upper()

    def resolve(self, name: str, entity_type: str = "character") -> str:
        normalized = self.normalize_name(name)

        # Simple deterministic resolution
        for entity_id, entity in self.entities.items():
            if entity.name == normalized or normalized in entity.aliases:
                return entity_id

        # If not found, create a new one deterministically
        entity_id = f"{self.story_universe_id}_{entity_type}_{normalized.replace(' ', '_')}".lower()
        self.entities[entity_id] = Entity(
            id=entity_id,
            story_universe_id=self.story_universe_id,
            type=entity_type,
            name=normalized,
            aliases=[]
        )
        return entity_id

    def get_all(self) -> List[Entity]:
        return list(self.entities.values())
