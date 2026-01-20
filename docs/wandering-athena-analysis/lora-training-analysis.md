# LoRA Training Service - Analysis

## Overview

The LoRA training service from wandering-athena provides a complete pipeline for training character LoRAs on Z-Image-De-Turbo using the Ostris AI-Toolkit. It includes automatic configuration generation, caption tools, validation workflows, and training orchestration.

## Current Implementation in wandering-athena

**Location**: `src/services/lora_training/`

### Key Components

1. **LoRATrainer** (`trainer.py`)
   - Main training orchestration service
   - Subprocess management for AI-Toolkit
   - Result tracking and error handling
   - Configuration validation

2. **ConfigGenerator** (`config_generator.py`)
   - YAML configuration generation for Ostris AI-Toolkit
   - Multi-resolution support with resolution bucketing
   - AI-Toolkit format compliance

3. **CaptionGenerator** (`caption_generator.py`)
   - Basic caption file creation (.txt files)
   - JoyCaption VLM integration
   - Folder-level caption management
   - Image filename conforming based on captions
   - Validation utilities

4. **VisionCaptioner** (`vision_captioner.py`)
   - LLaVA-based image captioning using JoyCaption
   - Custom prompt templates (descriptive, sd-prompt, midjourney)
   - Batch processing support
   - GPU/CPU device management

5. **Caption Validation Workflow** (`caption_validation_workflow.py`)
   - LangGraph-based validation pipeline
   - PydanticAI + OpenAI integration
   - Non-destructive YAML-based review system
   - Batch approval and application

6. **Models** (`models.py`)
   - `LoRATrainingConfig`: Type-safe configuration with validation
   - `TrainingResult`: Result object with success status, paths, timing

### Key Features

- **Automatic YAML Generation**: Creates AI-Toolkit compatible config files
- **Configuration Validation**: Checks paths, parameters before training starts
- **Multi-Resolution Support**: Resolution bucketing for better generalization
- **Progress Tracking**: Returns detailed training results and timing
- **Error Handling**: Comprehensive error messages and result objects
- **Caption Tools**: Built-in caption generation and validation
- **VLM Integration**: JoyCaption for automatic detailed captions

## Current State in local-ai-packaged

### Existing Image Generation

- **ComfyUI** exists in `02-compute/comfyui/`
  - Full ComfyUI installation with Docker Compose
  - Supports Z-Image-Turbo workflows
  - API wrapper available
  - GPU support (NVIDIA CUDA, AMD ROCm, CPU)

### Missing Capabilities

- No LoRA training capabilities
- No caption generation or validation tools
- No Ostris AI-Toolkit integration
- No training pipeline orchestration
- No VLM-based captioning

## Integration Requirements

### Option 1: Integrate with ComfyUI Stack

**Approach**: Add LoRA training as a service within ComfyUI container or as a separate service

**Pros**:
- Leverages existing GPU infrastructure
- Can share model storage with ComfyUI
- Uses existing Docker Compose setup

**Cons**:
- Requires Ostris AI-Toolkit installation
- May need separate container for training isolation
- Different workflow from ComfyUI generation

**Implementation Steps**:
1. Add Ostris AI-Toolkit to ComfyUI container or create separate training container
2. Create training service in `04-lambda/src/capabilities/training/lora_training/`
3. Add REST API endpoints for training operations
4. Add MCP tools for training management
5. Integrate with existing storage (MinIO/Supabase) for training data

### Option 2: Add as Lambda Project

**Approach**: Create new project in `04-lambda/src/capabilities/training/lora_training/`

**Pros**:
- Matches wandering-athena pattern
- Can expose via REST API and MCP
- Independent service management
- Can use existing GPU resources

**Cons**:
- Requires Ostris AI-Toolkit installation
- Needs GPU access (may conflict with ComfyUI)
- Additional dependencies

**Implementation Steps**:
1. Create `04-lambda/src/capabilities/training/lora_training/` directory
2. Port trainer, config generator, and caption tools from wandering-athena
3. Add REST API endpoints in `04-lambda/server/api/`
4. Add MCP tools in `04-lambda/src/mcp_server/`
5. Create Docker Compose service or use existing GPU resources

### Option 3: Hybrid Approach

**Approach**: Lambda project that orchestrates training in ComfyUI container or separate training container

**Pros**:
- Best of both worlds
- Reuses existing GPU infrastructure
- Clean API interface
- Training isolation

**Cons**:
- More complex architecture
- Requires container orchestration

## Dependencies

### Required Python Packages

```python
# Core training
pyyaml>=6.0          # YAML config generation
pathlib              # Path handling (stdlib)

# Caption generation
transformers>=4.30.0  # For VisionCaptioner (JoyCaption)
torch>=2.0.0         # PyTorch with CUDA support
Pillow>=9.0.0       # Image processing
accelerate>=0.20.0   # Model loading optimization

# Validation workflow
pydantic-ai>=0.1.0   # For caption validation (already in local-ai-packaged)
langgraph>=0.1.0     # For validation workflow (if using LangGraph)
```

### External Dependencies

- **Ostris AI-Toolkit**: Must be cloned and installed
  - Repository: https://github.com/ostris/ai-toolkit
  - Required for actual training execution
  - Provides `run.py` script for training

- **Base Model**: Z-Image-De-Turbo
  - Model: `ostris/Z-Image-De-Turbo`
  - Training adapter LoRA required: `ostris/zimage_turbo_training_adapter/zimage_turbo_training_adapter_v1.safetensors`

- **JoyCaption Model** (for VLM captioning):
  - Model: `fancyfeast/llama-joycaption-alpha-two-hf-llava`
  - Optional but recommended for quality captions

### System Requirements

- CUDA-capable GPU (8GB+ VRAM minimum, 24GB recommended)
- Python 3.10+
- CUDA 11.8+ or 12.1+
- 20GB+ free disk space for models and training data

## Code Reference

### Key Classes from wandering-athena

```python
# Training configuration
config = LoRATrainingConfig(
    character_name="my_character",
    image_folder="data/training/my_character",
    output_dir="data/lora-trainer/my_character",
    steps=2500,
    rank=16,
    alpha=16,
    resolutions=[[1024, 1024], [768, 1024], [1024, 768]],
    ai_toolkit_path="ai-toolkit",
)

# Training execution
trainer = LoRATrainer(ai_toolkit_path="ai-toolkit")
result = trainer.train_from_config(config)

# Caption generation
caption_gen = CaptionGenerator()
stats = caption_gen.create_captions_for_folder(
    image_folder="data/training/my_character",
    character_name="my character",
    use_vlm=True,  # Use VisionCaptioner
    vlm_style="descriptive",
)

# Caption validation
validation_yaml = await validate_and_save_to_yaml(
    folder_path="data/training/my_character",
    character_name="my character",
    style="terse",
)
```

## Integration Points

### With Existing Services

1. **ComfyUI** (`02-compute/comfyui/`)
   - Can share GPU resources
   - Can use same Docker network (`ai-network`)
   - Can leverage existing model storage
   - Trained LoRAs can be used in ComfyUI workflows

2. **Lambda Stack** (`04-lambda/`)
   - Can add as new project
   - Can expose via REST API
   - Can expose via MCP tools
   - Can integrate with existing storage

3. **Storage**
   - Can use existing MinIO for training data storage
   - Can integrate with Supabase Storage
   - Training outputs (LoRA files) can be stored in shared storage

4. **Ollama** (`02-compute/`)
   - Could potentially use Ollama for caption generation (alternative to JoyCaption)
   - Would need vision model support

## Recommended Approach

**Phase 1**: Add as Lambda project with training container
- Create `04-lambda/src/capabilities/training/lora_training/`
- Port core training service classes
- Add REST API endpoints
- Add MCP tools
- Create separate training container with Ostris AI-Toolkit

**Phase 2**: Add caption tools
- Port CaptionGenerator and VisionCaptioner
- Add caption generation endpoints
- Add validation workflow

**Phase 3**: Integration and optimization
- Integrate with storage systems
- Add training job queue
- Add progress tracking
- Add notification system

## Implementation Checklist

- [ ] Create project directory structure
- [ ] Add dependencies to `pyproject.toml`
- [ ] Port LoRATrainer class
- [ ] Port ConfigGenerator class
- [ ] Port CaptionGenerator class
- [ ] Port VisionCaptioner class (optional, requires transformers)
- [ ] Port caption validation workflow (optional, requires LangGraph)
- [ ] Add REST API endpoints
- [ ] Add MCP tool definitions
- [ ] Create Docker Compose service for training (with Ostris AI-Toolkit)
- [ ] Add environment variables for configuration
- [ ] Create documentation
- [ ] Add tests
- [ ] Update README

## Notes

- LoRA training requires 5-20 high-quality images (9-12 ideal)
- Each image needs a corresponding .txt caption file
- Training on Z-Image-De-Turbo (not Turbo) is required
- Training adapter LoRA is mandatory
- bfloat16 precision is used for memory efficiency
- Multi-resolution training improves generalization
- Caption quality significantly impacts training results
- VLM-based captions (JoyCaption) produce better results than generic captions
- Consider model quantization for smaller GPUs
- Training can take 30-60 minutes depending on steps and GPU
