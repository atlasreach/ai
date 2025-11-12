"""
Characters API Router
Endpoints for listing and retrieving AI characters
"""

from fastapi import APIRouter, HTTPException
from typing import List
from backend.models.characters import Character, list_characters, get_character


router = APIRouter(prefix="/characters", tags=["characters"])


@router.get("/", response_model=List[Character])
async def get_all_characters():
    """
    Get list of all available characters

    Returns:
        List of Character objects
    """
    return list_characters()


@router.get("/{character_id}", response_model=Character)
async def get_character_by_id(character_id: str):
    """
    Get specific character by ID

    Args:
        character_id: Character identifier (e.g., "milan")

    Returns:
        Character object

    Raises:
        404: Character not found
    """
    try:
        return get_character(character_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
