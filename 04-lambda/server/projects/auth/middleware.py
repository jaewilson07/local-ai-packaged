"""Optional authentication middleware for FastAPI.

This middleware provides automatic JWT validation for all routes (except excluded ones)
and adds the user to request state. It works alongside the dependency-based approach.

Usage:
    # In main.py, add after CORS middleware:
    from server.projects.auth.middleware import AuthMiddleware
    
    app.add_middleware(
        AuthMiddleware,
        exclude_paths=["/health", "/docs", "/openapi.json", "/mcp", "/mcp-info", "/"]
    )
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import List, Optional
import logging

from server.projects.auth.services.jwt_service import JWTService
from server.projects.auth.services.supabase_service import SupabaseService
from server.projects.auth.services.neo4j_service import Neo4jService
from server.projects.auth.services.minio_service import MinIOService
from server.projects.auth.models import User
from server.projects.auth.config import config

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic JWT validation and user provisioning.
    
    This middleware:
    - Validates Cloudflare Access JWT for all routes (except excluded paths)
    - Performs JIT user provisioning
    - Adds user to request.state for easy access in endpoints
    - Returns 403/401 for missing/invalid tokens
    
    Excluded paths bypass authentication entirely.
    """
    
    def __init__(
        self,
        app,
        exclude_paths: Optional[List[str]] = None,
        exclude_path_prefixes: Optional[List[str]] = None
    ):
        """
        Initialize auth middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: Exact paths to exclude from auth (e.g., ["/health", "/docs"])
            exclude_path_prefixes: Path prefixes to exclude (e.g., ["/static", "/public"])
        """
        super().__init__(app)
        self.exclude_paths = set(exclude_paths or [])
        self.exclude_path_prefixes = exclude_path_prefixes or []
        
        # Default exclusions for common FastAPI endpoints
        default_exclusions = [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/",
        ]
        self.exclude_paths.update(default_exclusions)
    
    def _should_exclude(self, path: str) -> bool:
        """Check if path should be excluded from authentication."""
        # Check exact paths
        if path in self.exclude_paths:
            return True
        
        # Check path prefixes
        for prefix in self.exclude_path_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    async def dispatch(self, request: Request, call_next):
        """Process request through middleware."""
        # Skip authentication for excluded paths
        if self._should_exclude(request.url.path):
            return await call_next(request)
        
        # Extract JWT from header
        cf_jwt = request.headers.get("Cf-Access-Jwt-Assertion")
        
        if not cf_jwt:
            logger.warning(f"Missing JWT header for {request.url.path}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Missing Cf-Access-Jwt-Assertion header"
            )
        
        try:
            # Validate JWT and extract email
            jwt_service = JWTService(config)
            email = await jwt_service.validate_and_extract_email(cf_jwt)
            
            # Check if user exists in Supabase, provision if not
            supabase_service = SupabaseService(config)
            
            # Check if user already exists
            existing_user = await supabase_service.get_user_by_email(email)
            is_new_user = existing_user is None
            
            # Get or provision user
            user = await supabase_service.get_or_provision_user(email)
            
            # Provision in Neo4j and MinIO if this is a new user
            if is_new_user:
                try:
                    neo4j_service = Neo4jService(config)
                    await neo4j_service.provision_user(email)
                except Exception as e:
                    logger.warning(f"Neo4j provisioning failed for {email}: {e}")
                
                try:
                    minio_service = MinIOService(config)
                    await minio_service.provision_user(user.id, email)
                except Exception as e:
                    logger.warning(f"MinIO provisioning failed for {email}: {e}")
            
            # Add user to request state for easy access in endpoints
            request.state.user = user
            request.state.email = email
            
            # Continue to next middleware/endpoint
            response = await call_next(request)
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Authentication failed for {request.url.path}: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
