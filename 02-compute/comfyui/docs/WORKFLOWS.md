# ComfyUI Workflows Guide

Guide for managing and using workflows in ComfyUI.

## Workflow Location

ComfyUI stores workflows in:
- **Host Path:** `workspace/ComfyUI/user/default/workflows/`
- **Container Path:** `/opt/ComfyUI/user/default/workflows/` (when container is running)

## Adding Workflows

### Option 1: Using the Import Script

```bash
# From project root
python3 setup/add_workflow.py <workflow_file.json>

# Or use the interactive script
./setup/import_workflow.sh
```

### Option 2: Direct Save

```bash
# Save from file
cat workflow.json | python3 setup/save_workflow_direct.py

# Or from stdin
python3 setup/save_workflow_direct.py < workflow.json
```

### Option 3: Manual Copy

1. Copy your workflow JSON
2. Save to: `workspace/ComfyUI/user/default/workflows/<workflow_name>.json`
3. Validate JSON:
   ```bash
   python3 -m json.tool workspace/ComfyUI/user/default/workflows/<workflow_name>.json > /dev/null
   ```

## Available Workflows

### Z-Image-Turbo Workflows

1. **Z-Image-Turbo-BF16-T2I.json** (20KB)
   - Text-to-image workflow for Z-Image-Turbo BF16 model

2. **workflow-z-image-turbo-controlnet-v21-a-game-changing.json** (97KB)
   - ControlNet V2.1 workflow - main comprehensive workflow

3. **workflow-z-image-the-new-king-of-raw-image-editing.json** (9.0KB)
   - Raw image editing workflow

4. **workflow-super-fast-beauty-generator---super-upgraded.json** (25KB)
   - Beauty generator workflow with upgrades

5. **workflow-z-image-non-destructive-staged-magnification.json** (57KB)
   - Non-destructive staged magnification workflow

6. **workflow-red-z-imagedetail-deamon-realistic-text-to-image-generation.json** (17KB)
   - Realistic text-to-image generation workflow

7. **workflow-zimage-contronet-supports-lora-and-seedvr2-high-definition-upscaling.json** (28KB)
   - ControlNet with LoRA and SeedVR2 upscaling workflow

### Other Workflows

- `controlnet_cgpixel.json` - ControlNet pixel art workflow
- `default-z-image.json` - Default Z-Image workflow
- `multi-lora.json` - Multi-LoRA workflow
- And others...

## Using Workflows in ComfyUI

1. **Open ComfyUI Web Interface:**
   - Usually at: `http://localhost:8188` (or your configured port)

2. **Load a Workflow:**
   - Click the "Load" button (or press `Ctrl+O`)
   - Navigate to the workflows list
   - Select the workflow you want to use

3. **Workflow Files:**
   - All workflows are saved as `.json` files
   - They appear in the ComfyUI workflow loader dropdown

## Verification

After adding a workflow:

```bash
# Check file exists
ls -lh workspace/ComfyUI/user/default/workflows/<workflow_name>.json

# Validate JSON
python3 -m json.tool workspace/ComfyUI/user/default/workflows/<workflow_name>.json > /dev/null && echo "✅ Valid JSON"

# In container (if using Docker)
docker exec -it <container_name> ls -lh /opt/ComfyUI/user/default/workflows/<workflow_name>.json
```

## Required Custom Nodes

Most Z-Image-Turbo workflows require these custom nodes:

1. **ComfyUI-Controlnet-Aux** - For preprocessors (Canny, Depth, DensePose)
2. **ComfyUI-Easy-Use** - For style selector and GPU cleanup
3. **rgthree-comfy** - For image comparer and fast groups
4. **ComfyUI-QwenVL** - For Qwen Vision-Language model (auto prompt generation)
5. **ComfyUI-Custom-Scripts** - For ShowText node

See [SETUP.md](SETUP.md) for installation instructions.

## Notes

- Workflows are automatically available in ComfyUI once saved to the workflows directory
- Large workflow JSON files (100KB+) are normal - they contain all node definitions and configurations
- If using Docker, workflows will be available after container restart (if needed)
- Make sure all required models and custom nodes are installed before using a workflow





