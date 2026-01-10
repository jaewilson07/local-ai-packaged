# Qwen Image Edit Service - Analysis

## Overview

The Qwen Image Edit service from wandering-athena provides a RunPod serverless handler for the Qwen-Image-Edit-2509 model, enabling image editing capabilities through a Diffusers pipeline.

## Current Implementation in wandering-athena

**Location**: `src/services/image_generation/runpod_service.py`

### Key Features

1. **RunPod Serverless Handler**
   - Designed for A100 (80GB) instances
   - Global model loading pattern to mitigate cold starts
   - Supports both creation (via noise/base) and editing workflows

2. **Model Details**
   - Model: `Qwen/Qwen-Image-Edit-2509`
   - Precision: bfloat16 (required for 20B model to fit in memory)
   - Device: CUDA (with CPU fallback)

3. **API Interface**
   - Input: JSON with prompt, optional base64 image, negative prompt, inference steps, guidance scale, seed
   - Output: Base64 encoded edited image with metadata
   - Error handling for invalid inputs and model failures

4. **Utilities**
   - Base64 image encoding/decoding
   - PIL Image conversion
   - Error handling and logging

## Current State in local-ai-packaged

### Existing Image Generation

- **ComfyUI** exists in `02-compute/comfyui/`
  - Full ComfyUI installation with Docker Compose
  - Supports multiple workflows (Z-Image-Turbo, ControlNet, etc.)
  - API wrapper available at `/ai-dock/api/`
  - Port: 8188 (configurable)
  - GPU support (NVIDIA CUDA, AMD ROCm, CPU)

### Missing Capabilities

- No Qwen Image Edit integration
- No serverless image editing service
- No direct Diffusers pipeline integration
- No RunPod deployment support

## Integration Requirements

### Option 1: Integrate with ComfyUI Stack

**Approach**: Add Qwen Image Edit as a ComfyUI custom node or workflow

**Pros**:
- Leverages existing ComfyUI infrastructure
- No new service needed
- Can use existing GPU resources

**Cons**:
- Requires ComfyUI workflow creation
- May not match RunPod serverless pattern
- Different API interface

**Implementation Steps**:
1. Create ComfyUI custom node for Qwen Image Edit
2. Add Qwen-Image-Edit-2509 model to ComfyUI models directory
3. Create workflow JSON for image editing
4. Expose via ComfyUI API wrapper

### Option 2: Add as Lambda Project

**Approach**: Create new project in `04-lambda/server/projects/qwen_image_edit/`

**Pros**:
- Matches wandering-athena pattern
- Can expose via REST API and MCP
- Independent service management
- Can use RunPod or local GPU

**Cons**:
- Requires new service setup
- Needs GPU access (may conflict with ComfyUI)
- Additional dependencies

**Implementation Steps**:
1. Create `04-lambda/server/projects/qwen_image_edit/` directory
2. Implement service using Diffusers (similar to wandering-athena)
3. Add REST API endpoints in `04-lambda/server/api/`
4. Add MCP tools in `04-lambda/server/mcp/`
5. Add Docker Compose service (if needed) or use existing GPU resources

### Option 3: Hybrid Approach

**Approach**: Lambda project that calls ComfyUI for GPU resources

**Pros**:
- Best of both worlds
- Reuses existing GPU infrastructure
- Clean API interface

**Cons**:
- More complex architecture
- Requires ComfyUI API integration

## Dependencies

### Required Python Packages

```python
# From wandering-athena
diffusers>=0.21.0  # For QwenImageEditPipeline
torch>=2.0.0       # PyTorch with CUDA support
Pillow>=9.0.0     # Image processing
runpod>=1.0.0     # Optional, for serverless deployment
```

### Model Requirements

- **Model**: Qwen/Qwen-Image-Edit-2509 (~20B parameters)
- **VRAM**: ~40GB+ (with bfloat16)
- **Storage**: ~40GB for model files

### System Requirements

- CUDA-capable GPU (A100 80GB recommended, RTX 3090 24GB minimum)
- Python 3.10+
- CUDA 11.8+ or 12.1+

## Code Reference

### Key Functions from wandering-athena

```python
# Model loading
pipeline = QwenImageEditPipeline.from_pretrained(
    "Qwen/Qwen-Image-Edit-2509",
    torch_dtype=torch.bfloat16
)

# Image processing
def decode_base64_image(image_string):
    image_data = base64.b64decode(image_string)
    return Image.open(io.BytesIO(image_data)).convert("RGB")

def encode_image_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# Inference
output = pipeline(
    prompt=prompt,
    image=pil_image,
    negative_prompt=negative_prompt,
    num_inference_steps=steps,
    true_cfg_scale=cfg_scale,
    generator=generator
)
```

## Integration Points

### With Existing Services

1. **ComfyUI** (`02-compute/comfyui/`)
   - Can share GPU resources
   - Can use same Docker network (`ai-network`)
   - Can leverage existing model storage

2. **Lambda Stack** (`04-lambda/`)
   - Can add as new project
   - Can expose via REST API
   - Can expose via MCP tools

3. **Storage**
   - Can use existing MinIO for image storage
   - Can integrate with Supabase Storage

## Recommended Approach

**Phase 1**: Add as Lambda project with local GPU support
- Create `04-lambda/server/projects/qwen_image_edit/`
- Implement service class
- Add REST API endpoints
- Add MCP tools
- Test with local GPU

**Phase 2**: Optional RunPod integration
- Add RunPod deployment option
- Create serverless handler
- Configure for cloud deployment

## Implementation Checklist

- [ ] Create project directory structure
- [ ] Add dependencies to `pyproject.toml`
- [ ] Implement QwenImageEditService class
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Create Docker Compose service (if separate container needed)
- [ ] Add environment variables for configuration
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- Qwen Image Edit requires a base image (doesn't generate from scratch)
- Model is large (~20B parameters) - requires significant VRAM
- bfloat16 precision is mandatory for memory efficiency
- Consider model quantization for smaller GPUs
- May need to coordinate GPU usage with ComfyUI if sharing resources
