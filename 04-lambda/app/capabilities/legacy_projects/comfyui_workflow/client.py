"""ComfyUI API client for workflow execution."""

import asyncio
import logging
from typing import Any

import aiohttp

from .config import ComfyUIConfig

logger = logging.getLogger(__name__)


class ComfyUIClient:
    """Async client for ComfyUI API."""

    def __init__(self, config: ComfyUIConfig | None = None):
        self.config = config or ComfyUIConfig()
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            headers = {"Content-Type": "application/json"}
            if self.config.is_remote and self.config.comfyui_access_token:
                headers["CF-Access-Token"] = self.config.comfyui_access_token
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=self.config.submit_timeout),
            )
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def submit_workflow(self, workflow_json: dict[str, Any]) -> str | None:
        """Submit a workflow to ComfyUI using standard /prompt endpoint.

        Args:
            workflow_json: ComfyUI workflow in API format

        Returns:
            Prompt ID if successful, None otherwise
        """
        import uuid

        session = await self._get_session()
        url = f"{self.config.comfyui_url.rstrip('/')}{self.config.submit_endpoint}"

        # Generate a unique client_id for this submission
        client_id = str(uuid.uuid4())

        # Standard ComfyUI /prompt payload format
        payload = {
            "prompt": workflow_json,
            "client_id": client_id,
        }

        try:
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    # Standard ComfyUI returns {"prompt_id": "..."}
                    prompt_id = result.get("prompt_id")
                    if prompt_id:
                        logger.info(f"Workflow submitted successfully: {prompt_id}")
                        return prompt_id
                    # Check for error in response
                    error = result.get("error")
                    if error:
                        logger.error(f"ComfyUI error: {error}")
                    return None
                body = await response.text()
                logger.error(f"ComfyUI submit failed: {response.status} - {body[:200]}")
                return None
        except Exception as e:
            logger.exception(f"Error submitting workflow: {e}")
            return None

    async def get_result(self, request_id: str) -> dict[str, Any] | None:
        """Get workflow execution result from history.

        Args:
            request_id: The prompt_id returned from submit

        Returns:
            Result dict with status and outputs, or None
        """
        session = await self._get_session()
        url = f"{self.config.comfyui_url.rstrip('/')}{self.config.history_endpoint}/{request_id}"

        try:
            async with session.get(url) as response:
                if response.status == 200:
                    history = await response.json()
                    # History returns {prompt_id: {status: {...}, outputs: {...}}}
                    if request_id in history:
                        prompt_data = history[request_id]
                        status_data = prompt_data.get("status", {})
                        outputs = prompt_data.get("outputs", {})

                        # Check if completed (status_str indicates completion)
                        status_str = status_data.get("status_str", "unknown")
                        completed = status_data.get("completed", False)

                        if completed or status_str == "success":
                            return {
                                "status": "completed",
                                "outputs": outputs,
                            }
                        if status_str == "error":
                            messages = status_data.get("messages", [])
                            error_msg = (
                                "; ".join(str(m) for m in messages) if messages else "Unknown error"
                            )
                            return {
                                "status": "failed",
                                "error": error_msg,
                            }
                        return {
                            "status": "running",
                        }
                    return None
                return None
        except Exception as e:
            logger.warning(f"Error getting result: {e}")
            return None

    async def poll_for_completion(
        self, request_id: str, timeout: int | None = None, poll_interval: int | None = None
    ) -> dict[str, Any] | None:
        timeout = timeout or self.config.poll_timeout
        poll_interval = poll_interval or self.config.poll_interval
        start_time = asyncio.get_event_loop().time()

        while True:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout:
                return None

            result = await self.get_result(request_id)
            if result:
                status = result.get("status")
                if status in ("completed", "failed"):
                    return result

            await asyncio.sleep(poll_interval)

    async def get_image(
        self, filename: str, subfolder: str = "", folder_type: str = "output"
    ) -> bytes | None:
        session = await self._get_session()
        params = {"filename": filename, "subfolder": subfolder, "type": folder_type}
        url = f"{self.config.comfyui_url.rstrip('/')}{self.config.view_endpoint}"

        try:
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.read()
                return None
        except Exception as e:
            logger.warning(f"Error getting image: {e}")
            return None

    def extract_output_images(self, result: dict[str, Any]) -> list[dict[str, str]]:
        images = []
        outputs = result.get("outputs", {})
        for node_output in outputs.values():
            if isinstance(node_output, dict):
                for value in node_output.values():
                    if isinstance(value, list):
                        for img_data in value:
                            if isinstance(img_data, dict) and "filename" in img_data:
                                images.append(
                                    {
                                        "filename": img_data.get("filename"),
                                        "subfolder": img_data.get("subfolder", ""),
                                        "type": img_data.get("type", "output"),
                                    }
                                )
        return images
