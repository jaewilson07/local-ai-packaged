"""ComfyUI API service wrapper."""

import logging
from typing import Optional, Dict, Any
from uuid import UUID
import httpx

from server.projects.comfyui_workflow.services.lora_sync_service import LoRASyncService

logger = logging.getLogger(__name__)


class ComfyUIService:
    """Service for interacting with ComfyUI API."""
    
    def __init__(
        self,
        http_client: httpx.AsyncClient,
        base_url: str,
        lora_sync_service: Optional[LoRASyncService] = None
    ):
        """
        Initialize ComfyUI service.
        
        Args:
            http_client: HTTP client for ComfyUI API
            base_url: ComfyUI base URL
            lora_sync_service: Optional LoRA sync service
        """
        self.http_client = http_client
        self.base_url = base_url.rstrip("/")
        self.lora_sync_service = lora_sync_service
        self.api_endpoint = "/ai-dock/api/payload"
        self.result_endpoint = "/ai-dock/api/result"
    
    async def submit_workflow(
        self,
        workflow_json: Dict[str, Any],
        user_id: UUID
    ) -> Optional[str]:
        """
        Submit a workflow to ComfyUI.
        
        Automatically syncs user LoRA models if needed.
        
        Args:
            workflow_json: ComfyUI workflow JSON
            user_id: User UUID (for LoRA sync)
        
        Returns:
            Request ID if successful, None otherwise
        """
        # Transform workflow to inject user LoRA paths if needed
        transformed_workflow = await self._transform_workflow(workflow_json, user_id)
        
        # Prepare payload
        payload = {
            "input": {
                "request_id": "",
                "modifier": "",
                "modifications": {},
                "workflow_json": transformed_workflow
            }
        }
        
        try:
            response = await self.http_client.post(
                self.api_endpoint,
                json=payload,
                timeout=30.0
            )
            
            if response.status_code == 202:
                result = response.json()
                request_id = result.get("id")
                logger.info(f"Submitted workflow to ComfyUI, request_id: {request_id}")
                return request_id
            elif response.status_code == 401:
                logger.error("ComfyUI authentication failed")
                return None
            else:
                logger.error(f"Failed to submit workflow: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error submitting workflow to ComfyUI: {e}")
            return None
    
    async def get_job_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status from ComfyUI.
        
        Args:
            request_id: ComfyUI request ID
        
        Returns:
            Job status dictionary or None if error
        """
        try:
            response = await self.http_client.get(
                f"{self.result_endpoint}/{request_id}",
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                # Job not found (may still be processing)
                return None
            else:
                logger.error(f"Failed to get job status: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error getting job status: {e}")
            return None
    
    async def _transform_workflow(
        self,
        workflow_json: Dict[str, Any],
        user_id: UUID
    ) -> Dict[str, Any]:
        """
        Transform workflow to inject user-specific LoRA paths.
        
        Args:
            workflow_json: Original workflow JSON
            user_id: User UUID
        
        Returns:
            Transformed workflow JSON
        """
        if not self.lora_sync_service:
            # No sync service, return workflow as-is
            return workflow_json
        
        transformed = workflow_json.copy()
        
        # Find all LoraLoader nodes and transform their lora_name
        for node_id, node_data in transformed.items():
            if isinstance(node_data, dict) and node_data.get("class_type") == "LoraLoader":
                inputs = node_data.get("inputs", {})
                lora_name = inputs.get("lora_name")
                
                if lora_name:
                    # Check if this is a user LoRA (starts with user-{uuid}/)
                    # If not, it's a shared LoRA and we leave it as-is
                    if not lora_name.startswith(f"user-{user_id}/"):
                        # This might be a user LoRA that needs syncing
                        # Try to resolve it
                        synced_path = await self.lora_sync_service.ensure_lora_synced(
                            user_id=user_id,
                            lora_filename=lora_name
                        )
                        
                        if synced_path:
                            # Update the lora_name to use the synced path
                            inputs["lora_name"] = synced_path
                            logger.info(f"Updated LoRA path for node {node_id}: {lora_name} -> {synced_path}")
        
        return transformed
