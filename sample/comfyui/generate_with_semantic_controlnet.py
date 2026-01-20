#!/usr/bin/env python3
"""
Generate Images with Semantic ControlNet Selection

This script demonstrates:
1. Semantic search for matching ControlNet skeletons
2. Image generation with selected skeleton + character LoRA
3. Side-by-side comparison of results

Usage:
    python sample/comfyui/generate_with_semantic_controlnet.py

Environment Variables:
    CLOUDFLARE_EMAIL - Your Cloudflare Access email (for authentication)
"""

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


def search_skeletons(query: str, preprocessor_type: str | None = None, match_count: int = 5):
    """
    Search for matching ControlNet skeletons

    Args:
        query: Search query (e.g., "woman in car interior")
        preprocessor_type: Filter by preprocessor type
        match_count: Number of results to return

    Returns:
        Search results with similarity scores
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    endpoint = f"{api_base_url}/api/v1/controlnet/skeletons/search"

    logger.info(f"Searching for skeletons: '{query}'")

    payload = {
        "query": query,
        "match_count": match_count,
        "include_private": True,
        "search_type": "hybrid",
    }

    if preprocessor_type:
        payload["preprocessor_type"] = preprocessor_type

    response = requests.post(endpoint, json=payload, headers=headers)

    if response.status_code == 200:
        results = response.json()
        logger.info(f"\n✓ Found {results['total_count']} matching skeletons:")

        for i, result in enumerate(results["results"], 1):
            skeleton = result["skeleton"]
            score = result["similarity_score"]
            logger.info(f"\n  {i}. {skeleton['name']} (similarity: {score:.3f})")
            logger.info(f"     Preprocessor: {skeleton['preprocessor_type']}")
            logger.info(f"     Description: {skeleton.get('description', 'N/A')[:80]}...")
            logger.info(f"     Tags: {', '.join(skeleton.get('tags', []))}")
            if result.get("preview_url"):
                logger.info(f"     Preview: {result['preview_url'][:60]}...")

        return results
    else:
        logger.error(f"✗ Search failed: HTTP {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None


def generate_from_reference(
    image_url: str,
    prompt_description: str,
    character_lora: str,
    use_controlnet: bool = True,
    auto_select_skeleton: bool = True,
    skeleton_search_query: str | None = None,
):
    """
    Generate images from reference with ControlNet guidance

    Args:
        image_url: URL of reference image
        prompt_description: Description for generation
        character_lora: Character LoRA name
        use_controlnet: Whether to use ControlNet
        auto_select_skeleton: Auto-select matching skeleton
        skeleton_search_query: Custom skeleton search query

    Returns:
        Generation job info
    """
    api_base_url = get_api_base_url()
    headers = get_auth_headers()

    endpoint = f"{api_base_url}/api/v1/comfyui/generate-from-reference"

    logger.info(f"\nGenerating image from reference:")
    logger.info(f"  Reference: {image_url[:60]}...")
    logger.info(f"  Description: {prompt_description}")
    logger.info(f"  Character LoRA: {character_lora}")
    logger.info(f"  Use ControlNet: {use_controlnet}")

    params = {
        "image_url": image_url,
        "prompt_description": prompt_description,
        "character_lora": character_lora,
        "use_controlnet": use_controlnet,
        "auto_select_skeleton": auto_select_skeleton,
    }

    if skeleton_search_query:
        params["skeleton_search_query"] = skeleton_search_query

    response = requests.post(endpoint, params=params, headers=headers, timeout=120)

    if response.status_code == 202:
        job = response.json()
        logger.info(f"\n✓ Generation queued!")
        logger.info(f"  Run ID: {job['run_id']}")
        logger.info(f"  Status: {job['status']}")
        logger.info(f"  Stream URL: {job['stream_url']}")

        # Show analysis results
        if "vision_analysis" in job:
            analysis = job["vision_analysis"]
            logger.info(f"\nVision Analysis:")
            logger.info(f"  Description: {analysis['description'][:100]}...")
            logger.info(f"  Tags: {', '.join(analysis.get('tags', []))}")

        if "optimized_prompt" in job:
            logger.info(f"\nOptimized Prompt:")
            logger.info(f"  {job['optimized_prompt'][:150]}...")

        if "selected_skeleton" in job and job["selected_skeleton"]:
            skeleton = job["selected_skeleton"]
            logger.info(f"\nSelected Skeleton:")
            logger.info(f"  Name: {skeleton['name']}")
            logger.info(f"  Preprocessor: {skeleton['preprocessor_type']}")

        return job
    else:
        logger.error(f"✗ Generation failed: HTTP {response.status_code}")
        logger.error(f"Response: {response.text}")
        return None


def main():
    logger.info("=" * 80)
    logger.info("Semantic ControlNet Generation Demo")
    logger.info("=" * 80)

    # Example 1: Search for skeletons with text description
    logger.info("\n" + "=" * 80)
    logger.info("Example 1: Search for Car Interior Skeletons")
    logger.info("=" * 80)

    search_query = "woman in car interior, profile view, selfie"
    search_results = search_skeletons(query=search_query, match_count=3)

    if not search_results or not search_results["results"]:
        logger.warning("\n⚠ No skeletons found. Please create some first using:")
        logger.warning("  python sample/comfyui/create_controlnet_skeleton.py")
        return

    # Example 2: Generate with auto-selected skeleton
    logger.info("\n" + "=" * 80)
    logger.info("Example 2: Generate with Auto-Selected Skeleton")
    logger.info("=" * 80)

    reference_url = "https://www.lemon8-app.com/seo/image?item_id=7221732653144408581&index=2&sign=bf012e6fb6a10849a4b89d1c1d33c7c1"
    prompt = "Alix sends a selfie from inside a car"
    character_lora = "alix"  # Replace with your actual LoRA name

    job = generate_from_reference(
        image_url=reference_url,
        prompt_description=prompt,
        character_lora=character_lora,
        use_controlnet=True,
        auto_select_skeleton=True,
    )

    if job:
        logger.info(f"\n✓ Generation started! Run ID: {job['run_id']}")
        logger.info(f"\nTo monitor progress, use:")
        logger.info(f"  curl {get_api_base_url()}{job['stream_url']}")

    # Example 3: Search for specific type of skeleton
    logger.info("\n" + "=" * 80)
    logger.info("Example 3: Search for OpenPose Skeletons")
    logger.info("=" * 80)

    pose_results = search_skeletons(
        query="standing pose with arms", preprocessor_type="openpose", match_count=3
    )

    # Example 4: Generate with custom skeleton query
    logger.info("\n" + "=" * 80)
    logger.info("Example 4: Generate with Custom Skeleton Query")
    logger.info("=" * 80)

    logger.info("\nYou can customize skeleton search separately from generation:")
    logger.info("  - prompt_description: Context for overall generation")
    logger.info("  - skeleton_search_query: Specific query for finding matching skeleton")

    example_prompt = "Alix waves hello from her VW Rabbit"
    example_skeleton_query = "car interior dashboard view volkswagen"

    logger.info(f"\nExample:")
    logger.info(f"  Prompt: {example_prompt}")
    logger.info(f"  Skeleton Query: {example_skeleton_query}")
    logger.info(f"\nThis would search for car interior skeletons while generating a waving pose.")

    # Uncomment to actually generate:
    # job = generate_from_reference(
    #     image_url=reference_url,
    #     prompt_description=example_prompt,
    #     character_lora=character_lora,
    #     skeleton_search_query=example_skeleton_query,
    # )

    logger.info("\n" + "=" * 80)
    logger.info("✓ Demo complete!")
    logger.info("=" * 80)
    logger.info("\nWorkflow:")
    logger.info("  1. Create skeletons from reference images")
    logger.info("  2. Search semantically for matching skeletons")
    logger.info("  3. Generate with selected skeleton + character LoRA")
    logger.info("  4. As you add more skeletons, results improve!")
    logger.info("\nNext steps:")
    logger.info("  - Build your skeleton library with diverse poses/settings")
    logger.info("  - Experiment with different preprocessor types")
    logger.info("  - Use depth preprocessors for consistent interiors")
    logger.info("  - Use openpose for consistent character poses")


if __name__ == "__main__":
    main()
