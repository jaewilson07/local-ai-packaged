"""MongoDB user provisioning service."""

import logging
import secrets
import string

from pymongo import AsyncMongoClient
from pymongo.errors import DuplicateKeyError, OperationFailure

from server.projects.auth.config import AuthConfig
from server.projects.mongo_rag.config import config as rag_config

logger = logging.getLogger(__name__)


class MongoDBService:
    """Service for MongoDB user provisioning and management."""

    def __init__(self, config: AuthConfig):
        """
        Initialize MongoDB service.

        Args:
            config: Auth configuration
        """
        self.config = config
        # Use service account for provisioning operations
        self._admin_client: AsyncMongoClient | None = None
        self._admin_db = None

    async def _get_admin_client(self) -> AsyncMongoClient:
        """Get or create admin MongoDB client for provisioning operations."""
        if self._admin_client is None:
            # Use service account URI from config
            admin_uri = rag_config.mongodb_uri
            self._admin_client = AsyncMongoClient(admin_uri, serverSelectionTimeoutMS=5000)
            self._admin_db = self._admin_client[rag_config.mongodb_database]

            # Verify connection
            await self._admin_client.admin.command("ping")
            logger.info("Created MongoDB admin client for provisioning")

        return self._admin_client

    def _generate_password(self, length: int = 32) -> str:
        """
        Generate a secure random password for MongoDB user.

        Args:
            length: Password length (default: 32)

        Returns:
            Random password string
        """
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

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
            import hashlib

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
        db_name = rag_config.mongodb_database

        # Define privileges for RAG collections
        privileges = [
            {
                "resource": {"db": db_name, "collection": "documents"},
                "actions": ["find", "insert", "update", "remove"],
            },
            {
                "resource": {"db": db_name, "collection": "chunks"},
                "actions": ["find", "insert", "update", "remove"],
            },
            {
                "resource": {"db": db_name, "collection": "memory_messages"},
                "actions": ["find", "insert", "update", "remove"],
            },
            {
                "resource": {"db": db_name, "collection": "memory_facts"},
                "actions": ["find", "insert", "update", "remove"],
            },
            {
                "resource": {"db": db_name, "collection": "memory_web_content"},
                "actions": ["find", "insert", "update", "remove"],
            },
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

    async def provision_user(self, email: str, user_id: str) -> tuple[str, str]:
        """
        Create MongoDB user if it doesn't exist (JIT provisioning).

        Creates user with RBAC role for RAG collections.
        Stores password in Supabase profiles table (caller's responsibility).

        Args:
            email: User email address
            user_id: User UUID (for reference)

        Returns:
            Tuple of (mongodb_username, mongodb_password)

        Raises:
            OperationFailure: If MongoDB operation fails
        """
        # Ensure RAG user role exists
        await self._create_rag_user_role()

        client = await self._get_admin_client()
        username = self._sanitize_username(email)
        password = self._generate_password()
        role_name = "rag_user"

        # Check if user already exists
        if await self.user_exists(email):
            logger.info(f"MongoDB user {username} already exists for {email}")
            # User exists, but we don't have their password stored
            # For now, generate a new one (in production, you'd retrieve from secure storage)
            # TODO: Store/retrieve passwords securely (e.g., in Supabase profiles table)
            return username, password

        try:
            # Create user with role
            await client.admin.command(
                {
                    "createUser": username,
                    "pwd": password,
                    "roles": [{"role": role_name, "db": rag_config.mongodb_database}],
                }
            )

            logger.info(f"Provisioned MongoDB user {username} for {email}")
            return username, password

        except DuplicateKeyError:
            logger.info(f"MongoDB user {username} already exists (duplicate key)")
            return username, password
        except OperationFailure as e:
            if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                logger.info(f"MongoDB user {username} already exists")
                return username, password
            logger.exception(f"Failed to provision MongoDB user {username}: {e}")
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
                logger.exception(f"Failed to delete MongoDB user {username}: {e}")
                raise

    async def close(self) -> None:
        """Close admin client connection."""
        if self._admin_client:
            await self._admin_client.close()
            self._admin_client = None
            self._admin_db = None
            logger.info("Closed MongoDB admin client")
