"""Supabase user provisioning service."""

import logging
from typing import Optional
from uuid import uuid4
import asyncpg
from datetime import datetime

from server.projects.auth.config import AuthConfig
from server.projects.auth.models import User

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for Supabase user provisioning and management."""
    
    def __init__(self, config: AuthConfig):
        """
        Initialize Supabase service.
        
        Args:
            config: Auth configuration with Supabase settings
        """
        self.config = config
        self.db_url = config.supabase_db_url
        self._pool: Optional[asyncpg.Pool] = None
    
    async def _get_pool(self) -> asyncpg.Pool:
        """Get or create connection pool."""
        if self._pool is None:
            if not self.db_url:
                raise ValueError("Supabase DB URL not configured")
            
            self._pool = await asyncpg.create_pool(
                self.db_url,
                min_size=1,
                max_size=5,
                command_timeout=10
            )
            logger.info("Created Supabase connection pool")
        
        return self._pool
    
    async def _ensure_profiles_table(self) -> None:
        """Ensure profiles table exists with required schema."""
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            # Check if table exists
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'profiles'
                )
            """)
            
            if not table_exists:
                logger.info("Creating profiles table")
                await conn.execute("""
                    CREATE TABLE profiles (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email TEXT UNIQUE NOT NULL,
                        role TEXT NOT NULL DEFAULT 'user',
                        tier TEXT NOT NULL DEFAULT 'free',
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    )
                """)
                
                # Create index on email for fast lookups
                await conn.execute("""
                    CREATE INDEX idx_profiles_email ON profiles(email)
                """)
                
                logger.info("Created profiles table with indexes")
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email address.
        
        Args:
            email: User email address
            
        Returns:
            User object if found, None otherwise
        """
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, email, role, tier, created_at
                FROM profiles
                WHERE email = $1
            """, email)
            
            if row:
                return User(
                    id=row['id'],
                    email=row['email'],
                    role=row['role'],
                    tier=row['tier'],
                    created_at=str(row['created_at']) if row['created_at'] else None
                )
        
        return None
    
    async def create_user(self, email: str, role: str = "user", tier: str = "free") -> User:
        """
        Create a new user in Supabase.
        
        Args:
            email: User email address
            role: User role (default: "user")
            tier: User tier (default: "free")
            
        Returns:
            Created User object
        """
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            user_id = uuid4()
            now = datetime.now()
            
            await conn.execute("""
                INSERT INTO profiles (id, email, role, tier, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, user_id, email, role, tier, now, now)
            
            logger.info(f"Created user {email} with ID {user_id}")
            
            return User(
                id=user_id,
                email=email,
                role=role,
                tier=tier,
                created_at=now.isoformat()
            )
    
    async def get_or_provision_user(self, email: str) -> User:
        """
        Get existing user or provision new one (JIT provisioning).
        
        Args:
            email: User email address
            
        Returns:
            User object (existing or newly created)
        """
        # Ensure table exists
        await self._ensure_profiles_table()
        
        # Try to get existing user
        user = await self.get_user_by_email(email)
        
        if user:
            return user
        
        # User doesn't exist, provision new one
        logger.info(f"Provisioning new user: {email}")
        return await self.create_user(email)
    
    async def is_admin(self, email: str) -> bool:
        """
        Check if user is an admin.
        
        Args:
            email: User email address
            
        Returns:
            True if user has admin role, False otherwise
        """
        user = await self.get_user_by_email(email)
        return user is not None and user.role == "admin"
    
    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("Closed Supabase connection pool")
