"""Wrapper classes for dependency injection patterns."""

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

TDeps = TypeVar("TDeps")


@dataclass
class DepsWrapper(Generic[TDeps]):
    """
    Wrapper for passing dependencies through layers.
    
    Useful when you need to pass dependencies through intermediate
    functions that don't directly use them.
    
    Examples:
        >>> deps = AgentDeps.from_settings()
        >>> await deps.initialize()
        >>> 
        >>> # Wrap dependencies
        >>> wrapper = DepsWrapper(deps)
        >>> 
        >>> # Pass through layers
        >>> result = await process_with_deps(wrapper)
        >>> 
        >>> # Unwrap and cleanup
        >>> await wrapper.deps.cleanup()
    """

    deps: TDeps

    def __getattr__(self, name: str) -> Any:
        """Allow direct access to wrapped dependency attributes."""
        return getattr(self.deps, name)


@dataclass
class ConfigWrapper:
    """
    Wrapper for configuration objects.
    
    Provides a consistent interface for accessing configuration
    from different sources (env vars, files, databases).
    """

    _config: dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value."""
        self._config[key] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return self._config.copy()

    @classmethod
    def from_dict(cls, config: dict[str, Any]) -> "ConfigWrapper":
        """Create wrapper from dictionary."""
        return cls(_config=config.copy())
