# Z-Image-Turbo Models Reference

Complete reference for all models required and available for Z-Image-Turbo workflows.

## Core Models

### Text Encoder
- **File:** `qwen_3_4b.safetensors`
- **Directory:** `text_encoders/`
- **URL:** https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors
- **Size:** ~3.4 GB
- **Used by:** CLIPLoader node

### Diffusion Model
- **File:** `z_image_turbo_bf16.safetensors`
- **Directory:** `diffusion_models/`
- **URL:** https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors
- **Size:** ~12 GB
- **Used by:** UNETLoader node

### VAE
- **File:** `ae.safetensors`
- **Directory:** `vae/`
- **URL:** https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors
- **Size:** ~320 MB
- **Used by:** VAELoader node

### ControlNet Model Patches

#### ControlNet Union V1.0
- **File:** `Z-Image-Turbo-Fun-Controlnet-Union.safetensors`
- **Directory:** `model_patches/`
- **URL:** https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors
- **Size:** ~2.9 GB

#### ControlNet Union V2.0/V2.1
- **File:** `Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors`
- **Directory:** `model_patches/`
- **URL:** https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.0/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union-2.0.safetensors
- **Size:** ~6.3 GB

#### ControlNet Union V2.1 (8-steps variant)
- **File:** `Z-Image-Turbo-Fun-Controlnet-Union-2.1-8steps.safetensors`
- **Directory:** `model_patches/`
- **Size:** ~6.3 GB

#### Style Models
- **File:** `pixel_art_style_z_image_turbo.safetensors`
- **Directory:** `model_patches/`
- **Size:** ~163 MB

### Optional: GGUF Model
- **File:** `z_image_turbo-Q8_0.gguf`
- **Directory:** `unet/`
- **Size:** ~6.8 GB
- **Used by:** GGUF loader nodes

## Preprocessor Models

These are auto-downloaded by ControlNet Aux custom node on first use:

- `depth_anything_vitl14.pth` - Depth estimation
- `yolox_l.onnx` - Pose detection (bbox)
- `dw-ll_ucoco_384_bs5.torchscript.pt` - Pose estimation

**Location:** `/opt/ComfyUI/custom_nodes/comfyui_controlnet_aux/models/`

## Directory Structure

```
workspace/storage/stable_diffusion/models/
├── text_encoders/
│   └── qwen_3_4b.safetensors
├── diffusion_models/
│   └── z_image_turbo_bf16.safetensors
├── vae/
│   └── ae.safetensors
├── model_patches/
│   ├── Z-Image-Turbo-Fun-Controlnet-Union.safetensors
│   ├── Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors
│   ├── Z-Image-Turbo-Fun-Controlnet-Union-2.1-8steps.safetensors
│   └── pixel_art_style_z_image_turbo.safetensors
└── unet/
    └── z_image_turbo-Q8_0.gguf
```

**Container paths:** `/opt/ComfyUI/models/` (same structure)

## Quick Download

Use the provided script:

```bash
./setup/download_z_image_turbo_models.sh ./workspace/storage/stable_diffusion
```

Or download manually:

```bash
# Text Encoder
wget -O workspace/storage/stable_diffusion/models/text_encoders/qwen_3_4b.safetensors \
  https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors

# Diffusion Model
wget -O workspace/storage/stable_diffusion/models/diffusion_models/z_image_turbo_bf16.safetensors \
  https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/diffusion_models/z_image_turbo_bf16.safetensors

# VAE
wget -O workspace/storage/stable_diffusion/models/vae/ae.safetensors \
  https://huggingface.co/Comfy-Org/z_image_turbo/resolve/main/split_files/vae/ae.safetensors

# ControlNet Union V1.0
wget -O workspace/storage/stable_diffusion/models/model_patches/Z-Image-Turbo-Fun-Controlnet-Union.safetensors \
  https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union.safetensors

# ControlNet Union V2.0
wget -O workspace/storage/stable_diffusion/models/model_patches/Z-Image-Turbo-Fun-Controlnet-Union-2.1.safetensors \
  https://huggingface.co/alibaba-pai/Z-Image-Turbo-Fun-Controlnet-Union-2.0/resolve/main/Z-Image-Turbo-Fun-Controlnet-Union-2.0.safetensors
```

## Storage Mappings

The following storage mappings ensure models are accessible in Docker:

```bash
storage_map["stable_diffusion/models/text_encoders"]="/opt/ComfyUI/models/text_encoders"
storage_map["stable_diffusion/models/diffusion_models"]="/opt/ComfyUI/models/diffusion_models"
storage_map["stable_diffusion/models/model_patches"]="/opt/ComfyUI/models/model_patches"
```

## Verification

Check models are accessible:

```bash
# On host
ls -lh workspace/storage/stable_diffusion/models/text_encoders/
ls -lh workspace/storage/stable_diffusion/models/diffusion_models/
ls -lh workspace/storage/stable_diffusion/models/vae/
ls -lh workspace/storage/stable_diffusion/models/model_patches/

# In container
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/text_encoders/
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/diffusion_models/
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/model_patches/
```

## Total Size

**Estimated total:** ~30-35 GB (including all variants)

Ensure sufficient disk space before downloading!





