#!/usr/bin/env python3
"""Check model status in ComfyUI container."""
import os
import sys

MODELS_YAML = "/basedir/provision/models.yml"
BASE_DIR = "/basedir"
MODELS_DIR = os.path.join(BASE_DIR, "models")

DIRECTORIES = {
    "checkpoints": os.path.join(MODELS_DIR, "checkpoints"),
    "vae": os.path.join(MODELS_DIR, "vae"),
    "loras": os.path.join(MODELS_DIR, "loras"),
    "upscale_models": os.path.join(MODELS_DIR, "upscale_models"),
    "unet": os.path.join(MODELS_DIR, "unet"),
    "clip": os.path.join(MODELS_DIR, "clip"),
}

print("=" * 50)
print("  ComfyUI Model Status Check")
print("=" * 50)

if not os.path.exists(MODELS_YAML):
    print(f"Error: {MODELS_YAML} not found")
    sys.exit(1)

# Simple YAML parser
config = {}
current_category = None
current_model = {}

with open(MODELS_YAML) as f:
    for raw_line in f:
        line = raw_line.rstrip()
        if not line or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())

        if indent == 0 and line.endswith(":"):
            if current_model and current_category:
                config[current_category].append(current_model)
                current_model = {}
            category = line[:-1].strip()
            if category in DIRECTORIES:
                current_category = category
                config[category] = []
            continue

        if indent == 2 and line.strip().startswith("- "):
            if current_model and current_category:
                config[current_category].append(current_model)
            current_model = {}
            remaining = line.strip()[2:].strip()
            if ":" in remaining:
                key, value = remaining.split(":", 1)
                current_model[key.strip()] = value.strip()
            continue

        if indent >= 4 and ":" in line:
            key, value = line.split(":", 1)
            current_model[key.strip()] = value.strip()

    if current_model and current_category:
        config[current_category].append(current_model)

# Show parsed config
total = sum(len(v) for v in config.values())
print(f"\nParsed {total} models from config:")
for cat, models in config.items():
    print(f"  {cat}: {len(models)} models")

# Check what exists
missing = []
existing = []

print("\nModel status:")
for category, models in config.items():
    target_dir = DIRECTORIES.get(category, "")
    if not models:
        continue
    print(f"\n{category.upper()}:")
    for model in models:
        name = model.get("name", "unknown")
        path = os.path.join(target_dir, name)
        exists = os.path.exists(path)
        if exists:
            existing.append(name)
            print(f"  ✓ {name}")
        else:
            missing.append((category, name, model.get("url", "")))
            print(f"  ○ {name} (missing)")

print("\n" + "=" * 50)
print(f"Summary: {len(existing)} existing, {len(missing)} missing")
print("=" * 50)

if missing:
    print("\nMissing models that will be downloaded:")
    for cat, name, url in missing:
        print(f"  [{cat}] {name}")
