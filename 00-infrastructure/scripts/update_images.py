#!/usr/bin/env python3
"""
update_images.py

Standalone script to update Docker images without restarting services.
This is useful when you just want to pull the latest images.

Usage:
    python update_images.py [--profile cpu|gpu-nvidia|gpu-amd|none] [--environment private|public] [--skip-dhi-auth]
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import from start_services
# Script is in 00-infrastructure/scripts/, so root is ../../..
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import argparse

from start_services import (
    authenticate_dhi_registry,
    check_and_fix_docker_compose_for_searxng,
    generate_searxng_secret_key,
    pull_docker_images,
)


def main():
    parser = argparse.ArgumentParser(description="Update Docker images to their latest versions.")
    parser.add_argument(
        "--profile",
        choices=["cpu", "gpu-nvidia", "gpu-amd", "none"],
        default="cpu",
        help="Profile to use for Docker Compose (default: cpu)",
    )
    parser.add_argument(
        "--environment",
        choices=["private", "public"],
        default="private",
        help="Environment to use for Docker Compose (default: private)",
    )
    parser.add_argument(
        "--skip-dhi-auth",
        action="store_true",
        help="Skip dhi.io registry authentication",
    )
    args = parser.parse_args()

    print("=== Updating Docker Images ===")
    print(f"Profile: {args.profile}")
    print(f"Environment: {args.environment}")
    print("")

    # Generate SearXNG secret key and check docker-compose.yml
    generate_searxng_secret_key()
    check_and_fix_docker_compose_for_searxng()

    # Authenticate to dhi.io registry before pulling images
    authenticate_dhi_registry(skip_auth=args.skip_dhi_auth)

    # Pull latest Docker images
    try:
        pull_docker_images(args.profile, args.environment)
        print("")
        print("=== Image Update Complete ===")
        print("")
        print("To restart services with the updated images, run:")
        print(
            f"  python start_services.py --profile {args.profile} --environment {args.environment}"
        )
        print("")
        print("Or restart individual stacks:")
        print("  ./start-stack.sh infrastructure")
        print("  ./start-stack.sh data")
        print(f"  ./start-stack.sh compute {args.profile}")
        print("  ./start-stack.sh apps")
    except Exception as e:
        print(f"Error updating images: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
