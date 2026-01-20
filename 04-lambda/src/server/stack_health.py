"""Stack health check API.

Provides aggregated health status for all services across all stacks.
This is an authenticated, read-only endpoint for monitoring/dashboards.

Best practices applied:
- Caching (30s TTL) to prevent overloading health endpoints
- Per-service timeouts (3s) to prevent blocking
- Critical vs optional service classification
- Concurrent checks for fast response
- No circular dependencies (Lambda doesn't check itself via network)
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Literal

import aiohttp
from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel
from services.auth.dependencies import get_current_user
from services.auth.models import User

logger = logging.getLogger(__name__)

# =============================================================================
# Configuration
# =============================================================================

# Health check settings
HEALTH_CHECK_TIMEOUT = 3.0  # seconds per service
HEALTH_CHECK_CACHE_TTL = 30.0  # seconds


class CheckType(str, Enum):
    """Type of health check to perform."""

    HTTP = "http"
    TCP = "tcp"


@dataclass
class ServiceConfig:
    """Configuration for a service health check."""

    name: str
    stack: str
    host: str
    port: int
    check_type: CheckType
    path: str = ""  # For HTTP checks
    critical: bool = False


# =============================================================================
# Service Registry
# =============================================================================

SERVICE_REGISTRY: list[ServiceConfig] = [
    # Infrastructure stack (00-infrastructure)
    ServiceConfig(
        name="caddy",
        stack="infrastructure",
        host="caddy",
        port=80,
        check_type=CheckType.HTTP,
        path="/health",
        critical=True,
    ),
    ServiceConfig(
        name="redis",
        stack="infrastructure",
        host="redis",
        port=6379,
        check_type=CheckType.TCP,
        critical=True,
    ),
    # Data stack (01-data)
    ServiceConfig(
        name="supabase-db",
        stack="data",
        host="supabase-db",
        port=5432,
        check_type=CheckType.TCP,
        critical=True,
    ),
    ServiceConfig(
        name="mongodb",
        stack="data",
        host="mongodb",
        port=27017,
        check_type=CheckType.TCP,
        critical=True,
    ),
    ServiceConfig(
        name="neo4j",
        stack="data",
        host="neo4j",
        port=7474,
        check_type=CheckType.HTTP,
        path="/",
        critical=False,
    ),
    ServiceConfig(
        name="qdrant",
        stack="data",
        host="qdrant",
        port=6333,
        check_type=CheckType.HTTP,
        path="/healthz",
        critical=False,
    ),
    ServiceConfig(
        name="supabase-minio",
        stack="data",
        host="supabase-minio",
        port=9020,
        check_type=CheckType.HTTP,
        path="/minio/health/live",
        critical=False,
    ),
    # Compute stack (02-compute)
    ServiceConfig(
        name="ollama",
        stack="compute",
        host="ollama",
        port=11434,
        check_type=CheckType.TCP,
        critical=True,
    ),
    ServiceConfig(
        name="comfyui",
        stack="compute",
        host="comfyui",
        port=8188,
        check_type=CheckType.HTTP,
        path="/",
        critical=False,
    ),
    # Apps stack (03-apps)
    ServiceConfig(
        name="n8n",
        stack="apps",
        host="n8n",
        port=5678,
        check_type=CheckType.HTTP,
        path="/healthz",
        critical=False,
    ),
    ServiceConfig(
        name="flowise",
        stack="apps",
        host="flowise",
        port=3001,
        check_type=CheckType.HTTP,
        path="/api/v1/ping",
        critical=False,
    ),
    ServiceConfig(
        name="open-webui",
        stack="apps",
        host="open-webui",
        port=8080,
        check_type=CheckType.HTTP,
        path="/health",
        critical=False,
    ),
    ServiceConfig(
        name="immich-server",
        stack="apps",
        host="immich-server",
        port=2283,
        check_type=CheckType.TCP,
        critical=False,
    ),
]


# =============================================================================
# Pydantic Models
# =============================================================================


class ServiceHealth(BaseModel):
    """Health status of a single service."""

    name: str
    status: Literal["healthy", "unhealthy"]
    latency_ms: int | None = None
    error: str | None = None
    critical: bool = False


class StackHealth(BaseModel):
    """Health status of a stack (collection of services)."""

    status: Literal["healthy", "degraded", "unhealthy"]
    services: list[ServiceHealth]


class HealthSummary(BaseModel):
    """Summary counts for health status."""

    total_services: int
    healthy: int
    unhealthy: int
    critical_healthy: int
    critical_unhealthy: int


class FullStackHealth(BaseModel):
    """Complete health status for all stacks."""

    status: Literal["healthy", "degraded", "unhealthy"]
    cached: bool = False
    cached_at: datetime | None = None
    checked_at: datetime
    stacks: dict[str, StackHealth]
    summary: HealthSummary


# =============================================================================
# Stack Health Service
# =============================================================================


class StackHealthService:
    """Service for checking health of all stacks."""

    _instance: "StackHealthService | None" = None
    _cache: FullStackHealth | None = None
    _cache_time: float = 0.0

    def __new__(cls) -> "StackHealthService":
        """Singleton pattern for caching."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def _check_http(self, service: ServiceConfig) -> ServiceHealth:
        """Perform HTTP health check."""
        url = f"http://{service.host}:{service.port}{service.path}"
        start = time.monotonic()

        try:
            timeout = aiohttp.ClientTimeout(total=HEALTH_CHECK_TIMEOUT)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    latency_ms = int((time.monotonic() - start) * 1000)
                    if response.status < 400:
                        return ServiceHealth(
                            name=service.name,
                            status="healthy",
                            latency_ms=latency_ms,
                            critical=service.critical,
                        )
                    return ServiceHealth(
                        name=service.name,
                        status="unhealthy",
                        latency_ms=latency_ms,
                        error=f"HTTP {response.status}",
                        critical=service.critical,
                    )
        except asyncio.TimeoutError:
            return ServiceHealth(
                name=service.name,
                status="unhealthy",
                error="Connection timeout",
                critical=service.critical,
            )
        except Exception as e:
            # Sanitize error message (no sensitive details)
            error_msg = str(e).split("\n")[0][:100]
            return ServiceHealth(
                name=service.name,
                status="unhealthy",
                error=error_msg,
                critical=service.critical,
            )

    async def _check_tcp(self, service: ServiceConfig) -> ServiceHealth:
        """Perform TCP connectivity check."""
        start = time.monotonic()

        try:
            # Use asyncio to open a TCP connection
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(service.host, service.port),
                timeout=HEALTH_CHECK_TIMEOUT,
            )
            writer.close()
            await writer.wait_closed()

            latency_ms = int((time.monotonic() - start) * 1000)
            return ServiceHealth(
                name=service.name,
                status="healthy",
                latency_ms=latency_ms,
                critical=service.critical,
            )
        except asyncio.TimeoutError:
            return ServiceHealth(
                name=service.name,
                status="unhealthy",
                error="Connection timeout",
                critical=service.critical,
            )
        except Exception as e:
            # Sanitize error message
            error_msg = str(e).split("\n")[0][:100]
            return ServiceHealth(
                name=service.name,
                status="unhealthy",
                error=error_msg,
                critical=service.critical,
            )

    async def _check_service(self, service: ServiceConfig) -> ServiceHealth:
        """Check a single service based on its check type."""
        if service.check_type == CheckType.HTTP:
            return await self._check_http(service)
        return await self._check_tcp(service)

    def _compute_stack_status(
        self, services: list[ServiceHealth]
    ) -> Literal["healthy", "degraded", "unhealthy"]:
        """Compute status for a single stack."""
        critical_unhealthy = any(s.status == "unhealthy" and s.critical for s in services)
        any_unhealthy = any(s.status == "unhealthy" for s in services)

        if critical_unhealthy:
            return "unhealthy"
        if any_unhealthy:
            return "degraded"
        return "healthy"

    def _compute_overall_status(
        self, stacks: dict[str, StackHealth]
    ) -> Literal["healthy", "degraded", "unhealthy"]:
        """Compute overall status based on all stacks."""
        # Check for any critical service failures across all stacks
        for stack in stacks.values():
            for service in stack.services:
                if service.status == "unhealthy" and service.critical:
                    return "unhealthy"

        # Check for any unhealthy services (non-critical)
        for stack in stacks.values():
            if stack.status in ("degraded", "unhealthy"):
                return "degraded"

        return "healthy"

    async def check_all(self, bypass_cache: bool = False) -> FullStackHealth:
        """Check all services and return aggregated health status.

        Args:
            bypass_cache: If True, skip cache and perform fresh checks.

        Returns:
            FullStackHealth with status of all services.
        """
        # Check cache
        now = time.monotonic()
        if not bypass_cache and self._cache and (now - self._cache_time) < HEALTH_CHECK_CACHE_TTL:
            # Return cached result with updated metadata
            return FullStackHealth(
                status=self._cache.status,
                cached=True,
                cached_at=datetime.now(timezone.utc),
                checked_at=self._cache.checked_at,
                stacks=self._cache.stacks,
                summary=self._cache.summary,
            )

        # Perform all checks concurrently
        check_start = datetime.now(timezone.utc)
        tasks = [self._check_service(service) for service in SERVICE_REGISTRY]
        results = await asyncio.gather(*tasks)

        # Group results by stack
        stacks: dict[str, list[ServiceHealth]] = {}
        for service_config, health in zip(SERVICE_REGISTRY, results, strict=False):
            stack_name = service_config.stack
            if stack_name not in stacks:
                stacks[stack_name] = []
            stacks[stack_name].append(health)

        # Compute stack statuses
        stack_health: dict[str, StackHealth] = {}
        for stack_name, services in stacks.items():
            stack_health[stack_name] = StackHealth(
                status=self._compute_stack_status(services),
                services=services,
            )

        # Compute summary
        all_services = [s for services in stacks.values() for s in services]
        summary = HealthSummary(
            total_services=len(all_services),
            healthy=sum(1 for s in all_services if s.status == "healthy"),
            unhealthy=sum(1 for s in all_services if s.status == "unhealthy"),
            critical_healthy=sum(1 for s in all_services if s.critical and s.status == "healthy"),
            critical_unhealthy=sum(
                1 for s in all_services if s.critical and s.status == "unhealthy"
            ),
        )

        # Build result
        result = FullStackHealth(
            status=self._compute_overall_status(stack_health),
            cached=False,
            cached_at=None,
            checked_at=check_start,
            stacks=stack_health,
            summary=summary,
        )

        # Update cache
        self._cache = result
        self._cache_time = now

        logger.info(
            "stack_health_checked",
            extra={
                "status": result.status,
                "healthy": summary.healthy,
                "unhealthy": summary.unhealthy,
                "critical_unhealthy": summary.critical_unhealthy,
            },
        )

        return result


# =============================================================================
# Router
# =============================================================================

router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/stack", response_model=FullStackHealth)
async def get_stack_health(
    user: User = Depends(get_current_user),
    cache_control: str | None = Header(None, alias="Cache-Control"),
) -> FullStackHealth:
    """Get aggregated health status for all stacks.

    This endpoint is authenticated and provides comprehensive health
    status for monitoring dashboards.

    Use `Cache-Control: no-cache` header to bypass the cache and
    get fresh health check results.

    Returns:
        FullStackHealth with status of all services across all stacks.
    """
    # Check for cache bypass
    bypass_cache = cache_control is not None and "no-cache" in cache_control.lower()

    service = StackHealthService()
    return await service.check_all(bypass_cache=bypass_cache)
