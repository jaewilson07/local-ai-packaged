"""MongoDB client service."""

import hashlib
import logging

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.security import generate_secure_password

from .config import RAGConfig
from .schemas import MongoCredentials

logger = logging.getLogger(__name__)


class MongoDBClient:
    """Client for MongoDB user provisioning and management."""

    def __init__(self):
        """Initialize MongoDB client."""
        self._admin_client: AsyncMongoClient | None = None
        self._admin_db = None

    async def _get_admin_client(self) -> AsyncMongoClient:
        """Get or create admin MongoDB client for provisioning operations."""
        if self._admin_client is None:
            # Use service account URI from config
            admin_uri = RAGConfig.mongodb_uri
            self._admin_client = AsyncMongoClient(admin_uri, serverSelectionTimeoutMS=5000)
            self._admin_db = self._admin_client[RAGConfig.mongodb_database]

            # Verify connection
            await self._admin_client.admin.command("ping")
            logger.info("Created MongoDB admin client for provisioning")

        return self._admin_client

    def _sanitize_username(self, email: str) -> str:
        """
        Convert email to MongoDB-safe username.

        MongoDB usernames cannot contain '@' or special characters.
        We'll use a hash-based approach or replace '@' with '_'.

        Args:
            email: User email address

        Returns:
            MongoDB-safe username
        """
        # Replace @ with _at_ and remove other special chars
        username = email.replace("@", "_at_").replace(".", "_").lower()
        # MongoDB username max length is 64 chars
        if len(username) > 64:
            # Use first 32 chars + hash of full email
            email_hash = hashlib.sha256(email.encode()).hexdigest()[:16]
            username = username[:32] + "_" + email_hash
        return username

    async def user_exists(self, email: str) -> bool:
        """
        Check if MongoDB user exists.

        Args:
            email: User email address

        Returns:
            True if user exists, False otherwise
        """
        try:
            client = await self._get_admin_client()
            username = self._sanitize_username(email)

            # Check if user exists in admin database
            users = await client.admin.command("usersInfo", username)
            return len(users.get("users", [])) > 0
        except OperationFailure as e:
            if "UserNotFound" in str(e) or "not found" in str(e).lower():
                return False
            raise

    async def _create_rag_user_role(self) -> None:
        """
        Create MongoDB RBAC role for RAG users if it doesn't exist.

        Role grants read/write access to RAG collections.
        """
        client = await self._get_admin_client()

        role_name = "rag_user"
        db_name = RAGConfig.mongodb_database

        # Define privileges for RAG collections
        privileges = [
            {
                "resource": {"db": db_name, "collection": col},
                "actions": ["find", "insert", "update", "remove"],
            }
            for col in [
                RAGConfig.mongodb_collection_documents,
                RAGConfig.mongodb_collection_chunks,
                "memory_messages",
                "memory_facts",
                "memory_web_content",
            ]
        ]

        try:
            # Try to create role (will fail if exists, which is fine)
            await client.admin.command(
                {"createRole": role_name, "privileges": privileges, "roles": []}
            )
            logger.info(f"Created MongoDB role: {role_name}")
        except OperationFailure as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.debug(f"MongoDB role {role_name} already exists")
            else:
                logger.warning(f"Failed to create MongoDB role {role_name}: {e}")
                raise

    async def provision_user(self, email: str, user_id: str) -> MongoCredentials:
        """
        Create MongoDB user if it doesn't exist (JIT provisioning).

        Args:
            email: User email address
            user_id: User UUID (for reference)

        Returns:
            MongoCredentials object containing username and password
        """
        # Ensure RAG user role exists
        await self._create_rag_user_role()

        client = await self._get_admin_client()
        username = self._sanitize_username(email)
        password = generate_secure_password(include_special=True)
        role_name = "rag_user"

        # Check if user already exists
        if await self.user_exists(email):
            logger.info(f"MongoDB user {username} already exists for {email}")
            return MongoCredentials(username=username, password=password)

        try:
            # Create user with role
            await client.admin.command(
                {
                    "createUser": username,
                    "pwd": password,
                    "roles": [{"role": role_name, "db": RAGConfig.mongodb_database}],
                }
            )

            logger.info(f"Provisioned MongoDB user {username} for {email}")
            return MongoCredentials(username=username, password=password)

        except DuplicateKeyError:
            logger.info(f"MongoDB user {username} already exists (duplicate key)")
            return MongoCredentials(username=username, password=password)
        except OperationFailure as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info(f"MongoDB user {username} already exists")
                return MongoCredentials(username=username, password=password)
            logger.exception(f"Failed to provision MongoDB user {username}")
            raise

    async def get_mongodb_username(self, email: str) -> str:
        """
        Get MongoDB username for an email address.

        Args:
            email: User email address

        Returns:
            MongoDB username
        """
        return self._sanitize_username(email)

    async def delete_user(self, email: str) -> None:
        """
        Delete MongoDB user.

        Args:
            email: User email address
        """
        try:
            client = await self._get_admin_client()
            username = self._sanitize_username(email)

            await client.admin.command("dropUser", username)
            logger.info(f"Deleted MongoDB user {username} for {email}")
        except OperationFailure as e:
            if "UserNotFound" in str(e) or "not found" in str(e).lower():
                logger.info(f"MongoDB user {username} not found, skipping deletion")
            else:
                logger.exception(f"Failed to delete MongoDB user {username}")
                raise

    async def close(self) -> None:
        """Close admin client connection."""
        if self._admin_client:
            await self._admin_client.close()
            self._admin_client = None
            self._admin_db = None
            logger.info("Closed MongoDB admin client")

    async def ping(self) -> bool:
        """
        Check connectivity to MongoDB.

        Returns:
            True if connected, raises Exception otherwise
        """
        client = await self._get_admin_client()
        await client.admin.command("ping")
        return True
