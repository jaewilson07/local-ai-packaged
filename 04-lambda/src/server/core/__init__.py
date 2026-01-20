"""Server core module.

IMPORTANT: For utilities and exceptions, import directly from submodules
to avoid circular imports:
    from server.core.api_utils import DependencyContext
    from server.core.exceptions import LLMException, MongoDBException
"""

from .error_handling import handle_project_errors
from .logging import setup_logging

__all__ = ["handle_project_errors", "setup_logging"]
