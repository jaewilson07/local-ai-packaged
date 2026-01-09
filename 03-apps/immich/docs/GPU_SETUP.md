# Immich GPU Acceleration Setup

This guide covers GPU acceleration configuration for Immich video transcoding.

## Overview

Immich uses GPU acceleration for video transcoding in the `immich-microservices` service. This significantly improves transcoding performance compared to CPU-only processing.

## Supported GPU Types

### NVIDIA GPU (Recommended)

NVIDIA GPUs are supported via the NVIDIA Container Runtime. This is the recommended setup for video transcoding.

**Requirements:**
- NVIDIA GPU with CUDA support
- NVIDIA drivers installed on host
- Docker NVIDIA runtime configured

**Configuration:**
- Service: `immich-microservices-gpu`
- Profile: `gpu-nvidia`
- Uses `deploy.resources.reservations.devices` with NVIDIA driver

### Intel QuickSync

Intel QuickSync (integrated graphics) can be used for hardware-accelerated transcoding.

**Requirements:**
- Intel CPU with integrated graphics
- `/dev/dri` device available on host

**Configuration:**
- Map `/dev/dri` device to container
- Note: Not currently configured in this setup, but can be added if needed

### AMD GPU

AMD GPUs can be used with ROCm support.

**Requirements:**
- AMD GPU with ROCm support
- `/dev/kfd` and `/dev/dri` devices available

**Configuration:**
- Map `/dev/kfd` and `/dev/dri` devices
- Note: Not currently configured in this setup, but can be added if needed

## Current Setup

The current configuration supports **NVIDIA GPU** acceleration:

```yaml
immich-microservices-gpu:
  profiles: ["gpu-nvidia"]
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: all
            capabilities: [gpu]
```

## Starting with GPU

To start Immich with GPU acceleration:

```bash
python start_services.py --profile gpu-nvidia --stack apps
```

This will:
1. Start `immich-microservices-gpu` (with GPU access)
2. Start other Immich services (server, machine-learning, postgres, typesense)

## Verifying GPU Access

### Check GPU in Container

```bash
docker exec immich-microservices-gpu nvidia-smi
```

Expected output shows GPU information and processes.

### Check Transcoding Performance

1. Upload a video file via the Immich web interface
2. Monitor transcoding progress in the web UI
3. Check logs for GPU usage indicators:

```bash
docker compose -p localai-apps logs -f immich-microservices-gpu | grep -i gpu
```

## CPU-Only Mode

If GPU is not available or not needed, use CPU-only mode:

```bash
python start_services.py --profile cpu --stack apps
```

This starts `immich-microservices-cpu` which uses CPU for transcoding (slower but works on any system).

## Troubleshooting

### GPU Not Detected

1. **Verify NVIDIA drivers:**
   ```bash
   nvidia-smi
   ```

2. **Check Docker NVIDIA runtime:**
   ```bash
   docker info | grep -i nvidia
   ```

3. **Verify GPU access in container:**
   ```bash
   docker exec immich-microservices-gpu nvidia-smi
   ```

### Transcoding Still Using CPU

1. Ensure GPU profile is used: `--profile gpu-nvidia`
2. Check that `immich-microservices-gpu` is running (not `immich-microservices-cpu`)
3. Verify GPU is accessible in container
4. Check Immich logs for transcoding method

### Performance Issues

1. **GPU Memory:**
   - Large videos may require significant GPU memory
   - Monitor GPU memory usage: `nvidia-smi`

2. **Concurrent Transcoding:**
   - Multiple videos transcoding simultaneously may impact performance
   - Consider limiting concurrent jobs in Immich settings

3. **Storage I/O:**
   - Ensure storage (library directory) is on fast storage (SSD recommended)
   - Network storage may bottleneck transcoding

## Configuration Options

### Limiting GPU Usage

If you need to limit GPU usage, you can modify the docker-compose configuration to use specific GPUs:

```yaml
devices:
  - driver: nvidia
    device_ids: ['0']  # Use only first GPU
    capabilities: [gpu]
```

### Environment Variables

Immich automatically detects and uses GPU when available. No special environment variables are required for basic GPU usage.

## References

- [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)
- [Immich GPU Documentation](https://docs.immich.app/administration/hardware-transcoding)
