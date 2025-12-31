#!/bin/bash

# ComfyUI Model Provisioning Script
# Reads models.yml and downloads models to appropriate directories
# This script is idempotent - it skips models that already exist

set -e

MODELS_YAML="/provision/models.yml"
BASE_DIR="/basedir"
MODELS_DIR="${BASE_DIR}/models"

# Model type directories
CHECKPOINTS_DIR="${MODELS_DIR}/checkpoints"
VAE_DIR="${MODELS_DIR}/vae"
LORAS_DIR="${MODELS_DIR}/loras"
UPSCALE_DIR="${MODELS_DIR}/upscale_models"

# Create directories if they don't exist
mkdir -p "${CHECKPOINTS_DIR}" "${VAE_DIR}" "${LORAS_DIR}" "${UPSCALE_DIR}"

# Function to download a file with progress
download() {
    local url="$1"
    local output="$2"
    local description="$3"
    
    if [ -f "${output}" ]; then
        echo "✓ ${description} already exists, skipping..."
        return 0
    fi
    
    echo "Downloading ${description}..."
    wget -q --show-progress -e dotbytes=4M -O "${output}" "${url}" || {
        echo "Error downloading ${description}"
        return 1
    }
    echo "✓ ${description} downloaded successfully"
}

# Function to parse YAML and download models for a category
download_category() {
    local category="$1"
    local target_dir="$2"
    
    # Extract models for this category from YAML
    # Using awk to parse YAML structure
    awk -v category="$category" -v target_dir="$target_dir" '
    BEGIN {
        in_category = 0
        model_name = ""
        model_url = ""
        model_desc = ""
    }
    /^[a-z_]+:/ {
        if ($1 == category":") {
            in_category = 1
        } else if (in_category == 1) {
            # We hit a new category, process what we have and exit
            if (model_name != "" && model_url != "") {
                if (model_desc == "") model_desc = model_name
                system("wget -q --show-progress -e dotbytes=4M -O \"" target_dir "/" model_name "\" \"" model_url "\" 2>&1 || echo \"Error downloading " model_desc "\"")
            }
            exit
        }
    }
    in_category == 1 {
        if ($1 == "-" && $2 == "name:") {
            # Save previous model if we have one
            if (model_name != "" && model_url != "") {
                if (model_desc == "") model_desc = model_name
                cmd = "if [ ! -f \"" target_dir "/" model_name "\" ]; then echo \"Downloading " model_desc "...\"; wget -q --show-progress -e dotbytes=4M -O \"" target_dir "/" model_name "\" \"" model_url "\" && echo \"✓ " model_desc " downloaded successfully\"; else echo \"✓ " model_desc " already exists, skipping...\"; fi"
                system(cmd)
            }
            # Start new model
            model_name = ""
            model_url = ""
            model_desc = ""
            gsub(/^[[:space:]]*-[[:space:]]*name:[[:space:]]*/, "")
            gsub(/^name:[[:space:]]*/, "")
            model_name = $0
            gsub(/^[[:space:]]+/, "", model_name)
        } else if ($1 == "url:") {
            gsub(/^[[:space:]]*url:[[:space:]]*/, "")
            model_url = $0
            gsub(/^[[:space:]]+/, "", model_url)
        } else if ($1 == "description:") {
            gsub(/^[[:space:]]*description:[[:space:]]*/, "")
            model_desc = $0
            gsub(/^[[:space:]]+/, "", model_desc)
        }
    }
    END {
        # Process last model
        if (in_category == 1 && model_name != "" && model_url != "") {
            if (model_desc == "") model_desc = model_name
            cmd = "if [ ! -f \"" target_dir "/" model_name "\" ]; then echo \"Downloading " model_desc "...\"; wget -q --show-progress -e dotbytes=4M -O \"" target_dir "/" model_name "\" \"" model_url "\" && echo \"✓ " model_desc " downloaded successfully\"; else echo \"✓ " model_desc " already exists, skipping...\"; fi"
            system(cmd)
        }
    }
    ' "${MODELS_YAML}"
}

# Check if models.yml exists
if [ ! -f "${MODELS_YAML}" ]; then
    echo "Warning: ${MODELS_YAML} not found. Skipping model provisioning."
    exit 0
fi

echo "=============================================="
echo "  ComfyUI Model Provisioning"
echo "=============================================="
echo ""

# Download models by category
if grep -q "^checkpoints:" "${MODELS_YAML}"; then
    echo "Processing checkpoints..."
    download_category "checkpoints" "${CHECKPOINTS_DIR}"
    echo ""
fi

if grep -q "^vae:" "${MODELS_YAML}"; then
    echo "Processing VAE models..."
    download_category "vae" "${VAE_DIR}"
    echo ""
fi

if grep -q "^loras:" "${MODELS_YAML}"; then
    echo "Processing LoRA models..."
    download_category "loras" "${LORAS_DIR}"
    echo ""
fi

if grep -q "^upscale_models:" "${MODELS_YAML}"; then
    echo "Processing upscale models..."
    download_category "upscale_models" "${UPSCALE_DIR}"
    echo ""
fi

echo "=============================================="
echo "  Model provisioning complete!"
echo "=============================================="

