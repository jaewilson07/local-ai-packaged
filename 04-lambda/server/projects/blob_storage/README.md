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

## Dependencies

- `server.projects.auth.dependencies.get_current_user`: User authentication
- `server.projects.auth.services.minio_service.MinIOService`: MinIO file operations
