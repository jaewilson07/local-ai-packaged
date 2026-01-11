"""Sample script to import a LoRA model from Google Drive.

This script demonstrates how to:
1. Import a LoRA model from Google Drive using the ComfyUI workflow API
2. The file will be downloaded, uploaded to MinIO, and metadata stored in Supabase
"""

import os
import sys
import asyncio
from pathlib import Path

# Add server to path
server_path = Path(__file__).parent.parent.parent / "04-lambda" / "server"
sys.path.insert(0, str(server_path))

from server.projects.google_drive.service import GoogleDriveService
from server.projects.auth.services.minio_service import MinIOService
from server.projects.auth.config import config as auth_config
from server.projects.comfyui_workflow.stores.supabase_store import SupabaseWorkflowStore
from server.projects.auth.services.supabase_service import SupabaseService


async def import_lora_from_google_drive(
    google_drive_file_id: str,
    lora_name: str,
    user_id: str,
    description: str = None,
    tags: list = None
):
    """
    Import a LoRA model from Google Drive.
    
    Args:
        google_drive_file_id: Google Drive file ID
        lora_name: Name for the LoRA model (will be used as filename)
        user_id: User UUID as string
        description: Optional description
        tags: Optional list of tags
    """
    from uuid import UUID
    
    try:
        user_uuid = UUID(user_id)
    except ValueError:
        print(f"Error: Invalid user ID format: {user_id}")
        return None
    
    # Initialize services
    print("Initializing services...")
    
    # Google Drive service
    try:
        google_drive_service = GoogleDriveService()
        print("✓ Google Drive service initialized")
    except Exception as e:
        print(f"✗ Failed to initialize Google Drive service: {e}")
        print("Make sure GDOC_TOKEN is set in .env")
        return None
    
    # MinIO service
    minio_service = MinIOService(auth_config)
    print("✓ MinIO service initialized")
    
    # Supabase service
    supabase_service = SupabaseService(auth_config)
    store = SupabaseWorkflowStore(supabase_service)
    print("✓ Supabase service initialized")
    
    try:
        # Get file metadata from Google Drive
        print(f"\nFetching file metadata from Google Drive (ID: {google_drive_file_id})...")
        file_metadata = google_drive_service.api.get_file_metadata(
            google_drive_file_id,
            fields="id,name,size"
        )
        
        original_filename = file_metadata.get("name", "lora.safetensors")
        file_size = file_metadata.get("size")
        
        print(f"  Original filename: {original_filename}")
        print(f"  File size: {file_size} bytes" if file_size else "  File size: Unknown")
        
        # Ensure filename has .safetensors extension
        if not lora_name.endswith((".safetensors", ".ckpt", ".pt")):
            lora_name = f"{lora_name}.safetensors"
        
        print(f"\nDownloading file from Google Drive...")
        file_data = google_drive_service.download_file(google_drive_file_id)
        print(f"  Downloaded {len(file_data)} bytes")
        
        # Upload to MinIO
        print(f"\nUploading to MinIO as '{lora_name}'...")
        minio_path = await minio_service.upload_file(
            user_id=user_uuid,
            file_data=file_data,
            object_key=f"loras/{lora_name}",
            content_type="application/octet-stream"
        )
        print(f"  ✓ Uploaded to: {minio_path}")
        
        # Create metadata in Supabase
        print(f"\nCreating metadata in Supabase...")
        lora_model = await store.create_lora_model(
            user_id=user_uuid,
            name=lora_name.replace(".safetensors", "").replace(".ckpt", "").replace(".pt", ""),
            filename=lora_name,
            minio_path=minio_path,
            file_size=file_size or len(file_data),
            description=description or f"Imported from Google Drive: {original_filename}",
            tags=tags or []
        )
        
        print(f"  ✓ Created LoRA model with ID: {lora_model.id}")
        print(f"\n✅ Successfully imported LoRA: {lora_name}")
        print(f"   - MinIO path: {minio_path}")
        print(f"   - LoRA ID: {lora_model.id}")
        
        return lora_model
        
    except Exception as e:
        print(f"\n✗ Error importing LoRA: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        await supabase_service.close()


async def main():
    """Main function to import the sample LoRA."""
    # Google Drive file ID from the URL
    google_drive_file_id = "1qfZLsFG_0vpq1qvf_uHhTU8ObQLMy4I7"
    
    # LoRA name
    lora_name = "jw_sample_lora.safetensors"
    
    # Get user ID from env or prompt
    user_id = os.getenv("USER_ID")
    if not user_id:
        print("Error: USER_ID environment variable not set")
        print("Set it with: export USER_ID=your-user-uuid")
        return
    
    print("=" * 60)
    print("Import LoRA from Google Drive")
    print("=" * 60)
    print(f"Google Drive File ID: {google_drive_file_id}")
    print(f"LoRA Name: {lora_name}")
    print(f"User ID: {user_id}")
    print("=" * 60)
    
    result = await import_lora_from_google_drive(
        google_drive_file_id=google_drive_file_id,
        lora_name=lora_name,
        user_id=user_id,
        description="Sample LoRA imported from Google Drive",
        tags=["sample", "imported"]
    )
    
    if result:
        print("\n" + "=" * 60)
        print("Import completed successfully!")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("Import failed!")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
