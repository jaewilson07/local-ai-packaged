"""Discord Characters REST API."""

from fastapi import APIRouter
import logging

from server.projects.discord_characters import api as discord_characters_api

router = APIRouter()
logger = logging.getLogger(__name__)

# Include the project's API router
router.include_router(
    discord_characters_api.router,
    prefix="/discord/characters",
    tags=["discord-characters"]
)
