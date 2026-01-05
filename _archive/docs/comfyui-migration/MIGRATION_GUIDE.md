# Migration Guide: From ai-dock ComfyUI to Standard ComfyUI Docker

This guide helps you migrate from the custom ai-dock ComfyUI setup to a standard ComfyUI Docker installation while preserving all your customizations.

## Overview

This project includes portable setup scripts that work with both:
- **ai-dock ComfyUI** (current setup)
- **Standard ComfyUI Docker** (target setup)
- **Local ComfyUI installations**

All customizations have been preserved and adapted to work across these environments.

## Key Differences

### ai-dock ComfyUI
- Container name: `comfyui-supervisor-1`
- Python path: `/opt/environments/python/comfyui/bin/python`
- ComfyUI path: `/opt/ComfyUI`
- Service management: `supervisorctl restart comfyui`
- Includes: Service portal, Jupyter, API wrapper, authentication

### Standard ComfyUI Docker
- Container name: `comfyui` (or similar)
- Python path: `python3` (inside container)
- ComfyUI path: `/app` or `/ComfyUI`
- Service management: `docker restart <container_name>`
- Includes: Just ComfyUI

## Migration Steps

### Step 1: Set Up Standard ComfyUI Docker

1. **Pull the standard ComfyUI Docker image:**
   ```bash
   docker pull comfyanonymous/comfyui:latest
   ```

2. **Create a docker-compose.yml for standard ComfyUI:**
   ```yaml
   version: '3.8'
   services:
     comfyui:
       image: comfyanonymous/comfyui:latest
       container_name: comfyui
       restart: unless-stopped
       ports:
         - "8188:8188"
       volumes:
         - ./models:/app/models
         - ./output:/app/output
         - ./input:/app/input
         - ./custom_nodes:/app/custom_nodes
       deploy:
         resources:
           reservations:
             devices:
               - driver: nvidia
                 count: all
                 capabilities: [gpu]
   ```

3. **Start the container:**
   ```bash
   docker-compose up -d
   ```

### Step 2: Run Provisioning

The provisioning script automatically detects your environment and works with standard ComfyUI:

```bash
./setup/provision_comfyui.sh
```

This will:
- Install custom nodes from `config/provisioning/default.sh`
- Install Python packages
- Download models (checkpoints, VAE, ControlNet, LoRA, etc.)

### Step 3: Verify Installation

```bash
# Check environment detection
./setup/comfyui_env.sh

# Verify PyTorch and CUDA
./setup/verify_pytorch_cuda.sh

# Run diagnostics
./setup/comfyui_diagnostics.sh
```

### Step 4: Use Setup Scripts

All setup scripts now work with standard ComfyUI:

```bash
# Install missing dependencies
./setup/install_missing_dependencies.sh

# Install FlashAttention
./setup/install_flash_attention.sh

# Update ComfyUI
./setup/update_comfyui.sh

# Manage custom nodes
./setup/custom_nodes_setup.sh list
./setup/custom_nodes_setup.sh install-module rotary_embedding_torch
```

## Environment Detection

The setup scripts automatically detect your environment:

1. **Inside container** - Detects ai-dock vs standard ComfyUI paths
2. **Docker exec mode** - Finds running ComfyUI containers
3. **Local installation** - Finds local ComfyUI directory

You can manually check detection:

```bash
source setup/comfyui_env.sh
detect_environment
print_environment
```

## Preserved Customizations

### 1. Setup Scripts (`setup/`)
All scripts have been updated to work with standard ComfyUI:
- ✅ `install_missing_dependencies.sh`
- ✅ `install_flash_attention.sh`
- ✅ `update_comfyui.sh`
- ✅ `verify_pytorch_cuda.sh`
- ✅ `comfyui_diagnostics.sh`
- ✅ `custom_nodes_setup.sh` (from previous plan)
- ✅ `provision_comfyui.sh` (new portable provisioning)

### 2. Provisioning Configuration (`config/provisioning/`)
Your provisioning configs are preserved and work with the new script:
- ✅ `default.sh` - Main provisioning config
- ✅ Custom node lists
- ✅ Python package lists
- ✅ Model download URLs

### 3. Workflow Management
Workflow scripts work with both environments:
- ✅ `add_workflow.py`
- ✅ `save_workflow_direct.py`
- ✅ `import_workflow.sh`

## Model Paths

### ai-dock
- Models: `/opt/ComfyUI/models/`
- Mapped from: `workspace/storage/stable_diffusion/models/`

### Standard ComfyUI Docker
- Models: `/app/models/` (or `/ComfyUI/models/`)
- Mapped from: `./models` (host directory)

The provisioning script automatically handles path differences.

## Custom Nodes

Custom nodes are installed to:
- **ai-dock**: `/opt/ComfyUI/custom_nodes/`
- **Standard Docker**: `/app/custom_nodes/` (mapped to `./custom_nodes`)

The provisioning script installs nodes to the correct location based on detected environment.

## Troubleshooting

### Scripts Can't Find Container

If scripts can't auto-detect your container:

1. **Check container name:**
   ```bash
   docker ps --format '{{.Names}}'
   ```

2. **Set container name manually:**
   ```bash
   export CONTAINER_NAME="your-container-name"
   source setup/comfyui_env.sh
   detect_environment
   ```

### Python Path Issues

If Python commands fail:

1. **Verify Python in container:**
   ```bash
   docker exec <container_name> python3 --version
   ```

2. **Check ComfyUI path:**
   ```bash
   docker exec <container_name> ls -la /app
   # or
   docker exec <container_name> ls -la /ComfyUI
   ```

### Model Downloads Fail

If model downloads fail:

1. **Check authentication tokens:**
   ```bash
   echo $HF_TOKEN
   echo $CIVITAI_TOKEN
   ```

2. **Verify network access:**
   ```bash
   docker exec <container_name> curl -I https://huggingface.co
   ```

## One-Command Setup

For a fresh standard ComfyUI installation:

```bash
./setup/standard_comfyui_setup.sh
```

This runs the complete provisioning process.

## Rollback

If you need to rollback to ai-dock:

1. The scripts still work with ai-dock containers
2. Just ensure your ai-dock container is running
3. Scripts will auto-detect and use ai-dock paths

## Next Steps

1. ✅ Set up standard ComfyUI Docker
2. ✅ Run provisioning script
3. ✅ Verify installation
4. ✅ Test workflows
5. ✅ Migrate any custom configurations

## Support

If you encounter issues:

1. Check environment detection: `source setup/comfyui_env.sh && detect_environment && print_environment`
2. Review logs: `docker logs <container_name>`
3. Run diagnostics: `./setup/comfyui_diagnostics.sh`

