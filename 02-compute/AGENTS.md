# Compute Stack - AGENTS.md

> **Multi-Editor Support**: Both GitHub Copilot and Cursor AI read this file. Rules here override the root AGENTS.md for compute layer concerns.

> **Override**: This file extends [../AGENTS.md](../AGENTS.md). Compute layer rules take precedence.

## Component Identity

**Stack**: `02-compute`  
**Purpose**: AI model inference and image generation  
**Docker Compose**: `02-compute/docker-compose.yml` (stack-level compose for ollama and comfyui)  
**Profiles**: CPU, GPU-NVIDIA, GPU-AMD (profile-based service selection)

**Network**: Uses external `ai-network`

## Folder Structure

**Stack-Level Files**:
- `docker-compose.yml` - Stack-level compose (ollama, comfyui with profiles)
- `AGENTS.md` - This file (stack-specific rules)

**Service-Specific Folders**:
- `ollama/` - Ollama service folder
  - `data/` - Model storage (bind mount to `/root/.ollama`)
- `comfyui/` - ComfyUI service folder
  - `config/` - ComfyUI configuration files
  - `data/` - ComfyUI workspace, models, workflows (bind mount to `/comfy/mnt`)
    - `basedir/` - Model storage (bind mount to `/basedir`)
  - `scripts/` - ComfyUI utility scripts (provision-models.py, etc.) - mounted to `/provision:ro`
  - `upstream/` - Cloned upstream repositories
  - `docs/` - ComfyUI-specific documentation
  - `README.md` - ComfyUI setup and usage

## Ollama

### Architecture
- **Image**: `ollama/ollama:latest` (CPU/NVIDIA) or `ollama/ollama:rocm` (AMD)
- **Container**: `ollama` (profile-specific: `ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`)
- **Port**: 11434 (internal only)
- **Volume**: `./ollama/data:/root/.ollama` (local bind mount)

### Configuration
- **Context Length**: `OLLAMA_CONTEXT_LENGTH=8192`
- **Flash Attention**: `OLLAMA_FLASH_ATTENTION=1`
- **KV Cache**: `OLLAMA_KV_CACHE_TYPE=q8_0`
- **Max Loaded Models**: `OLLAMA_MAX_LOADED_MODELS=2`

### GPU Support
- **NVIDIA**: Uses `deploy.resources.reservations.devices` with `nvidia` driver
- **AMD**: Uses `devices` mapping for `/dev/kfd` and `/dev/dri`
- **CPU**: No GPU configuration (default)

### Model Provisioning
- **Init Container**: `ollama-pull-llama-*` (profile-specific)
- **Default Models**:
  - `qwen2.5:7b-instruct-q4_K_M` (instruction-tuned LLM)
  - `qwen3-embedding:4b` (embedding model)
- **Trigger**: Runs automatically on first start (one-time)

### Patterns
```yaml
# Service Definition
x-service-ollama: &service-ollama
  volumes:
    - ./ollama/data:/root/.ollama
  # ... other config
```

## ComfyUI

### Architecture
- **Image**: `mmartial/comfyui-nvidia-docker:latest`
- **Container**: `comfyui` (profile-specific variants)
- **Port**: 8188 (API)
- **Volumes**:
  - `./comfyui/data:/comfy/mnt` - Working directory
  - `./comfyui/data/basedir:/basedir` - Model storage

### Configuration
- **Base Directory**: `BASE_DIRECTORY=/basedir`
- **Security Level**: `SECURITY_LEVEL=normal`
- **Package Manager**: `USE_UV=true` (uses `uv` instead of pip)

### GPU Support
- **NVIDIA**: Same pattern as Ollama (deploy.resources)
- **AMD**: Device mapping for ROCm
- **CPU**: No GPU configuration

### Model Provisioning
- **Init Container**: `comfyui-provision-*` (profile-specific)
- **Provision Scripts**:
  - `/provision/provision-models.py` (mapped from `./comfyui/scripts/provision-models.py`)
  - `/provision/provision-models.sh` (mapped from `./comfyui/scripts/provision-models.sh`)
- **Trigger**: Runs on first start if provision script exists

### Patterns
```yaml
# Service definition uses anchor
x-comfyui: &service-comfyui
  image: mmartial/comfyui-nvidia-docker:latest
  volumes:
    - ./comfyui/data:/comfy/mnt
    - ./comfyui/data/basedir:/basedir
  # ... shared config

x-init-comfyui: &init-comfyui
  volumes:
    - ./comfyui/data:/comfy/mnt
    - ./comfyui/data/basedir:/basedir
    - ./comfyui/scripts:/provision:ro
```

## Architecture Patterns

### Profile-Based Service Selection
Services are defined once with anchors, then instantiated per profile:
```yaml
x-service: &service-base
  # ... shared config

service-cpu:
  profiles: ["cpu"]
  <<: *service-base

service-gpu:
  profiles: ["gpu-nvidia"]
  <<: *service-base
  # ... GPU-specific overrides
```

### Init Containers
One-time provisioning containers that run after main service starts:
- **Dependencies**: `depends_on` with service name
- **Entrypoint**: `/bin/sh -c "sleep N; command"`
- **Volumes**: Share storage with main service

### Volume Management
- **Ollama**: `./ollama/data` (bind mount)
- **ComfyUI**: `./comfyui/data` (bind mount)
- **Models**: Stored in bind mounts, not committed to git (ignored via .gitignore)

## Testing & Validation

### Health Checks
```bash
# Ollama
curl http://ollama:11434/api/tags

# ComfyUI
curl http://comfyui:8188/
```

### GPU Validation
```bash
# NVIDIA
nvidia-smi  # Host system
docker exec ollama nvidia-smi  # Container

# AMD
ls /dev/kfd /dev/dri  # Host system
```

### Common Issues
1. **GPU Not Detected**:
   - NVIDIA: Check `nvidia-container-toolkit` installation
   - AMD: Verify `/dev/kfd` and `/dev/dri` exist
2. **Model Download Fails**: Check network connectivity and disk space
3. **ComfyUI Provision Fails**: Verify provision script exists in `scripts/`
4. **Profile Mismatch**: Ensure `--profile` flag matches service profile

## Do's and Don'ts

### ✅ DO
- Use profile-based service selection
- Share volumes between main and init containers
- Test GPU availability before starting services
- Use anchors for shared service configs
- Store models in `data/` bind mounts

### ❌ DON'T
- Hardcode GPU device paths
- Mix CPU and GPU profiles in same compose command
- Commit model files to git
- Skip GPU validation (check before starting)
- Use different image tags for same service across profiles (except AMD)

## Domain Dictionary

- **Ollama**: Local LLM inference engine (supports many models)
- **ComfyUI**: Node-based Stable Diffusion interface and API
- **Profile**: Docker Compose feature for conditional service activation
- **Init Container**: One-time setup container (runs after main service)
- **ROCm**: AMD's GPU compute platform (alternative to CUDA)
- **Flash Attention**: Optimized attention mechanism for transformers

---

**See Also**:
- [../AGENTS.md](../AGENTS.md) for universal rules
- [start_services.py](../start_services.py) for GPU validation logic
