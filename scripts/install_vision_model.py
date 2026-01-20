#!/usr/bin/env python3
"""
Install Vision Model for Image Analysis

Installs llava:7b to Ollama for image-to-text analysis and auto-tagging.

Prerequisites:
- Ollama container running
- Docker network connectivity

Usage:
    python scripts/install_vision_model.py

Environment Variables:
    OLLAMA_BASE_URL - Ollama API URL (default: http://ollama:11434)
"""

import logging
import os
import sys

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
VISION_MODEL = "llava:7b"


def check_ollama_connectivity() -> bool:
    """Check if Ollama is reachable."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to connect to Ollama at {OLLAMA_BASE_URL}: {e}")
        return False


def model_exists(model_name: str) -> bool:
    """Check if a model is already installed."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(model.get("name") == model_name for model in models)
    except Exception as e:
        logger.error(f"Failed to check model existence: {e}")
    return False


def pull_model(model_name: str) -> bool:
    """Pull a model from Ollama."""
    logger.info(f"Pulling model: {model_name}")
    logger.info("This may take several minutes depending on model size...")

    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/pull",
            json={"name": model_name, "stream": True},
            stream=True,
            timeout=1800,  # 30 minute timeout for large models
        )

        if response.status_code != 200:
            logger.error(f"Failed to pull model: HTTP {response.status_code}")
            return False

        # Stream progress updates
        for line in response.iter_lines():
            if line:
                try:
                    import json

                    data = json.loads(line)
                    status = data.get("status", "")
                    if "total" in data and "completed" in data:
                        total = data["total"]
                        completed = data["completed"]
                        percent = (completed / total * 100) if total > 0 else 0
                        print(f"\r{status}: {percent:.1f}%", end="", flush=True)
                    else:
                        print(f"\r{status}", end="", flush=True)
                except:
                    pass

        print()  # Newline after progress
        logger.info(f"✓ Successfully pulled {model_name}")
        return True

    except Exception as e:
        logger.error(f"Failed to pull model: {e}")
        return False


def main():
    logger.info("=" * 60)
    logger.info("Vision Model Installation")
    logger.info("=" * 60)
    logger.info(f"Ollama URL: {OLLAMA_BASE_URL}")
    logger.info(f"Target model: {VISION_MODEL}")
    logger.info("")

    # Check connectivity
    logger.info("Checking Ollama connectivity...")
    if not check_ollama_connectivity():
        logger.error("Cannot connect to Ollama. Please ensure:")
        logger.error("  1. Ollama container is running")
        logger.error("  2. You're running this from within the Docker network")
        logger.error("  3. Or set OLLAMA_BASE_URL to http://localhost:11434")
        sys.exit(1)

    logger.info("✓ Ollama is reachable")

    # Check if model already exists
    logger.info(f"\nChecking if {VISION_MODEL} is installed...")
    if model_exists(VISION_MODEL):
        logger.info(f"✓ {VISION_MODEL} is already installed")
        logger.info("\nNo action needed!")
        sys.exit(0)

    # Pull the model
    logger.info(f"\n{VISION_MODEL} not found. Installing...")
    if pull_model(VISION_MODEL):
        logger.info("\n" + "=" * 60)
        logger.info("✓ Installation complete!")
        logger.info("=" * 60)
        logger.info(f"\n{VISION_MODEL} is ready for use.")
        logger.info("You can now use image analysis features.")
        sys.exit(0)
    else:
        logger.error("\n" + "=" * 60)
        logger.error("✗ Installation failed")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
