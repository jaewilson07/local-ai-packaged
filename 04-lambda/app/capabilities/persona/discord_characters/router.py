"""Discord Characters REST API."""

import logging

from app.capabilities.persona.discord_characters import api as discord_characters_api
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)

# Include the project's API router
router.include_router(
    discord_characters_api.router, prefix="/discord/characters", tags=["discord-characters"]
)
