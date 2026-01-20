"""
Vision analysis service for image-to-text and auto-tagging
"""

import base64
import json
import logging
from io import BytesIO

import httpx
from PIL import Image
from server.projects.controlnet_skeleton.config import get_controlnet_config
from server.projects.controlnet_skeleton.models import PreprocessorType, VisionAnalysisResult

logger = logging.getLogger(__name__)


class VisionAnalysisService:
    """Service for analyzing images using vision models"""

    def __init__(self):
        self.config = get_controlnet_config()
        self.ollama_url = f"{self.config.ollama_base_url}/api/generate"

    async def analyze_image(
        self, image_data: bytes, context: str = "ControlNet skeleton creation"
    ) -> VisionAnalysisResult:
        """
        Analyze an image using vision model

        Args:
            image_data: Raw image bytes
            context: Context for analysis (e.g., "Portrait photo", "Car interior")

        Returns:
            VisionAnalysisResult with description, tags, and suggestions
        """
        try:
            # Convert image to base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")

            # Build prompt
            prompt = self.config.vision_prompt_template.format(context=context)

            # Call Ollama vision model
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    self.ollama_url,
                    json={
                        "model": self.config.vision_model,
                        "prompt": prompt,
                        "images": [image_b64],
                        "stream": False,
                        "system": self.config.vision_system_prompt,
                    },
                )
                response.raise_for_status()
                result = response.json()

            # Parse response
            response_text = result.get("response", "")
            logger.debug(f"Vision model response: {response_text}")

            # Try to parse JSON response
            try:
                parsed = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback: extract JSON from text
                parsed = self._extract_json_from_text(response_text)

            # Build result
            return VisionAnalysisResult(
                description=parsed.get("description", "")[:500],  # Limit length
                prompt=parsed.get("prompt", parsed.get("description", ""))[:500],
                tags=parsed.get("tags", [])[:20],  # Limit tag count
                scene_composition=parsed.get("scene_composition"),
                detected_elements=parsed.get("detected_elements", [])[:20],
                suggested_preprocessor=self._parse_preprocessor(
                    parsed.get("suggested_preprocessor")
                ),
            )

        except Exception as e:
            logger.error(f"Vision analysis failed: {e}", exc_info=True)
            # Return fallback analysis
            return VisionAnalysisResult(
                description="Image analysis unavailable",
                prompt="High quality photo",
                tags=[],
                suggested_preprocessor=PreprocessorType.CANNY,  # Default fallback
            )

    async def generate_prompt_from_analysis(
        self, analysis: VisionAnalysisResult, character_lora: str | None = None
    ) -> str:
        """
        Generate an optimized prompt from vision analysis

        Args:
            analysis: Vision analysis result
            character_lora: Optional character LoRA name to include

        Returns:
            Optimized generation prompt
        """
        prompt_parts = []

        # Add character trigger if provided
        if character_lora:
            prompt_parts.append(character_lora)

        # Add description
        if analysis.description:
            prompt_parts.append(analysis.description)

        # Add key elements
        if analysis.detected_elements:
            elements = ", ".join(analysis.detected_elements[:5])
            prompt_parts.append(elements)

        # Add composition guidance
        if analysis.scene_composition:
            prompt_parts.append(analysis.scene_composition)

        # Add quality tags
        prompt_parts.extend(
            [
                "high quality",
                "detailed",
                "professional photography",
            ]
        )

        return ", ".join(prompt_parts)

    def _extract_json_from_text(self, text: str) -> dict:
        """Extract JSON object from text that may contain other content"""
        try:
            # Try to find JSON block
            start_idx = text.find("{")
            end_idx = text.rfind("}")
            if start_idx != -1 and end_idx != -1:
                json_str = text[start_idx : end_idx + 1]
                return json.loads(json_str)
        except:
            pass

        # Fallback to empty dict
        return {}

    def _parse_preprocessor(self, value: str | None) -> PreprocessorType | None:
        """Parse preprocessor type from string"""
        if not value:
            return None

        value_lower = value.lower()
        for preprocessor in PreprocessorType:
            if preprocessor.value in value_lower:
                return preprocessor

        return None

    async def suggest_preprocessor_from_tags(self, tags: list[str]) -> PreprocessorType:
        """
        Suggest the best preprocessor based on tags

        Args:
            tags: List of image tags

        Returns:
            Recommended preprocessor type
        """
        tags_lower = [tag.lower() for tag in tags]

        # Pose/body detection indicators
        if any(
            tag in tags_lower
            for tag in ["portrait", "person", "full-body", "pose", "standing", "sitting"]
        ):
            return PreprocessorType.OPENPOSE

        # Depth/3D indicators
        if any(tag in tags_lower for tag in ["interior", "room", "architecture", "depth"]):
            return PreprocessorType.DEPTH

        # Default to edge detection
        return PreprocessorType.CANNY

    def get_image_dimensions(self, image_data: bytes) -> dict[str, int]:
        """Get image dimensions from bytes"""
        try:
            image = Image.open(BytesIO(image_data))
            return {"width": image.width, "height": image.height}
        except Exception as e:
            logger.error(f"Failed to get image dimensions: {e}")
            return {"width": 0, "height": 0}
