# ComfyUI Workflow Management Project

Multi-user ComfyUI workflow management system with user-specific LoRA model support.

## Overview

This project provides a complete system for managing ComfyUI workflows in a multi-user environment:

- **Workflow Storage**: Store workflow configs in Supabase with Row-Level Security (RLS)
- **Workflow Execution**: Submit workflows to ComfyUI API and track execution
- **LoRA Model Management**: Upload, store, and sync user-specific LoRA models
- **Access Control**: Users can only access their own workflows and LoRA models (or public workflows)

## Features

- **Workflow CRUD**: Create, read, update, delete workflows
- **Workflow Execution**: Execute workflows via ComfyUI API with automatic LoRA sync
- **Execution History**: Track workflow runs with status and output images
- **LoRA Management**: Upload LoRA models to MinIO, sync to ComfyUI on demand
- **User Isolation**: Strict access control via Supabase RLS policies

## Architecture

```
User → FastAPI (Auth) → Supabase (Workflow Storage) → ComfyUI API
                              ↓
                         MinIO (LoRA Storage) → ComfyUI Data (Synced LoRAs)
```

## Database Schema

See `01-data/supabase/migrations/001_comfyui_workflows.sql` for the complete schema.

**Tables:**
- `comfyui_workflows`: Workflow configs with user ownership
- `comfyui_workflow_runs`: Execution history and results
- `comfyui_lora_models`: LoRA model metadata

**RLS Policies:**
- Users can only see their own workflows (or public ones)
- Users can only create/update/delete their own workflows
- Similar policies for workflow runs and LoRA models

## API Endpoints

### Workflows

- `POST /api/v1/comfyui/workflows` - Create workflow
- `GET /api/v1/comfyui/workflows` - List workflows
- `GET /api/v1/comfyui/workflows/{workflow_id}` - Get workflow
- `PUT /api/v1/comfyui/workflows/{workflow_id}` - Update workflow
- `DELETE /api/v1/comfyui/workflows/{workflow_id}` - Delete workflow

### Workflow Execution

- `POST /api/v1/comfyui/workflows/{workflow_id}/run` - Execute workflow
- `GET /api/v1/comfyui/workflows/{workflow_id}/runs` - List workflow runs
- `GET /api/v1/comfyui/runs/{run_id}` - Get run status/result

### LoRA Models

- `POST /api/v1/comfyui/loras` - Upload LoRA model
- `GET /api/v1/comfyui/loras` - List LoRA models
- `GET /api/v1/comfyui/loras/{lora_id}` - Get LoRA metadata
- `DELETE /api/v1/comfyui/loras/{lora_id}` - Delete LoRA model

## LoRA Model Sync

When a workflow uses a user's LoRA model:

1. **Check**: Service checks if LoRA exists in ComfyUI data directory
2. **Sync**: If missing, downloads from MinIO and copies to ComfyUI
3. **Transform**: Updates workflow JSON to use synced LoRA path
4. **Submit**: Submits transformed workflow to ComfyUI

**LoRA Path Format:**
- MinIO: `user-{uuid}/loras/{filename}`
- ComfyUI: `/basedir/models/loras/user-{uuid}/{filename}`
- Workflow: `user-{uuid}/{filename}`

## Configuration

**Environment Variables:**
- `COMFYUI_URL`: ComfyUI API URL (default: `http://comfyui:8188`)
- `COMFYUI_WEB_USER`: ComfyUI auth username (default: `user`)
- `COMFYUI_WEB_PASSWORD`: ComfyUI auth password (default: `password`)

## Dependencies

- `server.projects.auth.dependencies.get_current_user`: User authentication
- `server.projects.auth.services.supabase_service`: Supabase database operations
- `server.projects.auth.services.minio_service`: MinIO file operations
- `server.projects.blob_storage`: General blob storage API (for LoRA uploads)

## Usage Example

```python
# Create workflow
POST /api/v1/comfyui/workflows
{
    "name": "My Workflow",
    "workflow_json": {...},
    "is_public": false
}

# Upload LoRA
POST /api/v1/comfyui/loras
Content-Type: multipart/form-data
file: my-lora.safetensors
name: "My LoRA"

# Execute workflow
POST /api/v1/comfyui/workflows/{workflow_id}/run

# Check status
GET /api/v1/comfyui/runs/{run_id}
```

## Integration

This project integrates with:
- **Blob Storage Project**: Uses MinIO for LoRA file storage
- **Auth Project**: Uses user authentication and Supabase service
- **ComfyUI Service**: Direct API integration for workflow execution
