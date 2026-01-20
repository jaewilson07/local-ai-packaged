#!/usr/bin/env python3
"""
Create ControlNet Skeleton from Image URL

This script demonstrates how to create a ControlNet skeleton from an image URL.
The skeleton is automatically analyzed with vision model and stored for later reuse.

Usage:
    python sample/comfyui/create_controlnet_skeleton.py

Environment Variables:
    CLOUDFLARE_EMAIL - Your Cloudflare Access email (for authentication)
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import requests
from sample.shared.auth_helpers import get_api_base_url, get_auth_headers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_skeleton(
    image_url: str,
    name: str,
    preprocessor_type: str = "canny",
    description: str | None = None,
    auto_analyze: bool = True,
):
    """
    Create a ControlNet skeleton from an image URL

    Args:
        image_url: URL of the source image
        name: Name for the skeleton
        preprocessor_type: Type of preprocessor (canny, depth, openpose, etc.)
        description: Optional description (auto-generated if None and auto_analyze=True)
        auto_analyze: Whether to analyze image with vision model

    Returns:
        Created skeleton data
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    endpoint = f"{api_base_url}/api/v1/controlnet/skeletons/create-from-url"

    logger.info(f"Creating skeleton '{name}' from: {image_url}")
    logger.info(f"Preprocessor: {preprocessor_type}")
    logger.info(f"Auto-analyze: {auto_analyze}")

    params = {
        "image_url": image_url,
        "name": name,
        "preprocessor_type": preprocessor_type,
        "auto_analyze": auto_analyze,
        "is_public": True,  # Public by default for community sharing
    }

    if description:
        params["description"] = description

    response = requests.post(endpoint, params=params, headers=headers, timeout=120)

    if response.status_code == 201:
        skeleton = response.json()
        logger.info(f"✓ Skeleton created successfully!")
        logger.info(f"  ID: {skeleton['id']}")
        logger.info(f"  Name: {skeleton['name']}")
        logger.info(f"  Description: {skeleton.get('description', 'N/A')}")
        logger.info(f"  Tags: {', '.join(skeleton.get('tags', []))}")
        logger.info(f"  Preprocessor: {skeleton['preprocessor_type']}")
        logger.info(f"  MinIO Path: {skeleton['minio_path']}")

        # Show vision analysis if available
        metadata = skeleton.get("metadata", {})
        vision_data = metadata.get("vision_analysis")
        if vision_data:
            logger.info(f"\nVision Analysis:")
            logger.info(f"  Description: {vision_data.get('description', 'N/A')[:100]}...")
            logger.info(f"  Detected Elements: {', '.join(vision_data.get('detected_elements', []))}")
            logger.info(f"  Suggested Preprocessor: {vision_data.get('suggested_preprocessor', 'N/A')}")

        return skeleton
    else:
        logger.error(f"✗ Failed to create skeleton: HTTP {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None


def analyze_image_preview(image_url: str):
    """
    Preview what the vision model detects before creating skeleton

    Args:
        image_url: URL of the image to analyze

    Returns:
        Vision analysis result
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    endpoint = f"{api_base_url}/api/v1/controlnet/skeletons/analyze-image"

    logger.info(f"Analyzing image: {image_url}")

    params = {
        "image_url": image_url,
        "context": "ControlNet skeleton creation preview",
    }

    response = requests.post(endpoint, params=params, headers=headers, timeout=120)

    if response.status_code == 200:
        analysis = response.json()
        logger.info(f"\n✓ Vision Analysis Result:")
        logger.info(f"  Description: {analysis['description']}")
        logger.info(f"  Prompt: {analysis['prompt'][:100]}...")
        logger.info(f"  Tags: {', '.join(analysis['tags'])}")
        logger.info(f"  Scene Composition: {analysis.get('scene_composition', 'N/A')[:100]}...")
        logger.info(f"  Detected Elements: {', '.join(analysis.get('detected_elements', []))}")
        logger.info(f"  Suggested Preprocessor: {analysis.get('suggested_preprocessor', 'N/A')}")
        return analysis
    else:
        logger.error(f"✗ Failed to analyze image: HTTP {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None


def list_skeletons(preprocessor_type: str | None = None, limit: int = 20):
    """
    List available skeletons

    Args:
        preprocessor_type: Filter by preprocessor type
        limit: Maximum number of results

    Returns:
        List of skeletons
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    endpoint = f"{api_base_url}/api/v1/controlnet/skeletons/"

    params = {
        "include_public": True,
        "limit": limit,
    }

    if preprocessor_type:
        params["preprocessor_type"] = preprocessor_type

    response = requests.get(endpoint, params=params, headers=headers)

    if response.status_code == 200:
        skeletons = response.json()
        logger.info(f"\n✓ Found {len(skeletons)} skeletons:")
        for skeleton in skeletons:
            logger.info(f"  - {skeleton['name']} ({skeleton['preprocessor_type']})")
            logger.info(f"    Tags: {', '.join(skeleton.get('tags', []))}")
            logger.info(f"    Description: {skeleton.get('description', 'N/A')[:60]}...")
        return skeletons
    else:
        logger.error(f"✗ Failed to list skeletons: HTTP {response.status_code}")
        return []


def main():
    logger.info("=" * 80)
    logger.info("ControlNet Skeleton Creation Demo")
    logger.info("=" * 80)

    # Example 1: Preview analysis before creating skeleton
    logger.info("\n" + "=" * 80)
    logger.info("Example 1: Analyze Image (Preview)")
    logger.info("=" * 80)

    example_url = "https://www.lemon8-app.com/seo/image?item_id=7221732653144408581&index=2&sign=bf012e6fb6a10849a4b89d1c1d33c7c1"
    analyze_image_preview(example_url)

    # Example 2: Create skeleton with auto-analysis
    logger.info("\n" + "=" * 80)
    logger.info("Example 2: Create Skeleton with Auto-Analysis")
    logger.info("=" * 80)

    skeleton = create_skeleton(
        image_url=example_url,
        name="Woman in Car Selfie",
        preprocessor_type="canny",  # Edge detection for composition
        auto_analyze=True,
    )

    if skeleton:
        logger.info(f"\nSkeleton ID for future use: {skeleton['id']}")

    # Example 3: Create skeleton for VW Rabbit interior (custom description)
    logger.info("\n" + "=" * 80)
    logger.info("Example 3: Create Custom Skeleton (VW Rabbit Interior)")
    logger.info("=" * 80)

    # Note: Replace with actual VW Rabbit interior photo URL
    rabbit_interior_url = "https://example.com/vw-rabbit-interior.jpg"
    logger.info(f"To create VW Rabbit interior skeleton, use:")
    logger.info(f"  image_url: {rabbit_interior_url}")
    logger.info(f"  name: VW Rabbit Dashboard Interior")
    logger.info(f"  preprocessor_type: depth")
    logger.info(f"  description: Volkswagen Rabbit car interior, dashboard view, steering wheel")

    # Uncomment to actually create:
    # create_skeleton(
    #     image_url=rabbit_interior_url,
    #     name="VW Rabbit Dashboard Interior",
    #     preprocessor_type="depth",  # Depth for 3D interior structure
    #     description="Volkswagen Rabbit car interior, dashboard view, steering wheel, consistent background",
    #     auto_analyze=True,
    # )

    # Example 4: List all created skeletons
    logger.info("\n" + "=" * 80)
    logger.info("Example 4: List All Skeletons")
    logger.info("=" * 80)

    list_skeletons(limit=10)

    logger.info("\n" + "=" * 80)
    logger.info("✓ Demo complete!")
    logger.info("=" * 80)
    logger.info("\nNext steps:")
    logger.info("  1. Create more skeletons from various reference images")
    logger.info("  2. Use semantic search to find matching skeletons")
    logger.info("  3. Generate images with ControlNet guidance")
    logger.info("\nSee: sample/comfyui/generate_with_semantic_controlnet.py")


if __name__ == "__main__":
    main()
