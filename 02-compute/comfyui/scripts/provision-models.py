#!/usr/bin/env python3
"""
ComfyUI Model Provisioning Script
Reads models.yml and downloads models to appropriate directories
This script is idempotent - it skips models that already exist
"""

import os
import subprocess
import sys
from pathlib import Path

# Try to import yaml, fall back to simple parsing if not available
try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    print("Warning: PyYAML not available, using simple YAML parsing")

# Default paths (can be overridden with environment variables)
# In Docker: /provision/models.yml and /basedir/models
# Locally: Use MODELS_YAML and COMFYUI_BASE_DIR environment variables
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS_YAML = SCRIPT_DIR / "models.yml"
DEFAULT_BASE_DIR = SCRIPT_DIR.parent / "data" / "basedir"

MODELS_YAML = os.environ.get("MODELS_YAML", str(DEFAULT_MODELS_YAML))
BASE_DIR = os.environ.get("COMFYUI_BASE_DIR", str(DEFAULT_BASE_DIR))

# Check if running in Docker (container paths)
if os.path.exists("/provision/models.yml"):
    MODELS_YAML = "/provision/models.yml"
if os.path.exists("/basedir"):
    BASE_DIR = "/basedir"

MODELS_DIR = os.path.join(BASE_DIR, "models")

# Model type directories
DIRECTORIES = {
    "checkpoints": os.path.join(MODELS_DIR, "checkpoints"),
    "vae": os.path.join(MODELS_DIR, "vae"),
    "loras": os.path.join(MODELS_DIR, "loras"),
    "upscale_models": os.path.join(MODELS_DIR, "upscale_models"),
    "unet": os.path.join(MODELS_DIR, "unet"),
    "clip": os.path.join(MODELS_DIR, "clip"),
    "controlnet": os.path.join(MODELS_DIR, "controlnet"),
    "model_patches": os.path.join(
        MODELS_DIR, "diffusion_models"
    ),  # Model patches go to diffusion_models
}


def parse_simple_yaml(yaml_path):
    """Simple YAML parser for basic structure when PyYAML is not available."""
    config = {}
    current_category = None
    current_model = {}

    yaml_path_obj = Path(yaml_path)
    with yaml_path_obj.open() as f:
        for raw_line in f:
            line = raw_line.rstrip()

            # Skip empty lines and comments
            if not line or line.strip().startswith("#"):
                continue

            # Count leading spaces for indentation
            indent = len(line) - len(line.lstrip())

            # Check for category (no indentation)
            if indent == 0 and line.endswith(":"):
                # Save previous model if we have one
                if current_model and current_category:
                    config[current_category].append(current_model)
                    current_model = {}

                category = line[:-1].strip()
                if category in DIRECTORIES:
                    current_category = category
                    config[category] = []
                continue

            # Check for list item (2 spaces indent)
            if indent == 2 and line.startswith("- "):
                # Save previous model if we have one
                if current_model and current_category:
                    config[current_category].append(current_model)
                current_model = {}
                # The rest of the line might be "name: value" or just the start
                remaining = line[2:].strip()
                if ":" in remaining:
                    key, value = remaining.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    if key in ["name", "url", "description"]:
                        current_model[key] = value
                continue

            # Parse key-value pairs (4+ spaces indent, part of current model)
            if indent >= 4 and ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                if key in ["name", "url", "description"]:
                    current_model[key] = value

        # Add last model
        if current_model and current_category:
            config[current_category].append(current_model)

    return config


def download_file(url, output_path, description):
    """Download a file with progress indication."""
    if os.path.exists(output_path):
        file_size = os.path.getsize(output_path)
        if file_size > 0:
            print(f"✓ {description} already exists ({file_size / (1024**3):.2f} GB), skipping...")
            return True
        print(f"⚠ {description} exists but is empty (0 bytes), re-downloading...")
        os.remove(output_path)

    print(f"Downloading {description}...")
    try:
        # Use wget with progress indication
        subprocess.run(
            ["wget", "-q", "--show-progress", "-e", "dotbytes=4M", "-O", output_path, url],
            check=True,
        )
        print(f"✓ {description} downloaded successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error downloading {description}: {e}")
        return False


def main():
    # Create directories if they don't exist
    for dir_path in DIRECTORIES.values():
        Path(dir_path).mkdir(parents=True, exist_ok=True)

    # Check if models.yml exists
    if not os.path.exists(MODELS_YAML):
        print(f"Warning: {MODELS_YAML} not found. Skipping model provisioning.")
        return 0

    print("=" * 50)
    print("  ComfyUI Model Provisioning")
    print("=" * 50)
    print()

    # Load YAML configuration
    try:
        if HAS_YAML:
            models_yaml_path = Path(MODELS_YAML)
            with models_yaml_path.open() as f:
                config = yaml.safe_load(f)
        else:
            # Simple YAML parsing fallback
            config = parse_simple_yaml(MODELS_YAML)
    except Exception as e:
        print(f"Error reading {MODELS_YAML}: {e}")
        return 1

    if not config:
        print("No models configured in models.yml")
        return 0

    # Process each category
    for category, target_dir in DIRECTORIES.items():
        if category not in config or not config[category]:
            continue

        print(f"Processing {category}...")
        models = config[category]

        # Handle both list format and dict format
        if isinstance(models, list):
            for model in models:
                if isinstance(model, dict):
                    name = model.get("name")
                    url = model.get("url")
                    description = model.get("description", name or "Unknown model")

                    if name and url:
                        output_path = os.path.join(target_dir, name)
                        download_file(url, output_path, description)

        print()

    print("=" * 50)
    print("  Model provisioning complete!")
    print("=" * 50)

    return 0


if __name__ == "__main__":
    sys.exit(main())
