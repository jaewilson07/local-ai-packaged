# Blob Storage Project

General-purpose blob storage API for user file management using MinIO.

## Overview

This project provides REST API endpoints for users to upload, download, list, and delete files stored in MinIO. Files are organized by user ID in the format `user-{uuid}/{filename}`.

## Features

- **File Upload**: Upload files to user's personal storage
- **File Download**: Download files from user's storage
- **File Listing**: List all files for a user (with optional prefix filtering)
- **File Deletion**: Delete files from user's storage
- **Presigned URLs**: Generate temporary URLs for file access
- **User Isolation**: Each user can only access their own files

## API Endpoints

### Upload File
```
POST /api/v1/storage/upload
Content-Type: multipart/form-data

Body: file (multipart file)
```

### List Files
```
GET /api/v1/storage/list?prefix=loras/
```

### Download File
```
GET /api/v1/storage/download/{filename}
```

### Delete File
```
DELETE /api/v1/storage/delete/{filename}
```

### Get Presigned URL
```
GET /api/v1/storage/url/{filename}?expires_in=3600
```

## Authentication

All endpoints require authentication via Cloudflare Access JWT token (handled by `get_current_user` dependency).

## Storage Structure

Files are stored in MinIO under:
```
user-data/
  └── user-{uuid}/
      ├── .keep (placeholder)
      ├── filename1.jpg
      ├── filename2.pdf
      └── loras/
          └── my-lora.safetensors
```

## Integration

This project is used by:
- **ComfyUI Workflow Management**: Stores user LoRA models
- **Future projects**: Any project needing user file storage

## Architecture

This project follows the Service vs Capability Architecture pattern:

- **`config.py`**: Project-specific configuration
- **`dependencies.py`**: `BlobStorageDeps` class inheriting from `BaseDependencies`
- **`tools.py`**: Core capability functions (upload, download, list, delete, get URL)
- **`agent.py`**: `blob_storage_agent` with agent tools for file management
- **`models.py`**: Pydantic models for request/response validation
- **`router.py`**: REST endpoints using tools pattern
- **`api/blob_storage.py`**: Endpoint functions for MCP tools
- **MCP Tools**: Exposed via `fastmcp_server.py` for inter-agent communication

## Agent Tools

The `blob_storage_agent` provides the following tools:

- `upload_file`: Upload a file to user's blob storage
- `list_files`: List files for a user
- `download_file`: Download a file from user's storage
- `delete_file`: Delete a file from user's storage
- `get_file_url`: Generate a presigned URL for a file

## MCP Tools

The following MCP tools are available:

- `upload_file_to_storage`: Upload a file to user's blob storage
- `list_storage_files`: List files for a user
- `download_file_from_storage`: Download a file from user's storage
- `delete_file_from_storage`: Delete a file from user's storage
- `get_storage_file_url`: Generate a presigned URL for a file

## Usage Examples

### Using Tools Directly

```python
from server.projects.blob_storage.dependencies import BlobStorageDeps
from server.projects.blob_storage.tools import upload_file_tool
from server.projects.shared.context_helpers import create_run_context
from uuid import UUID

deps = BlobStorageDeps.from_settings()
await deps.initialize()

try:
    ctx = create_run_context(deps)
    result = await upload_file_tool(
        ctx=ctx,
        user_id=UUID("..."),
        file_data=b"...",
        filename="example.jpg",
        content_type="image/jpeg"
    )
finally:
    await deps.cleanup()
```

### Using the Agent

```python
from server.projects.blob_storage.agent import blob_storage_agent
from server.projects.blob_storage.dependencies import BlobStorageDeps

deps = BlobStorageDeps.from_settings()
await deps.initialize()

try:
    result = await blob_storage_agent.run(
        "Upload this file: example.jpg",
        deps=deps
    )
finally:
    await deps.cleanup()
```

## Dependencies

- `server.projects.auth.dependencies.get_current_user`: User authentication
- `server.projects.auth.services.minio_service.MinIOService`: MinIO file operations
- `server.projects.shared.dependencies.BaseDependencies`: Base dependencies class
