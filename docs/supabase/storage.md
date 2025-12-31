# Supabase Storage Configuration

Detailed guide for configuring and using Supabase Storage with S3-compatible backend.

## Overview

Supabase Storage in this setup uses **MinIO** as an S3-compatible storage backend. This provides:

- Full S3 API compatibility
- Persistent storage via Docker volumes
- Image transformation capabilities
- Fine-grained access control

## Architecture

```
┌─────────────────┐
│ Storage API     │ ← Supabase Storage Service
│ (storage-api)   │
└────────┬────────┘
         │
         ├──→ S3 Backend (MinIO)
         │    └──→ Persistent Volume
         │
         └──→ Image Proxy (imgproxy)
              └──→ Image transformations
```

## MinIO Service

### Configuration

The MinIO service is defined in `supabase/docker/docker-compose.s3.yml`:

```yaml
supabase-minio:
  container_name: supabase-minio
  image: minio/minio
  ports:
    - 9020:9020  # API
    - 9021:9021  # Console
  environment:
    MINIO_ROOT_USER: ${SUPABASE_MINIO_ROOT_USER:-supa-storage}
    MINIO_ROOT_PASSWORD: ${SUPABASE_MINIO_ROOT_PASSWORD:-secret1234}
  volumes:
    - supabase_minio_data:/data  # Persistent storage
```

### Default Credentials

- **Username**: `supa-storage`
- **Password**: `secret1234`

> ⚠️ **Change these in production!**

### Custom Credentials

Set in `.env`:

```bash
SUPABASE_MINIO_ROOT_USER=your-username
SUPABASE_MINIO_ROOT_PASSWORD=your-secure-password
```

## Storage Service Configuration

### Environment Variables

The storage service is configured with:

```yaml
STORAGE_BACKEND: s3
GLOBAL_S3_BUCKET: stub
GLOBAL_S3_ENDPOINT: http://supabase-minio:9020
GLOBAL_S3_PROTOCOL: http
GLOBAL_S3_FORCE_PATH_STYLE: true
AWS_ACCESS_KEY_ID: ${SUPABASE_MINIO_ROOT_USER:-supa-storage}
AWS_SECRET_ACCESS_KEY: ${SUPABASE_MINIO_ROOT_PASSWORD:-secret1234}
```

### Key Settings

- **STORAGE_BACKEND**: Set to `s3` for MinIO backend
- **GLOBAL_S3_ENDPOINT**: Internal Docker network address
- **GLOBAL_S3_FORCE_PATH_STYLE**: Required for MinIO compatibility
- **FILE_SIZE_LIMIT**: 50MB default (52428800 bytes)

## Accessing Storage

### Via Supabase API

```javascript
// Using Supabase JS client
import { createClient } from '@supabase/supabase-js'

const supabase = createClient(
  'http://localhost:8000',
  'your-anon-key'
)

// Upload file
const { data, error } = await supabase.storage
  .from('bucket-name')
  .upload('path/to/file.jpg', file)

// Download file
const { data, error } = await supabase.storage
  .from('bucket-name')
  .download('path/to/file.jpg')
```

### Direct S3 API Access

You can also use any S3-compatible client:

```python
# Python example with boto3
import boto3

s3 = boto3.client(
    's3',
    endpoint_url='http://localhost:9020',
    aws_access_key_id='supa-storage',
    aws_secret_access_key='secret1234',
    use_ssl=False
)

# Upload file
s3.upload_file('local-file.jpg', 'bucket-name', 'remote-file.jpg')
```

## Bucket Management

### Automatic Bucket Creation

The setup includes a service that creates the default `stub` bucket:

```yaml
supabase-minio-createbucket:
  image: minio/mc
  depends_on:
    supabase-minio:
      condition: service_healthy
  entrypoint: >
    /bin/sh -c "
    /usr/bin/mc alias set supa-minio http://supabase-minio:9020 ...;
    /usr/bin/mc mb supa-minio/stub || true;
    "
```

### Creating Additional Buckets

#### Via MinIO Console

1. Access console: `http://localhost:9021`
2. Login with credentials
3. Navigate to "Buckets"
4. Click "Create Bucket"

#### Via MinIO Client

```bash
mc alias set supabase-minio http://localhost:9020 supa-storage secret1234
mc mb supabase-minio/my-bucket
```

#### Via Supabase API

```javascript
// Create bucket via Supabase Storage API
const { data, error } = await supabase.storage.createBucket('my-bucket', {
  public: false,
  fileSizeLimit: 52428800,
  allowedMimeTypes: ['image/jpeg', 'image/png']
})
```

## Image Transformation

Supabase Storage includes image transformation via **imgproxy**:

### Features

- Resize images
- Format conversion (WebP, etc.)
- Quality optimization
- Watermarking

### Usage

```javascript
// Transform image URL
const imageUrl = supabase.storage
  .from('avatars')
  .getPublicUrl('user-avatar.jpg', {
    transform: {
      width: 200,
      height: 200,
      resize: 'cover',
      format: 'webp'
    }
  })
```

### Configuration

imgproxy is configured in the storage service:

```yaml
ENABLE_IMAGE_TRANSFORMATION: "true"
IMGPROXY_URL: http://imgproxy:5001
```

## Access Control

### Row Level Security (RLS)

Storage uses PostgreSQL RLS policies for access control:

```sql
-- Example: Public read, authenticated write
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
USING (bucket_id = 'public-bucket');

CREATE POLICY "Authenticated write access"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'public-bucket' 
  AND auth.role() = 'authenticated'
);
```

### Bucket Policies

Configure via Supabase Studio or SQL:

```sql
-- Make bucket public
UPDATE storage.buckets
SET public = true
WHERE id = 'my-bucket';

-- Set file size limit
UPDATE storage.buckets
SET file_size_limit = 10485760  -- 10MB
WHERE id = 'my-bucket';
```

## Persistence

### Volume Configuration

Storage is persisted via Docker named volume:

```yaml
volumes:
  supabase_minio_data:
```

### Data Location

- **Docker Volume**: Managed by Docker
- **Volume Name**: `supabase_minio_data`
- **Mount Point**: `/data` in container

### Backup

To backup MinIO data:

```bash
# Backup volume
docker run --rm \
  -v supabase_minio_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar czf /backup/minio-backup.tar.gz /data

# Restore volume
docker run --rm \
  -v supabase_minio_data:/data \
  -v $(pwd)/backup:/backup \
  alpine tar xzf /backup/minio-backup.tar.gz -C /
```

## Monitoring

### Health Checks

MinIO includes health check:

```yaml
healthcheck:
  test: [ "CMD", "curl", "-f", "http://localhost:9020/minio/health/live" ]
  interval: 2s
  timeout: 10s
  retries: 5
```

### Logs

View MinIO logs:

```bash
docker compose logs supabase-minio
docker compose logs supabase-storage
```

### Metrics

Access MinIO metrics (if enabled):

```bash
curl http://localhost:9020/minio/v2/metrics/cluster
```

## Troubleshooting

### Storage Service Not Starting

1. **Check MinIO health**:
   ```bash
   curl http://localhost:9020/minio/health/live
   ```

2. **Verify credentials**:
   ```bash
   docker compose exec supabase-minio env | grep MINIO
   ```

3. **Check storage logs**:
   ```bash
   docker compose logs supabase-storage
   ```

### Upload Failures

1. **File size limit**:
   - Default: 50MB
   - Check `FILE_SIZE_LIMIT` in storage service

2. **Bucket permissions**:
   - Verify bucket exists
   - Check RLS policies
   - Verify bucket is public or user has access

3. **Network issues**:
   - Ensure MinIO is accessible from storage service
   - Check Docker network connectivity

### Image Transformation Not Working

1. **Verify imgproxy**:
   ```bash
   docker compose logs supabase-imgproxy
   curl http://localhost:5001/health
   ```

2. **Check configuration**:
   - `ENABLE_IMAGE_TRANSFORMATION` should be `"true"`
   - `IMGPROXY_URL` should be correct

## Best Practices

1. **Use strong credentials** for MinIO in production
2. **Set appropriate bucket policies** for security
3. **Enable RLS** on storage objects
4. **Monitor storage usage** regularly
5. **Backup volumes** periodically
6. **Use image transformation** to optimize delivery
7. **Set file size limits** per bucket
8. **Use CDN** for production (if available)

## Migration

### From File Backend to S3

If you were using file backend and want to migrate:

1. **Export existing files**:
   ```bash
   docker compose exec supabase-storage \
     tar czf /tmp/storage-backup.tar.gz /var/lib/storage
   ```

2. **Update configuration** to S3 backend

3. **Import files to MinIO**:
   ```bash
   mc cp --recursive /path/to/files supabase-minio/bucket-name/
   ```

## References

- [Supabase Storage Docs](https://supabase.com/docs/guides/storage)
- [MinIO Documentation](https://min.io/docs)
- [S3 API Compatibility](https://docs.aws.amazon.com/AmazonS3/latest/API/Welcome.html)
- [imgproxy Documentation](https://docs.imgproxy.net/)

