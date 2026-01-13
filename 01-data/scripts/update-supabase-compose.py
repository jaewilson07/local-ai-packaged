#!/usr/bin/env python3
"""
update-supabase-compose.py

This script helps update the Supabase compose file from upstream while preserving customizations.
It copies from supabase/docker/docker-compose.yml and supabase/docker/docker-compose.s3.yml
to 01-data/supabase/docker-compose.yml, preserving network configuration and volume path adjustments.
"""

import os
import sys
from pathlib import Path


def update_supabase_compose():
    """Update 01-data/supabase/docker-compose.yml from upstream Supabase files."""

    source_main = "01-data/supabase/upstream/docker/docker-compose.yml"
    source_s3 = "01-data/supabase/upstream/docker/docker-compose.s3.yml"
    target = "01-data/supabase/docker-compose.yml"

    if not os.path.exists(source_main):
        print(f"Error: Source file not found: {source_main}")
        print(
            "Please ensure Supabase repository is cloned in the 01-data/supabase/upstream/ directory."
        )
        sys.exit(1)

    if not os.path.exists(source_s3):
        print(f"Warning: S3 compose file not found: {source_s3}")
        print("Continuing without S3 configuration...")

    print(f"Copying {source_main} to {target}...")

    # Read the source file
    source_main_path = Path(source_main)
    with source_main_path.open(encoding="utf-8") as f:
        content = f.read()

    # Remove the name field if present
    content = content.replace("name: supabase\n", "")
    content = content.replace("name: supabase", "")

    # Add network configuration at the top (after comments)
    network_config = """
networks:
  default:
    external: true
    name: ai-network

volumes:
  db-config:
  supabase_minio_data:

"""

    # Find where services: starts and insert network config before it
    if "services:" in content:
        # Insert network config before services
        services_index = content.find("services:")
        # Find the last newline before services
        insert_index = content.rfind("\n", 0, services_index) + 1
        content = content[:insert_index] + network_config + content[insert_index:]

    # Update volume paths to be relative to 01-data/supabase/
    # Replace ./volumes/ with ../../upstream/docker/volumes/
    content = content.replace("./volumes/", "../../upstream/docker/volumes/")

    # If S3 file exists, merge its storage configuration
    if os.path.exists(source_s3):
        print(f"Merging S3 configuration from {source_s3}...")
        source_s3_path = Path(source_s3)
        with source_s3_path.open(encoding="utf-8") as f:
            s3_content = f.read()

        # Extract supabase-minio and supabase-minio-createbucket services
        if "supabase-minio:" in s3_content:
            # Find the storage service in the main content and replace it with S3 version
            # This is a simplified merge - in practice, you might want more sophisticated merging
            print("Note: S3 storage configuration detected. Updating storage service...")
            # The storage service replacement is already handled in the compose file
            # We just need to ensure supabase-minio services are included

        # Add supabase-minio services before storage service
        if "  storage:" in content and "  supabase-minio:" not in content:
            # Extract minio services from S3 file
            minio_start = s3_content.find("  supabase-minio:")
            if minio_start != -1:
                # Find where storage service starts in main content
                storage_start = content.find("  storage:")
                # Find the line before storage
                insert_point = content.rfind("\n", 0, storage_start) + 1
                # Extract minio services (up to storage service in S3 file)
                minio_end = s3_content.find("  storage:", minio_start)
                if minio_end == -1:
                    minio_end = len(s3_content)
                minio_services = s3_content[minio_start:minio_end]
                # Insert before storage
                content = content[:insert_point] + minio_services + "\n" + content[insert_point:]

    # Update storage service to use S3 backend (if S3 file was merged)
    if "supabase-minio:" in content and "STORAGE_BACKEND: file" in content:
        # Replace file backend with S3 backend
        content = content.replace("STORAGE_BACKEND: file", "STORAGE_BACKEND: s3")
        # Update storage depends_on to include supabase-minio
        if "      imgproxy:" in content and "      supabase-minio:" not in content:
            # Find depends_on section of storage
            storage_depends_on = content.find("    depends_on:", content.find("  storage:"))
            if storage_depends_on != -1:
                # Find the end of depends_on section
                depends_end = content.find("\n    ", storage_depends_on + 20)
                if depends_end == -1:
                    depends_end = content.find("\n    environment:", storage_depends_on)
                if depends_end != -1:
                    # Insert supabase-minio dependency
                    insert_text = "      supabase-minio:\n        condition: service_healthy\n"
                    content = content[:depends_end] + insert_text + content[depends_end:]

    # Write the updated content
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with target_path.open("w", encoding="utf-8") as f:
        f.write(content)

    print(f"Successfully updated {target}")
    print("\nNote: Please review the file and ensure:")
    print("  1. Network configuration is correct (external: ai-network)")
    print("  2. Volume paths are relative to 01-data/supabase/")
    print("  3. All services are properly configured")
    print("  4. S3 storage configuration is merged if needed")


if __name__ == "__main__":
    update_supabase_compose()
