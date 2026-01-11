# Multi-GPU Configuration Guide

Guide for using multiple GPUs with ComfyUI.

## Your Setup

- **GPU 0**: NVIDIA GeForce RTX 3090 (24GB)
- **GPU 1**: NVIDIA GeForce RTX 2080 Ti (11GB)
- **Type**: Local Workers (both GPUs on same machine)

## ComfyUI-Distributed (Recommended)

ComfyUI-Distributed is a custom node extension that enables **true multi-GPU processing** for ComfyUI. Unlike native ComfyUI (which uses one GPU), this extension allows you to leverage **both GPUs simultaneously**.

### What It Does

- ✅ **Parallel Generation**: Generate multiple images/videos simultaneously (one per GPU)
- ✅ **Distributed Upscaling**: Split upscaling tiles across GPUs for faster processing
- ✅ **Auto-Detection**: Automatically detects and configures local GPUs on first launch

### What It Doesn't Do

- ❌ **Combine VRAM**: Doesn't pool VRAM from both GPUs
- ❌ **Speed Up Single Image**: Doesn't make a single image generate faster
- ❌ **Model Parallelism**: Doesn't split a single model across GPUs

## Installation

### Quick Install

```bash
./setup/install_comfyui_distributed.sh
```

### Manual Install

```bash
# Clone into custom_nodes directory
docker exec comfyui-supervisor-1 bash -c "cd /opt/ComfyUI/custom_nodes && git clone https://github.com/robertvoy/ComfyUI-Distributed.git"

# Restart ComfyUI
docker exec comfyui-supervisor-1 supervisorctl restart comfyui
```

## Usage Examples

### Example 1: Parallel Image Generation

**Goal**: Generate 2 images simultaneously (one per GPU)

**Steps**:
1. Open your ComfyUI workflow
2. Add **Distributed Seed** node → connect to your sampler's seed input
3. Add **Distributed Collector** node → connect after VAE Decode
4. In the ComfyUI-Distributed UI panel, enable workers
5. Run the workflow

**Result**: Both GPUs process simultaneously, each generating an image with a different seed.

### Example 2: Distributed Upscaling

**Goal**: Upscale a single image faster by distributing tiles across GPUs

**Steps**:
1. Load your image
2. Upscale with ESRGAN or similar
3. Connect to **Ultimate SD Upscale Distributed** node
4. Configure tile settings
5. Enable workers in UI

**Result**: Tiles are distributed across both GPUs, significantly speeding up upscaling.

### Example 3: Parallel Video Generation

**Goal**: Generate multiple videos simultaneously

**Steps**:
1. Open your workflow
2. Add **Distributed Seed** → connect to sampler seed
3. Add **Distributed Collector** → after VAE Decode
4. Add **Image Batch Divider** → after Distributed Collector
5. Set `divide_by` to 3 (master + 2 workers)
6. Enable workers
7. Run workflow

## Configuration

### For Local Workers (Your Case)

**No configuration needed!** The extension auto-detects your 2 GPUs on first launch.

### For Remote/Cloud Workers

Add `--enable-cors-header` to ComfyUI launch arguments:

```bash
# In docker-compose.yaml, add to COMFYUI_ARGS:
- COMFYUI_ARGS=--enable-cors-header
```

Or via the installation script:
```bash
./setup/install_comfyui_distributed.sh
# Answer 'y' when asked about CORS headers
```

## UI Controls

After installation, you'll see ComfyUI-Distributed controls in the ComfyUI interface:

1. **Worker Management Panel**: Enable/disable workers
2. **Worker Status**: See which GPUs are active
3. **Configuration**: Adjust worker settings

## Performance Expectations

### Parallel Generation
- **2 GPUs = 2x throughput** (generate 2 images in the time of 1)
- Each GPU processes independently
- Different seeds per GPU automatically

### Distributed Upscaling
- **Speed scales with GPU count**
- Tiles intelligently distributed
- Faster GPU handles more tiles (if `static_distribution=false`)

## Alternative: Single GPU Selection

If you want to use a specific GPU instead of multi-GPU:

### Use GPU 1 (RTX 2080 Ti) Instead

**Via Docker Environment Variable:**
```bash
# Add to docker-compose.yaml environment section:
- COMFYUI_ARGS=--cuda-device 1
```

### Use Default Device

```bash
# In docker-compose.yaml:
- COMFYUI_ARGS=--default-device 1
```

This makes GPU 1 the default, but both GPUs remain accessible.

## Verification

### Check GPU Availability

```bash
# Check which GPU ComfyUI is using
docker logs comfyui-supervisor-1 | grep "Device:"

# Check PyTorch GPU visibility
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -c "import torch; print(f'GPUs: {torch.cuda.device_count()}'); [print(f'  {i}: {torch.cuda.get_device_name(i)}') for i in range(torch.cuda.device_count())]"

# Monitor GPU usage
watch -n 1 nvidia-smi
```

### Check Workers Are Detected

```bash
# Check if GPUs are visible
docker exec comfyui-supervisor-1 /opt/environments/python/comfyui/bin/python -c "import torch; print(f'GPUs: {torch.cuda.device_count()}')"

# Check ComfyUI logs
docker logs comfyui-supervisor-1 | grep -i distributed
```

## Troubleshooting

### Workers Not Detected

```bash
# Verify installation
docker exec comfyui-supervisor-1 ls -la /opt/ComfyUI/custom_nodes/ComfyUI-Distributed

# Reinstall if needed
docker exec comfyui-supervisor-1 bash -c "rm -rf /opt/ComfyUI/custom_nodes/ComfyUI-Distributed"
./setup/install_comfyui_distributed.sh
```

### Performance Issues

- Ensure both GPUs are properly exposed: `nvidia-smi` should show both
- Check GPU utilization: `watch -n 1 nvidia-smi`
- Verify workers are enabled in UI

## Best Practices

1. **For Batch Generation**: Use parallel generation (Example 1)
2. **For Upscaling**: Use distributed upscaling (Example 2)
3. **For Single Images**: Stick with single GPU (RTX 3090)
4. **GPU Selection**: RTX 3090 handles larger models better (24GB vs 11GB)

## Current Configuration

Your `docker-compose.yaml` is correctly configured with:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all  # ✅ All GPUs are exposed to container
          capabilities: [gpu]
```

Both GPUs are available to the container, but ComfyUI only uses GPU 0 by default (unless using ComfyUI-Distributed).

## Resources

- **GitHub**: https://github.com/robertvoy/ComfyUI-Distributed
- **Video Tutorials**: Available on the GitHub page
- **Workflow Examples**: Included in the repository

## Summary

ComfyUI-Distributed is the **best solution** for using both GPUs simultaneously. It:
- ✅ Auto-configures local workers
- ✅ Enables parallel generation
- ✅ Accelerates upscaling workflows
- ✅ Works out of the box for your setup

**Install it now**: `./setup/install_comfyui_distributed.sh`
