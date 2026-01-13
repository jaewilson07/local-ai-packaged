"""Capability registry for managing bot capabilities."""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

import discord
from discord import app_commands

if TYPE_CHECKING:
    from bot.capabilities.base import BaseCapability

logger = logging.getLogger(__name__)


@dataclass
class CapabilityEvent:
    """
    Event that can be emitted by capabilities for inter-capability communication.

    Attributes:
        event_type: Type of event (e.g., "upload_complete", "character_response")
        source: Name of the capability that emitted the event
        data: Event-specific data payload
        timestamp: When the event was created
    """

    event_type: str
    source: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


# Type alias for event handlers
EventHandler = Callable[[CapabilityEvent], Coroutine[Any, Any, None]]


class CapabilityRegistry:
    """
    Registry for managing bot capabilities.

    Handles capability registration, initialization, and message routing.
    Capabilities are processed in priority order (lower priority number = higher priority).
    """

    def __init__(self, client: discord.Client):
        """
        Initialize the capability registry.

        Args:
            client: The Discord client instance
        """
        self.client = client
        self._capabilities: dict[str, BaseCapability] = {}
        self._sorted_capabilities: list[BaseCapability] = []
        self._event_handlers: dict[
            str, list[tuple[str, EventHandler]]
        ] = {}  # event_type -> [(capability_name, handler)]

    def register(self, capability: "BaseCapability") -> None:
        """
        Register a capability.

        Args:
            capability: The capability instance to register

        Raises:
            ValueError: If capability has unmet dependencies
        """
        if capability.name in self._capabilities:
            logger.warning(f"Capability '{capability.name}' already registered, replacing")

        # Set registry reference for event communication
        capability.set_registry(self)

        self._capabilities[capability.name] = capability
        self._update_sorted_list()
        logger.info(f"Registered capability: {capability.name} (priority: {capability.priority})")

    def validate_dependencies(self) -> list[str]:
        """
        Validate that all registered capabilities have their dependencies met.

        Returns:
            List of error messages for unmet dependencies (empty if all valid)
        """
        errors = []
        registered_names = set(self._capabilities.keys())

        for capability in self._capabilities.values():
            for required in capability.requires:
                if required not in registered_names:
                    errors.append(
                        f"Capability '{capability.name}' requires '{required}' which is not registered"
                    )

        return errors

    def subscribe(self, event_type: str, capability_name: str, handler: EventHandler) -> None:
        """
        Subscribe a capability to receive events of a specific type.

        Args:
            event_type: Type of event to subscribe to
            capability_name: Name of the subscribing capability
            handler: Async function to call when event is emitted
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append((capability_name, handler))
        logger.debug(f"Capability '{capability_name}' subscribed to '{event_type}' events")

    def unsubscribe(self, event_type: str, capability_name: str) -> None:
        """
        Unsubscribe a capability from events of a specific type.

        Args:
            event_type: Type of event to unsubscribe from
            capability_name: Name of the capability to unsubscribe
        """
        if event_type in self._event_handlers:
            self._event_handlers[event_type] = [
                (name, handler)
                for name, handler in self._event_handlers[event_type]
                if name != capability_name
            ]
            logger.debug(f"Capability '{capability_name}' unsubscribed from '{event_type}' events")

    async def emit(self, event: CapabilityEvent) -> None:
        """
        Emit an event to all subscribed capabilities.

        Args:
            event: The event to emit
        """
        handlers = self._event_handlers.get(event.event_type, [])
        if not handlers:
            logger.debug(f"No handlers for event type '{event.event_type}'")
            return

        logger.debug(
            f"Emitting '{event.event_type}' from '{event.source}' to {len(handlers)} handlers"
        )

        # Execute all handlers concurrently
        tasks = []
        for capability_name, handler in handlers:
            # Skip self-notifications unless explicitly allowed
            if capability_name != event.source:
                tasks.append(self._call_handler(capability_name, handler, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _call_handler(
        self, capability_name: str, handler: EventHandler, event: CapabilityEvent
    ) -> None:
        """
        Call a single event handler with error handling.

        Args:
            capability_name: Name of the capability handling the event
            handler: The handler function
            event: The event to handle
        """
        try:
            await handler(event)
        except Exception:
            logger.exception(
                f"Error in capability '{capability_name}' handling event '{event.event_type}'"
            )

    def _update_sorted_list(self) -> None:
        """Update the sorted capability list by priority."""
        self._sorted_capabilities = sorted(self._capabilities.values(), key=lambda c: c.priority)

    def get(self, name: str) -> "BaseCapability | None":
        """
        Get a capability by name.

        Args:
            name: The capability name

        Returns:
            The capability instance or None if not found
        """
        return self._capabilities.get(name)

    @property
    def capabilities(self) -> list["BaseCapability"]:
        """Get all registered capabilities sorted by priority."""
        return self._sorted_capabilities

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Call on_ready for all registered capabilities.

        Args:
            tree: The command tree for registering slash commands
        """
        for capability in self._sorted_capabilities:
            if capability.enabled:
                try:
                    await capability.on_ready(tree)
                    logger.info(f"Capability '{capability.name}' ready")
                except Exception:
                    logger.exception(f"Error in capability '{capability.name}' on_ready")

    async def handle_message(self, message: discord.Message) -> bool:
        """
        Route a message through all capabilities.

        Capabilities are processed in priority order. The first capability
        to return True stops further processing.

        Args:
            message: The Discord message to handle

        Returns:
            True if any capability handled the message
        """
        for capability in self._sorted_capabilities:
            if not capability.enabled:
                continue

            try:
                handled = await capability.on_message(message)
                if handled:
                    logger.debug(f"Message handled by capability '{capability.name}'")
                    return True
            except Exception:
                logger.exception(f"Error in capability '{capability.name}' on_message")

        return False

    async def cleanup(self) -> None:
        """Cleanup all capabilities."""
        for capability in self._sorted_capabilities:
            try:
                await capability.cleanup()
            except Exception:
                logger.exception(f"Error cleaning up capability '{capability.name}'")

        self._capabilities.clear()
        self._sorted_capabilities.clear()
        logger.info("All capabilities cleaned up")
