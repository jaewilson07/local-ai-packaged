"""MinIO user provisioning and file storage service."""

import asyncio
import logging
from uuid import UUID

import boto3
from botocore.exceptions import ClientError
from services.auth.config import AuthConfig

logger = logging.getLogger(__name__)


class MinIOService:
    """Service for MinIO user provisioning and management."""

    def __init__(self, config: AuthConfig):
        """
        Initialize MinIO service.

        Args:
            config: Auth configuration with MinIO settings
        """
        self.config = config
        self._s3_client: boto3.client | None = None

    def _get_s3_client(self):
        """Get or create S3 client for MinIO."""
        if self._s3_client is None:
            # Parse endpoint URL
            endpoint_url = self.config.minio_endpoint

            self._s3_client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=self.config.minio_access_key,
                aws_secret_access_key=self.config.minio_secret_key,
                region_name="us-east-1",  # MinIO doesn't care about region
                use_ssl=False,  # MinIO typically uses HTTP in internal networks
            )
            logger.info(f"Created MinIO S3 client for {endpoint_url}")

        return self._s3_client

    def user_folder_exists(self, user_id: UUID) -> bool:
        """
        Check if user folder/bucket exists in MinIO.

        Args:
            user_id: User UUID

        Returns:
            True if folder exists, False otherwise
        """
        s3_client = self._get_s3_client()
        bucket_name = "user-data"  # Single bucket for all users
        folder_prefix = f"user-{user_id}/"

        try:
            # Try to list objects with the prefix (limit to 1)
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=folder_prefix, MaxKeys=1
            )
            return "Contents" in response and len(response["Contents"]) > 0
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchBucket":
                return False
            raise

    async def provision_user(self, user_id: UUID, email: str) -> None:
        """
        Create user folder structure in MinIO if it doesn't exist (JIT provisioning).

        Note: boto3 is synchronous, but we wrap it in async for consistency.

        Args:
            user_id: User UUID
            email: User email address (for logging)
        """
        import asyncio

        s3_client = self._get_s3_client()
        bucket_name = "user-data"
        folder_prefix = f"user-{user_id}/"

        # Run synchronous boto3 operations in thread pool
        loop = asyncio.get_event_loop()

        try:
            # Check if bucket exists, create if not
            def check_and_create_bucket():
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404" or e.response["Error"]["Code"] == "403":
                        # Bucket doesn't exist, create it
                        s3_client.create_bucket(Bucket=bucket_name)
                        logger.info(f"Created MinIO bucket: {bucket_name}")
                    else:
                        raise

            await loop.run_in_executor(None, check_and_create_bucket)

            # Create a placeholder file to establish the folder
            # MinIO/S3 doesn't have true folders, but prefix-based organization
            placeholder_key = f"{folder_prefix}.keep"

            def create_placeholder():
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=placeholder_key)
                    # Folder already exists
                    logger.debug(f"User folder already exists for {email}")
                except ClientError as e:
                    if e.response["Error"]["Code"] == "404":
                        # Create placeholder file
                        s3_client.put_object(
                            Bucket=bucket_name,
                            Key=placeholder_key,
                            Body=b"",
                            Metadata={"user_email": email, "user_id": str(user_id)},
                        )
                        logger.info(f"Provisioned MinIO folder for user {email} (ID: {user_id})")
                    else:
                        raise

            await loop.run_in_executor(None, create_placeholder)

        except Exception:
            logger.exception("Failed to provision MinIO folder for {email}")
            raise

    def _get_user_prefix(self, user_id: UUID) -> str:
        """Get user folder prefix."""
        return f"user-{user_id}/"

    def _get_bucket_name(self) -> str:
        """Get bucket name for user data."""
        return "user-data"

    async def upload_file(
        self,
        user_id: UUID,
        file_data: bytes,
        object_key: str,
        content_type: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """
        Upload a file to MinIO for a specific user.

        Args:
            user_id: User UUID
            file_data: File content as bytes
            object_key: Object key (filename) within user folder
            content_type: MIME type (optional)
            metadata: Additional metadata (optional)

        Returns:
            Full object key (user-{uuid}/{object_key})

        Raises:
            ClientError: If upload fails
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        full_key = f"{user_prefix}{object_key}"

        # Ensure bucket exists
        loop = asyncio.get_event_loop()

        def upload():
            try:
                # Check if bucket exists
                s3_client.head_bucket(Bucket=bucket_name)
            except ClientError as e:
                if e.response["Error"]["Code"] == "404" or e.response["Error"]["Code"] == "403":
                    s3_client.create_bucket(Bucket=bucket_name)
                    logger.info(f"Created MinIO bucket: {bucket_name}")
                else:
                    raise

            # Prepare extra args
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type
            if metadata:
                extra_args["Metadata"] = metadata

            # Upload file
            s3_client.put_object(Bucket=bucket_name, Key=full_key, Body=file_data, **extra_args)
            logger.info(f"Uploaded file {full_key} for user {user_id}")

        await loop.run_in_executor(None, upload)
        return full_key

    async def download_file(self, user_id: UUID, object_key: str) -> bytes:
        """
        Download a file from MinIO for a specific user.

        Args:
            user_id: User UUID
            object_key: Object key (filename) within user folder

        Returns:
            File content as bytes

        Raises:
            ClientError: If file not found or download fails
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        full_key = f"{user_prefix}{object_key}"

        loop = asyncio.get_event_loop()

        def download():
            response = s3_client.get_object(Bucket=bucket_name, Key=full_key)
            return response["Body"].read()

        file_data = await loop.run_in_executor(None, download)
        logger.debug(f"Downloaded file {full_key} for user {user_id}")
        return file_data

    async def list_files(
        self, user_id: UUID, prefix: str | None = None, max_keys: int = 1000
    ) -> list[dict[str, any]]:
        """
        List files for a specific user.

        Args:
            user_id: User UUID
            prefix: Optional prefix to filter files (within user folder)
            max_keys: Maximum number of keys to return

        Returns:
            List of file metadata dictionaries with keys:
            - key: Full object key
            - filename: Just the filename (without user prefix)
            - size: File size in bytes
            - last_modified: Last modified timestamp
            - content_type: Content type if available
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        search_prefix = f"{user_prefix}{prefix}" if prefix else user_prefix

        loop = asyncio.get_event_loop()

        def list_objects():
            response = s3_client.list_objects_v2(
                Bucket=bucket_name, Prefix=search_prefix, MaxKeys=max_keys
            )

            files = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    # Skip the .keep placeholder file
                    if obj["Key"].endswith("/.keep"):
                        continue

                    # Extract filename (remove user prefix)
                    filename = obj["Key"][len(user_prefix) :]

                    files.append(
                        {
                            "key": obj["Key"],
                            "filename": filename,
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                            "etag": obj["ETag"].strip('"'),
                        }
                    )

            return files

        files = await loop.run_in_executor(None, list_objects)
        logger.debug(f"Listed {len(files)} files for user {user_id} with prefix {prefix}")
        return files

    async def delete_file(self, user_id: UUID, object_key: str) -> bool:
        """
        Delete a file from MinIO for a specific user.

        Args:
            user_id: User UUID
            object_key: Object key (filename) within user folder

        Returns:
            True if deleted, False if not found

        Raises:
            ClientError: If delete fails
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        full_key = f"{user_prefix}{object_key}"

        loop = asyncio.get_event_loop()

        def delete():
            try:
                s3_client.delete_object(Bucket=bucket_name, Key=full_key)
                logger.info(f"Deleted file {full_key} for user {user_id}")
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "NoSuchKey":
                    logger.warning(f"File {full_key} not found for deletion")
                    return False
                raise

        result = await loop.run_in_executor(None, delete)
        return result

    async def get_file_url(
        self, user_id: UUID, object_key: str, expires_in: int = 3600
    ) -> str | None:
        """
        Generate a presigned URL for a file (optional feature).

        Args:
            user_id: User UUID
            object_key: Object key (filename) within user folder
            expires_in: URL expiration time in seconds (default: 1 hour)

        Returns:
            Presigned URL or None if generation fails
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        full_key = f"{user_prefix}{object_key}"

        loop = asyncio.get_event_loop()

        def generate_url():
            try:
                url = s3_client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": bucket_name, "Key": full_key},
                    ExpiresIn=expires_in,
                )
                return url
            except Exception:
                logger.exception("Failed to generate presigned URL for {full_key}")
                return None

        url = await loop.run_in_executor(None, generate_url)
        return url

    async def file_exists(self, user_id: UUID, object_key: str) -> bool:
        """
        Check if a file exists for a specific user.

        Args:
            user_id: User UUID
            object_key: Object key (filename) within user folder

        Returns:
            True if file exists, False otherwise
        """
        s3_client = self._get_s3_client()
        bucket_name = self._get_bucket_name()
        user_prefix = self._get_user_prefix(user_id)
        full_key = f"{user_prefix}{object_key}"

        loop = asyncio.get_event_loop()

        def check_exists():
            try:
                s3_client.head_object(Bucket=bucket_name, Key=full_key)
                return True
            except ClientError as e:
                if e.response["Error"]["Code"] == "404":
                    return False
                raise

        exists = await loop.run_in_executor(None, check_exists)
        return exists
