# ComfyUI Workflow Management System

## Overview

The ComfyUI Workflow Management System provides a complete multi-user solution for managing ComfyUI workflows, executing image generation tasks, and managing user-specific LoRA models. The system integrates with Supabase for workflow storage, MinIO for blob storage, and Google Drive for external LoRA model sources.

## Architecture

```
User → FastAPI (Auth) → Supabase (Workflow Storage) → ComfyUI API
                              ↓
                         MinIO (LoRA Storage) → ComfyUI Data (Synced LoRAs)
                              ↓
                    Google Drive (External LoRA Source)
```

## Components

### 1. Workflow Storage (Supabase)
- **Tables**: `comfyui_workflows`, `comfyui_workflow_runs`, `comfyui_lora_models`
- **Access Control**: Row-Level Security (RLS) policies ensure users only access their own data
- **Features**: Workflow CRUD, execution history, LoRA metadata

### 2. Blob Storage (MinIO)
- **Purpose**: Store user-specific LoRA models
- **Path Structure**: `user-{uuid}/loras/{filename}`
- **Integration**: Automatic sync to ComfyUI data directory on workflow execution

### 3. Google Drive Integration
- **Purpose**: Import LoRA models from Google Drive
- **Flow**: Download from Drive → Upload to MinIO → Sync to ComfyUI
- **Authentication**: OAuth2 with automatic token refresh

### 4. LoRA Sync Service
- **Function**: Syncs LoRA models from MinIO or Google Drive to ComfyUI data directory
- **Path**: `/basedir/models/loras/user-{uuid}/{filename}`
- **Strategy**: Check if exists, download if missing, return ComfyUI path

### 5. ComfyUI Service
- **Function**: Wraps ComfyUI API for workflow submission
- **Features**: Automatic LoRA path transformation, job status tracking

## API Endpoints

### Workflows
- `POST /api/v1/comfyui/workflows` - Create workflow
- `GET /api/v1/comfyui/workflows` - List workflows
- `GET /api/v1/comfyui/workflows/{id}` - Get workflow
- `PUT /api/v1/comfyui/workflows/{id}` - Update workflow
- `DELETE /api/v1/comfyui/workflows/{id}` - Delete workflow

### Workflow Execution
- `POST /api/v1/comfyui/workflows/{id}/run` - Execute workflow
- `GET /api/v1/comfyui/workflows/{id}/runs` - List workflow runs
- `GET /api/v1/comfyui/runs/{id}` - Get run status/result

### LoRA Models
- `POST /api/v1/comfyui/loras` - Upload LoRA (multipart/form-data)
- `POST /api/v1/comfyui/loras/import-from-google-drive` - Import from Google Drive
- `GET /api/v1/comfyui/loras` - List LoRA models
- `GET /api/v1/comfyui/loras/{id}` - Get LoRA metadata
- `DELETE /api/v1/comfyui/loras/{id}` - Delete LoRA model

## Build Dependencies: Why gcc and g++ are Required

### The Problem

When deploying the Lambda server container, Python packages that include native C/C++ extensions require compilation during installation. The `python:3.10-slim` base image is minimal and doesn't include build tools by default.

### Packages Requiring Compilation

Several dependencies in the Lambda server require native compilation:

1. **docling-core** (v2.58.1)
   - Depends on `tree-sitter-java-orchard` (v0.4.2)
   - `tree-sitter` packages are Python bindings for Tree-sitter parsers
   - Requires C/C++ compilation to build native extensions

2. **cryptography** (>=42.0.0)
   - Uses Rust and C for cryptographic operations
   - Requires build tools for compilation

3. **Other native extensions**
   - Various packages may have optional C extensions for performance
   - NumPy, SciPy, and other scientific packages often have compiled components

### Error Without Build Tools

Without `gcc`, `g++`, and `build-essential`, package installation fails with:

```
error: command 'gcc' failed: No such file or directory
hint: This usually indicates a problem with the package or the build environment.
```

### Solution

The Dockerfile includes build dependencies:

```dockerfile
# Install runtime and build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        curl \
        gcc \           # GNU C Compiler - compiles C code
        g++ \           # GNU C++ Compiler - compiles C++ code
        python3-dev \   # Python development headers (needed for C extensions)
        build-essential && \  # Meta-package including make, libc6-dev, etc.
    rm -rf /var/lib/apt/lists/*
```

### Why Keep Build Tools in Production?

**Option 1: Multi-stage Build (Not Used Here)**
- Build packages in a builder stage with build tools
- Copy only compiled packages to production stage
- **Trade-off**: More complex, but smaller final image

**Option 2: Keep Build Tools (Current Approach)**
- Simpler Dockerfile
- Allows runtime package installation/updates
- **Trade-off**: Larger image size (~100-200MB), but more flexible

**Current Choice**: Keep build tools because:
1. The Lambda server uses a persistent volume for packages (`lambda-packages`)
2. Packages are installed once and persisted
3. The entrypoint script may need to install additional packages at runtime
4. The image size increase is acceptable for the flexibility gained

### Package Installation Flow

1. **Container starts** → `docker-entrypoint.sh` runs
2. **Check venv** → If `/opt/venv/bin/python` doesn't exist:
   - Create venv: `uv venv /opt/venv`
   - Install packages: `uv pip install -e /app`
   - This compiles native extensions using `gcc`/`g++`
3. **Persist packages** → Stored in Docker volume `lambda-packages`
4. **Subsequent starts** → Reuse existing venv from volume

### Build Tools Breakdown

- **gcc**: Compiles C source code to object files
- **g++**: Compiles C++ source code to object files
- **python3-dev**: Provides Python.h header files needed to compile Python C extensions
- **build-essential**: Meta-package including:
  - `make`: Build automation tool
  - `libc6-dev`: C standard library development files
  - Other essential build tools

### Alternative: Pre-compiled Wheels

Many packages provide pre-compiled "wheels" (`.whl` files) that don't require compilation:
- **Advantage**: Faster installation, no build tools needed
- **Limitation**: Not all packages have wheels for all platforms
- **Example**: `tree-sitter-java-orchard` may not have a wheel, requiring compilation

### Performance Impact

- **Build time**: ~2-5 minutes for full package installation
- **Image size**: ~100-200MB larger with build tools
- **Runtime**: No performance impact (tools are only used during package installation)

## Configuration

### Environment Variables

**ComfyUI:**
- `COMFYUI_URL`: ComfyUI API URL (default: `http://comfyui:8188`)
- `COMFYUI_WEB_USER`: ComfyUI auth username
- `COMFYUI_WEB_PASSWORD`: ComfyUI auth password

**Google Drive (Optional):**
- `GOOGLE_CLIENT_ID` or `CLIENT_ID_GOOGLE_LOGIN`: OAuth client ID
- `GOOGLE_CLIENT_SECRET` or `CLIENT_SECRET_GOOGLE_LOGIN`: OAuth client secret
- `GDOC_TOKEN`: OAuth token JSON (with refresh token)

### Docker Volume

- **Volume**: `lambda-packages`
- **Purpose**: Persist Python packages across container restarts
- **Location**: `/opt/venv` in container
- **Benefit**: Packages installed once, reused on subsequent starts

## Usage Examples

### Import LoRA from Google Drive

```python
POST /api/v1/comfyui/loras/import-from-google-drive
{
    "google_drive_file_id": "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7",
    "name": "jw_sample_lora",
    "description": "Sample LoRA",
    "tags": ["sample"]
}
```

### Execute Workflow with LoRA

```python
POST /api/v1/comfyui/workflows/{workflow_id}/run
{
    "input_params": {
        "lora_name": "jw_sample_lora.safetensors"
    }
}
```

The system will:
1. Check if LoRA exists in ComfyUI data directory
2. If missing, sync from MinIO or Google Drive
3. Transform workflow JSON to use correct LoRA path
4. Submit to ComfyUI API

## Troubleshooting

### Server Not Starting

**Issue**: Container restarting with `ModuleNotFoundError`

**Solution**: 
1. Check if build tools are installed: `docker exec lambda-server which gcc`
2. Rebuild container: `docker compose build --no-cache lambda-server`
3. Remove old volume: `docker volume rm 04-lambda_lambda-packages`
4. Restart: `docker compose up -d lambda-server`

### Package Installation Fails

**Issue**: `error: command 'gcc' failed`

**Solution**: Ensure Dockerfile includes build dependencies (gcc, g++, python3-dev, build-essential)

### Redirect Loop on API Access

**Issue**: "redirected too many times" when accessing endpoints

**Solution**: 
- Use correct hostname: `https://api.datacrew.space` (not `datacrew.space`)
- Ensure Cloudflare Access is configured for `api.datacrew.space`
- Access through Cloudflare Access (which injects JWT header automatically)

## Future Enhancements

- [ ] Workflow templates and sharing
- [ ] Batch workflow execution
- [ ] Workflow versioning
- [ ] LoRA model versioning
- [ ] Automatic LoRA sync on workflow execution
- [ ] Workflow scheduling/cron
- [ ] Webhook notifications for workflow completion
