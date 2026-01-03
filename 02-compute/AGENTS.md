# Compute Stack - AGENTS.md

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
- `data/` - Shared data directory for model storage
  - `ollama/` - Ollama model storage (mounted from volume)
  - `comfyui/` - ComfyUI workspace and models

**Service-Specific Folders**:
- `ollama/` - Ollama service folder
  - (Currently empty - service defined in stack-level compose)
  - (Future: `docs/`, `config/` if service-specific configs needed)
- `comfyui/` - ComfyUI service folder
  - `docker-compose.yaml` - Service-specific compose (if needed for independent management)
  - `data/` - ComfyUI workspace, models, workflows (bind mount)
  - `scripts/` - ComfyUI utility scripts (provision-models.py, etc.)
  - `docs/` - ComfyUI-specific documentation
  - `config/` - ComfyUI configuration files
  - `README.md` - ComfyUI setup and usage

**Refactoring Notes**:
- Ollama and ComfyUI are currently in stack-level compose (shared profiles)
- ComfyUI has extensive service-specific resources (data, scripts, docs) in its folder
- Ollama folder exists for consistency (even though empty) - follows "every service gets a folder" rule
- If services need independent management, move to service-specific compose files

## Ollama

### Architecture
- **Image**: `ollama/ollama:latest` (CPU/NVIDIA) or `ollama/ollama:rocm` (AMD)
- **Container**: `ollama` (profile-specific: `ollama-cpu`, `ollama-gpu`, `ollama-gpu-amd`)
- **Port**: 11434 (internal only)
- **Volume**: `ollama_storage` (model storage)

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
  - `nomic-embed-text` (embedding model)
- **Trigger**: Runs automatically on first start (one-time)

### Patterns
```yaml
# CPU Profile
ollama-cpu:
  profiles: ["cpu"]
  <<: *service-ollama

# NVIDIA GPU Profile
ollama-gpu:
  profiles: ["gpu-nvidia"]
  <<: *service-ollama
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]

# AMD GPU Profile
ollama-gpu-amd:
  profiles: ["gpu-amd"]
  <<: *service-ollama
  image: ollama/ollama:rocm
  devices:
    - "/dev/kfd"
    - "/dev/dri"
```

### Key Files
- `02-compute/docker-compose.yml` - Service definitions with profiles
- `02-compute/data/ollama/` - Model storage (mounted from volume)

### Search Hints
```bash
# Find Ollama configuration
rg -n "ollama" 02-compute/docker-compose.yml

# Find GPU profile definitions
rg -n "gpu-nvidia\|gpu-amd" 02-compute/docker-compose.yml

# Check Ollama logs
docker logs ollama
```

## ComfyUI

### Architecture
- **Image**: `mmartial/comfyui-nvidia-docker:latest`
- **Container**: `comfyui` (profile-specific variants)
- **Port**: 8188 (API)
- **Volumes**:
  - `./data/comfyui:/comfy/mnt` - Working directory
  - `./data/comfyui/basedir:/basedir` - Model storage

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
  - `./data/comfyui/provision-models.py` (Python)
  - `./data/comfyui/provision-models.sh` (Shell)
- **Trigger**: Runs on first start if provision script exists

### Patterns
```yaml
# Service definition uses anchor
x-comfyui: &service-comfyui
  image: mmartial/comfyui-nvidia-docker:latest
  # ... shared config

# Profile-specific services
comfyui-cpu:
  profiles: ["cpu"]
  <<: *service-comfyui

comfyui-gpu:
  profiles: ["gpu-nvidia"]
  <<: *service-comfyui
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

### Key Files
- `02-compute/docker-compose.yml` - Service definitions
- `02-compute/data/comfyui/` - ComfyUI workspace and models
- `02-compute/data/comfyui/ComfyUI/` - ComfyUI source (if cloned)
- `02-compute/data/comfyui/ComfyUI/tests/` - pytest test suite

### Testing
- **Unit Tests**: `pytest tests-unit/` (requires test dependencies)
- **Inference Tests**: `pytest tests/inference` (requires models)
- **Quality Regression**: Compare baseline images with generated outputs

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
- **Ollama**: `ollama_storage` (Docker volume, not in repo)
- **ComfyUI**: `./data/comfyui/` (bind mount, in repo)
- **Models**: Stored in volumes, not committed to git

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
3. **ComfyUI Provision Fails**: Verify provision script exists and is executable
4. **Profile Mismatch**: Ensure `--profile` flag matches service profile

## Do's and Don'ts

### ✅ DO
- Use profile-based service selection
- Share volumes between main and init containers
- Test GPU availability before starting services
- Use anchors for shared service configs
- Store models in volumes (not in repo)

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

