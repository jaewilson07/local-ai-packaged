"""Selfie generation capability - handles character selfie requests via ComfyUI."""

import asyncio
import io
import logging
import re
from uuid import UUID

import aiohttp
import discord
from discord import app_commands

from bot.api_client import APIClient
from bot.capabilities.base import BaseCapability

logger = logging.getLogger(__name__)


class SelfieGenerationCapability(BaseCapability):
    """
    Selfie generation capability that handles requests for AI-generated character images.

    When a user asks a character for a selfie (e.g., "Alix, can you send me a selfie?"),
    this capability:
    1. Detects the selfie request
    2. Optimizes the prompt using the character's context
    3. Generates the image via ComfyUI using the generate-with-lora API
    4. Sends the generated image back to Discord

    Requires:
        - character_mention: To identify which character is being mentioned
    """

    name = "selfie_generation"
    description = "AI character selfie generation via ComfyUI"
    priority = 55  # Before character_mention (60) to intercept image requests
    requires = ["character_commands"]  # Needs character management

    # Patterns that indicate a selfie/image request
    SELFIE_PATTERNS = [
        r"\bselfie\b",
        r"\bpic(?:ture)?\b",
        r"\bphoto\b",
        r"\bimage\b",
        r"\bshow (?:me|us) (?:your|a|an)\b",
        r"\bsend (?:me|us) (?:a|an)\b",
        r"\bcan you (?:send|show|take)\b",
        r"\btake a picture\b",
    ]

    def __init__(
        self,
        client: discord.Client,
        api_client: APIClient,
        settings: dict | None = None,
    ):
        """
        Initialize the selfie generation capability.

        Args:
            client: The Discord client instance
            api_client: The Lambda API client for ComfyUI access
            settings: Optional capability-specific settings from Lambda API
        """
        super().__init__(client, settings=settings)
        self.api_client = api_client
        
        # Configuration from settings or defaults
        self.workflow_id = settings.get("workflow_id") if settings else None
        self.default_lora = settings.get("default_lora", "alix_character_lora_zit.safetensors")
        self.batch_size = settings.get("batch_size", 1)  # Generate 1 image by default
        self.optimize_prompt = settings.get("optimize_prompt", True)
        self.upload_to_immich = settings.get("upload_to_immich", True)
        
        # Compile regex patterns for performance
        self.selfie_regex = re.compile(
            "|".join(self.SELFIE_PATTERNS),
            re.IGNORECASE
        )

    async def on_ready(self, tree: app_commands.CommandTree) -> None:
        """
        Called when bot is ready.

        This capability doesn't register commands - it only handles messages.
        """
        logger.info("Selfie generation capability ready - listening for image requests")
        
        # Try to find a workflow if not configured
        if not self.workflow_id:
            try:
                self.workflow_id = await self._find_workflow()
                if self.workflow_id:
                    logger.info(f"Auto-discovered workflow: {self.workflow_id}")
                else:
                    logger.warning("No workflow found for selfie generation - feature may not work")
            except Exception as e:
                logger.warning(f"Failed to auto-discover workflow: {e}")

    async def on_message(self, message: discord.Message) -> bool:
        """
        Handle messages that request character selfies.

        Args:
            message: The Discord message

        Returns:
            True if a selfie was requested and generation started
        """
        try:
            # Check if message contains selfie request patterns
            if not self.selfie_regex.search(message.content):
                return False

            channel_id = str(message.channel.id)
            user_id = str(message.author.id)

            # Get active characters in channel
            try:
                characters = await self.api_client.list_characters(channel_id)
            except Exception as e:
                logger.debug(f"Error listing characters for channel {channel_id}: {e}")
                return False

            if not characters:
                return False

            # Check if message mentions any character
            message_lower = message.content.lower()
            mentioned_character: dict | None = None

            for char in characters:
                character_name = (char.get("name") or char.get("character_id", "")).lower()
                character_id = char.get("character_id", "").lower()

                # Check if character name or ID is mentioned at start or with @
                if (
                    message_lower.startswith(character_name)
                    or message_lower.startswith(character_id)
                    or f"@{character_name}" in message_lower
                    or f"@{character_id}" in message_lower
                ):
                    mentioned_character = char
                    break

            if not mentioned_character:
                return False

            character_id = mentioned_character.get("character_id")
            character_name = mentioned_character.get("name") or character_id
            character_lora = mentioned_character.get("lora") or self.default_lora

            # Send "generating" message
            generating_msg = await message.channel.send(
                f"📸 {character_name} is taking a selfie... (this may take 30-60 seconds)"
            )

            # Build prompt from message context
            # Remove character mention to get the request context
            clean_message = self._clean_message(message.content, character_name, character_id)
            
            # Build enhanced prompt with character context
            prompt = self._build_selfie_prompt(
                character_name=character_name,
                user_request=clean_message,
                character_info=mentioned_character
            )

            # Start generation in background
            asyncio.create_task(
                self._generate_and_send_selfie(
                    message=message,
                    generating_msg=generating_msg,
                    character_name=character_name,
                    character_lora=character_lora,
                    prompt=prompt,
                    profile_image=mentioned_character.get("profile_image"),
                )
            )

            return True  # We handled this message

        except Exception:
            logger.exception("Error handling selfie request")
            return False

    async def _generate_and_send_selfie(
        self,
        message: discord.Message,
        generating_msg: discord.Message,
        character_name: str,
        character_lora: str,
        prompt: str,
        profile_image: str | None,
    ):
        """
        Generate selfie image and send to Discord (runs in background).

        Args:
            message: Original Discord message
            generating_msg: The "generating..." status message
            character_name: Name of the character
            character_lora: LoRA filename for the character
            prompt: Image generation prompt
            profile_image: URL of character's profile image
        """
        try:
            # Ensure we have a workflow
            if not self.workflow_id:
                await generating_msg.edit(
                    content=f"❌ {character_name} couldn't take a selfie - no workflow configured"
                )
                return

            # Call generate-with-lora API
            result = await self._call_generate_api(
                prompt=prompt,
                character_lora=character_lora,
            )

            if not result:
                await generating_msg.edit(
                    content=f"❌ {character_name} couldn't take a selfie - API error"
                )
                return

            run_id = result.get("id")
            
            # Update status message
            await generating_msg.edit(
                content=f"🎨 {character_name} is generating your selfie... "
                f"(Run ID: `{run_id}`)"
            )

            # Poll for completion (wait up to 5 minutes)
            final_status = await self._poll_generation_status(run_id, max_wait=300)

            if not final_status:
                await generating_msg.edit(
                    content=f"⏱️ {character_name}'s selfie generation timed out. "
                    f"Check `/api/v1/comfyui/runs/{run_id}` for status."
                )
                return

            status = final_status.get("status")
            
            if status == "completed":
                # Get generated images
                output_images = final_status.get("output_images", [])
                
                if output_images:
                    # Download and send the first image
                    image_url = output_images[0]
                    image_data = await self._download_image(image_url)
                    
                    if image_data:
                        # Create embed with image
                        embed = discord.Embed(
                            description=f"Here's your selfie! 📸",
                            color=discord.Color.blue()
                        )
                        embed.set_author(name=character_name, icon_url=profile_image)
                        embed.set_footer(text=f"Generated for {message.author.display_name}")
                        
                        # Attach image
                        file = discord.File(
                            io.BytesIO(image_data),
                            filename=f"{character_name}_selfie.png"
                        )
                        embed.set_image(url=f"attachment://{character_name}_selfie.png")
                        
                        # Delete generating message and send final message
                        await generating_msg.delete()
                        await message.channel.send(embed=embed, file=file)
                        
                        # Emit event for other capabilities
                        await self.emit_event("selfie_generated", {
                            "character_name": character_name,
                            "user_id": str(message.author.id),
                            "channel_id": str(message.channel.id),
                            "run_id": run_id,
                            "image_url": image_url,
                        })
                    else:
                        await generating_msg.edit(
                            content=f"❌ {character_name} took a selfie but couldn't download it"
                        )
                else:
                    await generating_msg.edit(
                        content=f"❌ {character_name} took a selfie but no images were generated"
                    )
            elif status == "failed":
                error_msg = final_status.get("error_message", "Unknown error")
                await generating_msg.edit(
                    content=f"❌ {character_name}'s selfie failed: {error_msg}"
                )
            else:
                await generating_msg.edit(
                    content=f"⚠️ {character_name}'s selfie ended with status: {status}"
                )

        except Exception as e:
            logger.exception("Error generating selfie")
            try:
                await generating_msg.edit(
                    content=f"❌ {character_name} encountered an error: {e}"
                )
            except Exception:
                pass  # Message might have been deleted

    async def _call_generate_api(
        self,
        prompt: str,
        character_lora: str,
    ) -> dict | None:
        """
        Call the generate-with-lora API endpoint.

        Args:
            prompt: Image generation prompt
            character_lora: LoRA filename

        Returns:
            API response dict or None if error
        """
        url = f"{self.api_client.base_url}/api/v1/comfyui/generate-with-lora"
        
        payload = {
            "workflow_id": self.workflow_id,
            "prompt": prompt,
            "character_lora": character_lora,
            "batch_size": self.batch_size,
            "optimize_prompt": self.optimize_prompt,
            "upload_to_immich": self.upload_to_immich,
        }

        session = await self.api_client._get_session()
        headers = self.api_client._get_headers()

        try:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 202:
                    return await response.json()
                else:
                    logger.error(f"Generate API returned {response.status}: {await response.text()}")
                    return None
        except Exception as e:
            logger.error(f"Failed to call generate API: {e}")
            return None

    async def _poll_generation_status(
        self,
        run_id: str,
        max_wait: float = 300.0,
        poll_interval: float = 3.0,
    ) -> dict | None:
        """
        Poll generation status until completion.

        Args:
            run_id: Workflow run UUID
            max_wait: Maximum time to wait in seconds
            poll_interval: Seconds between polls

        Returns:
            Final status dict or None if timeout/error
        """
        url = f"{self.api_client.base_url}/api/v1/comfyui/runs/{run_id}"
        session = await self.api_client._get_session()
        headers = self.api_client._get_headers()

        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            if elapsed > max_wait:
                logger.warning(f"Polling timeout for run {run_id}")
                return None

            try:
                async with session.get(url, headers=headers) as response:
                    if response.status != 200:
                        logger.error(f"Status API returned {response.status}")
                        return None
                    
                    status_data = await response.json()
                    status = status_data.get("status")
                    
                    # Check for terminal state
                    if status in ("completed", "failed"):
                        return status_data
                    
                    # Wait before next poll
                    await asyncio.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling status: {e}")
                return None

    async def _download_image(self, image_url: str) -> bytes | None:
        """
        Download image from URL.

        Args:
            image_url: URL of the image

        Returns:
            Image bytes or None if error
        """
        # Handle MinIO URLs (internal vs external)
        # The API returns internal MinIO URLs, we need to convert them
        if "minio:9000" in image_url:
            # Convert internal URL to accessible URL
            image_url = image_url.replace("http://minio:9000", "http://localhost:9000")
            logger.debug(f"Converted MinIO URL to: {image_url}")

        session = await self.api_client._get_session()

        try:
            async with session.get(image_url) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"Failed to download image: {response.status}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None

    async def _find_workflow(self) -> str | None:
        """
        Find an existing workflow for selfie generation.

        Returns:
            Workflow UUID string or None if not found
        """
        url = f"{self.api_client.base_url}/api/v1/comfyui/workflows?per_page=50"
        session = await self.api_client._get_session()
        headers = self.api_client._get_headers()

        try:
            async with session.get(url, headers=headers) as response:
                if response.status != 200:
                    return None
                
                result = await response.json()
                workflows = result.get("workflows", [])

                # Look for a workflow with generate-with-lora compatibility
                for wf in workflows:
                    workflow_json = wf.get("workflow_json", {})
                    metadata = workflow_json.get("_metadata", {})
                    overrides = metadata.get("parameter_overrides", {})

                    # Check if this workflow has the required overrides
                    if "positive_prompt" in overrides or "character_lora" in overrides:
                        return wf.get("id")

                return None

        except Exception as e:
            logger.error(f"Error finding workflow: {e}")
            return None

    def _clean_message(self, content: str, character_name: str, character_id: str) -> str:
        """
        Remove character mentions from message content.

        Args:
            content: Original message content
            character_name: The character's display name
            character_id: The character's ID

        Returns:
            Cleaned message content
        """
        clean_message = content
        for name_variant in [character_name, character_id]:
            # Remove @mentions
            clean_message = re.sub(
                rf"@{re.escape(name_variant)}\s*,?\s*", "", clean_message, flags=re.IGNORECASE
            )
            # Remove name at start
            if clean_message.lower().startswith(name_variant.lower()):
                clean_message = clean_message[len(name_variant) :].strip()
                clean_message = clean_message.lstrip(",: ").strip()
        return clean_message

    def _build_selfie_prompt(
        self,
        character_name: str,
        user_request: str,
        character_info: dict,
    ) -> str:
        """
        Build an image generation prompt from user request and character context.

        Args:
            character_name: Name of the character
            user_request: User's cleaned request message
            character_info: Character information dict

        Returns:
            Image generation prompt
        """
        # Start with character name
        prompt_parts = [f"selfie of {character_name}"]
        
        # Add user's context if they specified details
        if user_request and len(user_request) > 10:
            # Extract descriptive parts (remove common selfie request words)
            descriptive_context = re.sub(
                r"\b(selfie|picture|photo|image|show|send|take|can you|please|thanks)\b",
                "",
                user_request,
                flags=re.IGNORECASE
            ).strip()
            
            if descriptive_context:
                prompt_parts.append(descriptive_context)
        
        # Add default style if no context
        if len(prompt_parts) == 1:
            prompt_parts.append("casual, friendly, natural lighting, handheld camera")
        
        return ", ".join(prompt_parts)

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # API client cleanup is handled by the shared instance in main.py
        await super().cleanup()
