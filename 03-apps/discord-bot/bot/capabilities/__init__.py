"""Bot capabilities module."""

from bot.capabilities.base import BaseCapability
from bot.capabilities.character_commands import CharacterCommandsCapability
from bot.capabilities.character_mention import CharacterMentionCapability
from bot.capabilities.registry import CapabilityEvent, CapabilityRegistry

__all__ = [
    "BaseCapability",
    "CapabilityEvent",
    "CapabilityRegistry",
    "CharacterCommandsCapability",
    "CharacterMentionCapability",
]
