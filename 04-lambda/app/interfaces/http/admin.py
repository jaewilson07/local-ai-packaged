"""Admin endpoints for service monitoring and management.

Discord bot configuration is available at /admin/discord/config endpoints.
See server/projects/discord_bot_config/router.py for implementation.
"""

import logging

from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger(__name__)
