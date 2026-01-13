"""Base capability class for modular bot features."""

import logging
from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands

if TYPE_CHECKING:
    from bot.capabilities.registry import CapabilityEvent, CapabilityRegistry

logger = logging.getLogger(__name__)


class BaseCapability(ABC):
    """
    Base class for bot capabilities.

    Each capability represents a modular feature that can be enabled/disabled
    via configuration. Capabilities handle specific message types, commands,
    or background tasks.

    Lifecycle:
    1. __init__() - Called when capability is instantiated
    2. on_ready() - Called when Discord bot is ready (register commands here)
    3. on_message() - Called for each message (return True if handled)
    4. cleanup() - Called when bot is shutting down
    """

    # Unique name for this capability (used in ENABLED_CAPABILITIES config)
    name: str = "base"

    # Human-readable description
    description: str = "Base capability"

    # Priority for message handling (lower = higher priority)
    # Capabilities are processed in priority order; first to return True stops chain
    priority: int = 100

    # List of capability names that this capability requires
    # Used for dependency validation during load_capabilities()
    requires: list[str] = []

    def __init__(self, client: discord.Client, settings: dict[str, Any] | None = None):
        """
        Initialize the capability.

        Args:
            client: The Discord client instance
            settings: Optional capability-specific settings from Lambda API
        """
        self.client = client
        self.enabled = True
        self.settings = settings or {}
        self._registry: CapabilityRegistry | None = None
        logger.info(
            f"Capability '{self.name}' initialized with settings: {list(self.settings.keys())}"
        )

    def set_registry(self, registry: "CapabilityRegistry") -> None:
        """
        Set the registry reference for event communication.

        Called by CapabilityRegistry.register() - not typically called directly.

        Args:
            registry: The capability registry instance
        """
        self._registry = registry

    async def emit_event(self, event_type: str, data: dict[str, Any] | None = None) -> None:
        """
        Emit an event to other capabilities.

        Use this for inter-capability communication, like notifying other
        capabilities when an action completes.

        Args:
            event_type: Type of event (e.g., "upload_complete", "character_added")
            data: Optional event data payload

        Example:
            await self.emit_event("upload_complete", {
                "filename": "photo.jpg",
                "asset_id": "abc123",
                "user_id": "12345"
            })
        """
        if self._registry is None:
            logger.warning(f"Capability '{self.name}' tried to emit event but registry not set")
            return

        from bot.capabilities.registry import CapabilityEvent

        event = CapabilityEvent(event_type=event_type, source=self.name, data=data or {})
        await self._registry.emit(event)

    def subscribe_to_event(
        self, event_type: str, handler: Callable[["CapabilityEvent"], Coroutine[Any, Any, None]]
    ) -> None:
        """
        Subscribe to events from other capabilities.

        Call this in on_ready() to set up event handlers.

        Args:
            event_type: Type of event to subscribe to
            handler: Async function to call when event is received

        Example:
            async def handle_upload(event):
                print(f"File uploaded: {event.data.get('filename')}")

            self.subscribe_to_event("upload_complete", handle_upload)
        """
        if self._registry is None:
            logger.warning(f"Capability '{self.name}' tried to subscribe but registry not set")
            return

        self._registry.subscribe(event_type, self.name, handler)

    def unsubscribe_from_event(self, event_type: str) -> None:
        """
        Unsubscribe from events of a specific type.

        Args:
            event_type: Type of event to unsubscribe from
        """
        if self._registry is None:
            return

        self._registry.unsubscribe(event_type, self.name)

    @abstractmethod
    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when the Discord bot is ready.

        Use this to register slash commands or perform one-time setup.

        Args:
            tree: The command tree for registering slash commands
        """

    @abstractmethod
    async def on_message(self, message: discord.Message) -> bool:
        """
        Handle an incoming message.

        Args:
            message: The Discord message to handle

        Returns:
            True if the message was handled (stops further capability processing)
            False to allow other capabilities to process the message
        """

    async def cleanup(self) -> None:
        """
        Cleanup resources when the bot is shutting down.

        Override this to stop background tasks, close connections, etc.
        """
        logger.info(f"Capability '{self.name}' cleaning up")

    def is_bot_mentioned(self, message: discord.Message) -> bool:
        """
        Check if the bot is mentioned in the message.

        Args:
            message: The Discord message to check

        Returns:
            True if the bot is @mentioned in the message
        """
        if self.client.user is None:
            return False
        return self.client.user.mentioned_in(message)

    def get_message_without_mention(self, message: discord.Message) -> str:
        """
        Get the message content with bot mentions removed.

        Args:
            message: The Discord message

        Returns:
            Message content with bot @mentions stripped
        """
        content = message.content
        if self.client.user:
            # Remove <@BOT_ID> and <@!BOT_ID> patterns
            content = content.replace(f"<@{self.client.user.id}>", "").strip()
            content = content.replace(f"<@!{self.client.user.id}>", "").strip()
        return content
