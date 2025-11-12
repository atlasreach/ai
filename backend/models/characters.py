"""
Character Model Database
Defines available AI characters and their LoRA configurations
"""

from typing import Dict, List
from pydantic import BaseModel


class Character(BaseModel):
    """Character configuration for AI generation"""
    id: str
    name: str
    lora_model: str
    lora_strength: float
    trigger_word: str
    description: str
    thumbnail_url: str = ""

    class Config:
        json_schema_extra = {
            "example": {
                "id": "milan",
                "name": "Milan",
                "lora_model": "milan_000002000.safetensors",
                "lora_strength": 0.8,
                "trigger_word": "Milan",
                "description": "Professional female model",
                "thumbnail_url": "https://example.com/milan.jpg"
            }
        }


# Character Database
CHARACTERS: Dict[str, Character] = {
    "milan": Character(
        id="milan",
        name="Milan",
        lora_model="milan_000002000.safetensors",
        lora_strength=0.8,
        trigger_word="Milan",
        description="Professional female model trained on 2000 steps",
        thumbnail_url=""
    ),
    "milan_alt": Character(
        id="milan_alt",
        name="Milan (Alternative)",
        lora_model="milan_000001750.safetensors",
        lora_strength=0.75,
        trigger_word="Milan",
        description="Alternative Milan model trained on 1750 steps",
        thumbnail_url=""
    )
}


def get_character(character_id: str) -> Character:
    """Get character by ID"""
    if character_id not in CHARACTERS:
        raise ValueError(f"Character '{character_id}' not found")
    return CHARACTERS[character_id]


def list_characters() -> List[Character]:
    """List all available characters"""
    return list(CHARACTERS.values())
