#!/usr/bin/env python3
"""Download missing models to ComfyUI container."""
import os
import subprocess
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

# Get HF token from environment
HF_TOKEN = os.environ.get("HF_TOKEN", "")


def download_file(url, output_path, description):
    """Download a file with wget."""
    if os.path.exists(output_path):
        print(f"✓ {description} already exists, skipping...")
        return True

    print(f"\nDownloading {description}...")
    print(f"  URL: {url}")
    print(f"  To: {output_path}")

    try:
        cmd = ["wget", "-q", "--show-progress", "-O", output_path, url]

        # Add auth header for HuggingFace if token available
        if HF_TOKEN and "huggingface.co" in url:
            cmd = [
                "wget",
                "-q",
                "--show-progress",
                f"--header=Authorization: Bearer {HF_TOKEN}",
                "-O",
                output_path,
                url,
            ]

        result = subprocess.run(cmd, check=False)

        if result.returncode == 0 and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"✓ Downloaded {description} ({size / 1024 / 1024:.1f} MB)")
            return True
        print(f"✗ Failed to download {description}")
        # Clean up partial download
        if os.path.exists(output_path):
            os.remove(output_path)
        return False

    except Exception as e:
        print(f"✗ Error downloading {description}: {e}")
        return False


def parse_config():
    """Parse models.yml configuration."""
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

    return config


def main():
    # Parse command line for specific model
    specific_model = None
    if len(sys.argv) > 1:
        specific_model = sys.argv[1]
        print(f"Downloading specific model: {specific_model}")

    print("=" * 60)
    print("  ComfyUI Model Download")
    print("=" * 60)

    if not os.path.exists(MODELS_YAML):
        print(f"Error: {MODELS_YAML} not found")
        sys.exit(1)

    config = parse_config()

    # Ensure directories exist
    for dir_path in DIRECTORIES.values():
        os.makedirs(dir_path, exist_ok=True)

    # Download models
    downloaded = 0
    failed = 0
    skipped = 0

    for category, models in config.items():
        target_dir = DIRECTORIES.get(category, "")
        if not models:
            continue

        for model in models:
            name = model.get("name", "")
            url = model.get("url", "")
            description = model.get("description", name)

            if not name or not url:
                continue

            # Filter by specific model if provided
            if specific_model and specific_model not in name:
                continue

            output_path = os.path.join(target_dir, name)

            if os.path.exists(output_path):
                print(f"✓ {name} already exists")
                skipped += 1
                continue

            if download_file(url, output_path, description):
                downloaded += 1
            else:
                failed += 1

    print("\n" + "=" * 60)
    print(f"  Complete: {downloaded} downloaded, {skipped} skipped, {failed} failed")
    print("=" * 60)


if __name__ == "__main__":
    main()
