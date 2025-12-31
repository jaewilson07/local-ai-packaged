# ComfyUI Model Configuration

This guide explains how to configure and provision models for ComfyUI automatically.

## Overview

ComfyUI uses an automated model provisioning system that downloads models on first startup based on a configuration file. This ensures that all required models are available without manual intervention.

**How it works:**
1. Models are defined in `comfyui/models.yml`
2. On container startup, a provisioning container runs `provision-models.py` (or `provision-models.sh` as fallback)
3. The script reads `models.yml` and downloads models to the appropriate directories
4. The script is **idempotent** - it skips models that already exist

## Model Categories

ComfyUI organizes models into different categories, each with its own directory:

- **checkpoints** - Main Stable Diffusion model files (`.ckpt`, `.safetensors`)
- **vae** - Variational Autoencoder models for better image quality
- **loras** - LoRA (Low-Rank Adaptation) models for fine-tuning
- **upscale_models** - Models for upscaling images

## Configuration File: `models.yml`

The `comfyui/models.yml` file defines which models to download. It uses a simple YAML format:

```yaml
checkpoints:
  - name: model-name.ckpt
    url: https://example.com/path/to/model.ckpt
    description: Human-readable description

vae:
  - name: vae-model.safetensors
    url: https://example.com/path/to/vae.safetensors
    description: VAE description

loras:
  - name: lora-model.safetensors
    url: https://example.com/path/to/lora.safetensors
    description: LoRA description

upscale_models:
  - name: upscaler.pth
    url: https://example.com/path/to/upscaler.pth
    description: Upscaler description
```

### Example Configuration

See `comfyui/models.yml` for a complete example with popular models:

- **Stable Diffusion 1.5** - Classic SD model
- **Stable Diffusion 2.1** - Improved SD model
- **Stable Diffusion XL** - Base and refiner models
- **VAE models** - For enhanced image quality

## Adding New Models

### Step 1: Find the Model URL

1. Visit [Hugging Face](https://huggingface.co/models) or the model's official repository
2. Navigate to the model page
3. Find the direct download URL for the model file
   - On Hugging Face: Click on a file → "View raw" or copy the download URL
   - Look for URLs ending in `.ckpt`, `.safetensors`, `.pth`, etc.

### Step 2: Add to `models.yml`

Edit `comfyui/models.yml` and add your model to the appropriate category:

```yaml
checkpoints:
  - name: my-custom-model.safetensors
    url: https://huggingface.co/user/model/resolve/main/my-custom-model.safetensors
    description: My custom Stable Diffusion model
```

**Important:**
- Use the exact filename you want in the `name` field
- Use a direct download URL (not a page URL)
- Ensure the URL is accessible without authentication (or configure authentication separately)

### Step 3: Restart ComfyUI

The provisioning script runs automatically on container startup. To trigger it:

```bash
# Restart the provisioning container
docker compose restart comfyui-provision-cpu
# Or for GPU:
docker compose restart comfyui-provision-gpu
```

Or restart the entire stack:

```bash
python start_services.py --profile cpu
```

## Provisioning Scripts

The system includes two provisioning scripts:

### `provision-models.py` (Primary)

**Location:** `comfyui/provision-models.py`

**Features:**
- Python-based, more robust YAML parsing
- Uses PyYAML if available, falls back to simple parsing
- Better error handling
- Progress indication during downloads

**How it works:**
1. Reads `/provision/models.yml` (mounted from `./comfyui/models.yml`)
2. Creates model directories if they don't exist
3. For each model in the config:
   - Checks if the file already exists
   - If not, downloads using `wget` with progress
   - Saves to the appropriate directory under `/basedir/models/`

### `provision-models.sh` (Fallback)

**Location:** `comfyui/provision-models.sh`

**Features:**
- Bash script, no Python dependencies
- Uses `awk` for YAML parsing
- Simpler but less robust

**When it's used:**
- If `provision-models.py` is not found
- If Python is not available in the container

## Docker Integration

The provisioning system is integrated into Docker Compose:

### Provisioning Container

A separate init container (`comfyui-provision-*`) runs the provisioning script:

```yaml
comfyui-provision-cpu:
  profiles: ["cpu"]
  <<: *init-comfyui
  depends_on:
    - comfyui-cpu
```

**Key points:**
- Runs after the main ComfyUI container starts
- Mounts `./comfyui` directory as `/provision` (read-only)
- Executes the provisioning script automatically
- Exits after completion

### Volume Mounts

Models are stored in Docker volumes:

- `comfyui_basedir:/basedir` - Contains all ComfyUI data including models
- `comfyui_run:/comfy/mnt` - Runtime data

Models are downloaded to `/basedir/models/{category}/` inside the container.

## Manual Model Management

### Downloading Models Manually

If you prefer to download models manually:

1. **Find the model file location:**
   ```bash
   docker exec comfyui ls -la /basedir/models/checkpoints/
   ```

2. **Download directly into the container:**
   ```bash
   docker exec -it comfyui wget -O /basedir/models/checkpoints/my-model.ckpt \
     https://example.com/path/to/model.ckpt
   ```

3. **Or copy from host:**
   ```bash
   docker cp my-model.ckpt comfyui:/basedir/models/checkpoints/
   ```

### Removing Models

To remove a model:

```bash
docker exec comfyui rm /basedir/models/checkpoints/model-name.ckpt
```

Or remove it from `models.yml` and it won't be re-downloaded.

## Troubleshooting

### Models Not Downloading

**Check provisioning logs:**
```bash
docker logs comfyui-provision-cpu
# Or for GPU:
docker logs comfyui-provision-gpu
```

**Common issues:**
- Invalid URL (check the URL is accessible)
- Network issues (check container can reach internet)
- Disk space (check available space in volume)
- YAML syntax errors (validate `models.yml` format)

### YAML Parsing Errors

If you see YAML parsing errors:

1. **Validate YAML syntax:**
   - Use an online YAML validator
   - Check indentation (use 2 spaces, not tabs)
   - Ensure proper list format with `-`

2. **Test the script manually:**
   ```bash
   docker exec -it comfyui-provision-cpu python3 /provision/provision-models.py
   ```

### Models Not Appearing in ComfyUI

**Check model directory:**
```bash
docker exec comfyui ls -la /basedir/models/checkpoints/
```

**Verify ComfyUI can access models:**
- Check ComfyUI logs: `docker logs comfyui`
- Ensure models are in the correct directory
- Check file permissions (should be readable)

**Refresh ComfyUI:**
- Restart ComfyUI: `docker compose restart comfyui`
- Hard refresh browser (Ctrl+F5)

### Provisioning Script Not Running

**Check if provisioning container ran:**
```bash
docker ps -a | grep comfyui-provision
```

**Manually trigger provisioning:**
```bash
docker compose up comfyui-provision-cpu
```

## Best Practices

### Model Organization

1. **Use descriptive names** - Include model version or variant in filename
2. **Group related models** - Keep models from the same family together
3. **Document models** - Use the `description` field to note model purpose

### Performance

1. **Start with essential models** - Don't download everything at once
2. **Use safetensors format** - More secure than `.ckpt` files
3. **Monitor disk space** - Models can be large (several GB each)

### Security

1. **Verify model sources** - Only download from trusted repositories
2. **Check file integrity** - Some models provide checksums
3. **Keep models.yml in version control** - But don't commit actual model files

## Model Sources

Popular sources for ComfyUI models:

- **[Hugging Face](https://huggingface.co/models)** - Largest collection of models
- **[Civitai](https://civitai.com/)** - Community models and LoRAs
- **[Stability AI](https://stability.ai/)** - Official Stable Diffusion models

### Getting Hugging Face URLs

1. Navigate to the model page on Hugging Face
2. Click on the file you want
3. Click "View raw" or copy the download URL
4. Use the URL format: `https://huggingface.co/{user}/{model}/resolve/main/{filename}`

## Advanced Configuration

### Custom Model Directories

The provisioning script supports these categories:
- `checkpoints` → `/basedir/models/checkpoints/`
- `vae` → `/basedir/models/vae/`
- `loras` → `/basedir/models/loras/`
- `upscale_models` → `/basedir/models/upscale_models/`

To add support for other categories, modify `provision-models.py`:

```python
DIRECTORIES = {
    "checkpoints": os.path.join(MODELS_DIR, "checkpoints"),
    "vae": os.path.join(MODELS_DIR, "vae"),
    "loras": os.path.join(MODELS_DIR, "loras"),
    "upscale_models": os.path.join(MODELS_DIR, "upscale_models"),
    "controlnet": os.path.join(MODELS_DIR, "controlnet"),  # Add new category
}
```

### Authentication for Private Models

If you need to download private models:

1. **Set up authentication in the container:**
   ```bash
   docker exec -it comfyui-provision-cpu bash
   # Configure authentication (Hugging Face token, etc.)
   ```

2. **Or modify the provisioning script** to include authentication headers

## Related Files

- `comfyui/models.yml` - Model configuration file
- `comfyui/provision-models.py` - Python provisioning script
- `comfyui/provision-models.sh` - Bash provisioning script (fallback)
- `docker-compose.yml` - Docker Compose configuration

## References

- [ComfyUI Documentation](https://github.com/comfyanonymous/ComfyUI)
- [Stable Diffusion Models](https://huggingface.co/models?library=diffusers)
- [YAML Syntax Guide](https://yaml.org/spec/1.2.2/)

