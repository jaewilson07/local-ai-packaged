"""Parameter validation and substitution service for ComfyUI workflows."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class ParameterValidationError(Exception):
    """Raised when parameter validation fails."""


class ParameterService:
    """Service for validating and substituting parameters in ComfyUI workflows."""

    def validate_parameters(
        self, parameters: dict[str, Any], parameter_schema: dict[str, Any] | None
    ) -> dict[str, Any]:
        """
        Validate parameters against parameter schema.

        Args:
            parameters: User-provided parameters
            parameter_schema: Workflow parameter schema definition

        Returns:
            Validated and normalized parameters with defaults applied

        Raises:
            ParameterValidationError: If validation fails
        """
        if not parameter_schema:
            # No schema defined, return parameters as-is
            return parameters

        validated = {}

        for param_name, param_def in parameter_schema.items():
            param_type = param_def.get("type", "string")
            required = param_def.get("required", False)
            default = param_def.get("default")

            # Get value from parameters or use default
            value = parameters.get(param_name)

            if value is None:
                if required:
                    raise ParameterValidationError(f"Required parameter '{param_name}' is missing")
                elif default is not None:
                    value = default
                else:
                    continue  # Skip optional parameters without defaults

            # Type validation and conversion
            try:
                if param_type == "integer":
                    value = int(value)
                    # Check min/max if specified
                    if "min" in param_def and value < param_def["min"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be >= {param_def['min']}"
                        )
                    if "max" in param_def and value > param_def["max"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be <= {param_def['max']}"
                        )
                elif param_type == "string":
                    value = str(value)
                    # Check min/max length if specified
                    if "minLength" in param_def and len(value) < param_def["minLength"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be at least {param_def['minLength']} characters"
                        )
                    if "maxLength" in param_def and len(value) > param_def["maxLength"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be at most {param_def['maxLength']} characters"
                        )
                elif param_type == "boolean":
                    value = bool(value)
                elif param_type == "number":
                    value = float(value)
                    # Check min/max if specified
                    if "min" in param_def and value < param_def["min"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be >= {param_def['min']}"
                        )
                    if "max" in param_def and value > param_def["max"]:
                        raise ParameterValidationError(
                            f"Parameter '{param_name}' must be <= {param_def['max']}"
                        )

                validated[param_name] = value

            except (ValueError, TypeError) as e:
                raise ParameterValidationError(
                    f"Parameter '{param_name}' must be of type {param_type}: {e}"
                )

        # Add any additional parameters not in schema (for workflow-specific params)
        for key, value in parameters.items():
            if key not in validated and key not in parameter_schema:
                validated[key] = value

        return validated

    def substitute_parameters(
        self,
        workflow_json: dict[str, Any],
        parameters: dict[str, Any],
        lora_paths: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Substitute parameters in workflow JSON.

        This method performs parameter substitution in the workflow JSON:
        - Replaces prompt text in CLIPTextEncode nodes
        - Updates num_images in batch nodes
        - Replaces LoRA paths in LoraLoader nodes

        Args:
            workflow_json: Original workflow JSON
            parameters: Validated parameters
            lora_paths: Optional dict mapping lora names to file paths
                       (e.g., {"Alyx": "user-{uuid}/alix_lora.safetensors"})

        Returns:
            Modified workflow JSON with parameters substituted
        """
        import copy

        modified_workflow = copy.deepcopy(workflow_json)

        # Substitute prompt
        prompt = parameters.get("prompt")
        if prompt:
            # Find CLIPTextEncode nodes and update text input
            for node_id, node_data in modified_workflow.items():
                if isinstance(node_data, dict):
                    class_type = node_data.get("class_type")
                    if class_type == "CLIPTextEncode":
                        inputs = node_data.get("inputs", {})
                        # Update text input (usually key is "text")
                        if "text" in inputs:
                            inputs["text"] = prompt

        # Substitute num_images
        num_images = parameters.get("num_images", 1)
        if num_images and num_images > 1:
            # Find batch nodes or empty latent image nodes
            for node_id, node_data in modified_workflow.items():
                if isinstance(node_data, dict):
                    class_type = node_data.get("class_type")
                    if class_type in ("EmptyLatentImage", "KSampler"):
                        inputs = node_data.get("inputs", {})
                        # Update batch size
                        if "batch_size" in inputs:
                            inputs["batch_size"] = num_images

        # Substitute LoRA paths
        if lora_paths:
            for node_id, node_data in modified_workflow.items():
                if isinstance(node_data, dict):
                    class_type = node_data.get("class_type")
                    if class_type == "LoraLoader":
                        inputs = node_data.get("inputs", {})
                        lora_name = inputs.get("lora_name")

                        # Check if this LoRA matches any in lora_paths
                        for lora_key, lora_path in lora_paths.items():
                            # Match by character name or custom name
                            if lora_name and (
                                lora_key.lower() in lora_name.lower()
                                or lora_name.lower() in lora_key.lower()
                            ):
                                inputs["lora_name"] = lora_path
                                logger.info(
                                    f"Substituted LoRA path for node {node_id}: {lora_name} -> {lora_path}"
                                )
                                break

        # Substitute any additional workflow-specific parameters
        additional_params = parameters.get("additional_params", {})
        if additional_params:
            # This is a generic substitution - can be extended for specific node types
            for node_id, node_data in modified_workflow.items():
                if isinstance(node_data, dict):
                    inputs = node_data.get("inputs", {})
                    for param_key, param_value in additional_params.items():
                        if param_key in inputs:
                            inputs[param_key] = param_value

        return modified_workflow
