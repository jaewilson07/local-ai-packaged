# ComfyUI Setup Guide

Complete setup guide for ComfyUI, including Docker configuration, model installation, and dependency management.

## Docker Setup

### Understanding Storage Structure

In this Docker setup:
- **Host path:** `./workspace/storage/stable_diffusion/models/`
- **Container path:** `/opt/ComfyUI/models/`
- Models are automatically synced between host and container

### Required Model Directories

The Z-Image-Turbo workflow requires these additional directories:

```bash
mkdir -p workspace/storage/stable_diffusion/models/text_encoders
mkdir -p workspace/storage/stable_diffusion/models/diffusion_models
mkdir -p workspace/storage/stable_diffusion/models/model_patches
```

See [MODELS.md](MODELS.md) for detailed model information and download instructions.

## Installing Dependencies

### Missing Dependencies (soundfile)

If you get `ModuleNotFoundError: No module named 'soundfile'`:

#### Option 1: Use Installation Script (Recommended)

```bash
./setup/install_missing_dependencies.sh
```

#### Option 2: Install Directly in Container

```bash
docker exec -it comfyui-supervisor-1 /opt/environments/python/comfyui/bin/pip install --no-cache-dir soundfile
```

#### Option 3: Add to Provisioning Script

Edit `config/provisioning/default.sh` and add to `PIP_PACKAGES`:

```bash
PIP_PACKAGES=(
    "soundfile"
    # ... other packages
)
```

#### Option 4: Install System Dependencies First

If `soundfile` installation fails, install the system library first:

```bash
docker exec -it <container_name> bash -c "apt-get update && apt-get install -y libsndfile1"
docker exec -it <container_name> /opt/environments/python/comfyui/bin/pip install --no-cache-dir soundfile
```

### FlashAttention Installation

FlashAttention is compatible with RTX 3090 (Ampere architecture, compute capability 8.6).

#### Option 1: Quick Install Script

```bash
./setup/install_flash_attention.sh
```

#### Option 2: Manual Installation

```bash
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/pip install --no-cache-dir --no-build-isolation flash-attn
```

**Note:** Installation takes 5-15 minutes as it compiles CUDA kernels.

#### Option 3: Add to Provisioning Script

Edit `config/provisioning/default.sh`:

```bash
PIP_PACKAGES=(
    "soundfile"
    "flash-attn"  # Uncomment this line
)
```

#### Verification

```bash
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -c "import flash_attn; print('✅ FlashAttention installed successfully')"
```

## Installing Custom Nodes

### Required Custom Nodes for Z-Image-Turbo

1. **ComfyUI-Controlnet-Aux**
   ```bash
   docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git"
   ```

2. **ComfyUI-Easy-Use**
   ```bash
   docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/yolili/ComfyUI-Easy-Use.git"
   ```

3. **rgthree-comfy**
   ```bash
   docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/rgthree/rgthree-comfy.git"
   ```

4. **ComfyUI-QwenVL**
   ```bash
   docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/AILab-CVC/ComfyUI-QwenVL.git"
   ```

5. **ComfyUI-Custom-Scripts**
   ```bash
   docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git"
   ```

After installing custom nodes, restart ComfyUI:

```bash
docker exec comfyui-supervisor-1 supervisorctl restart comfyui
```

## Storage Mappings

Add to `build/COPY_ROOT_1/opt/ai-dock/storage_monitor/etc/mappings.sh`:

```bash
storage_map["stable_diffusion/models/text_encoders"]="/opt/ComfyUI/models/text_encoders"
storage_map["stable_diffusion/models/diffusion_models"]="/opt/ComfyUI/models/diffusion_models"
storage_map["stable_diffusion/models/model_patches"]="/opt/ComfyUI/models/model_patches"
```

## Verification

After setup, verify everything is working:

```bash
# Check models are accessible
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/text_encoders/
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/diffusion_models/
docker exec -it <container_name> ls -lh /opt/ComfyUI/models/model_patches/

# Check custom nodes
docker exec -it <container_name> ls -lh /opt/ComfyUI/custom_nodes/

# Check dependencies
docker exec -it <container_name> /opt/environments/python/comfyui/bin/python -c "import soundfile; print('✅ soundfile OK')"
docker exec -it <container_name> /opt/environments/python/comfyui/bin/python -c "import flash_attn; print('✅ FlashAttention OK')"
```

## Restart Services

After making changes:

```bash
# Restart ComfyUI service
docker exec comfyui-supervisor-1 supervisorctl restart comfyui

# Or restart entire container
docker-compose restart
```

## Troubleshooting

### Models Not Found
- Ensure directories are created in `workspace/storage/stable_diffusion/models/`
- Check file permissions (should be readable)
- Verify Docker volume mount: `docker exec -it <container> ls /opt/ComfyUI/models/`

### Custom Nodes Missing
- Install via ComfyUI Manager UI, or
- Clone manually into `/opt/ComfyUI/custom_nodes/` inside container
- Restart container after installing nodes

### Preprocessor Models Missing
- ControlNet Aux will download them automatically on first use
- Or download manually to `custom_nodes/comfyui_controlnet_aux/models/`

## Additional Resources

- [Models Reference](MODELS.md) - Complete model information
- [Workflows Guide](WORKFLOWS.md) - Workflow management
- [Troubleshooting Guide](COMFYUI_TROUBLESHOOTING.md) - Common issues and solutions
