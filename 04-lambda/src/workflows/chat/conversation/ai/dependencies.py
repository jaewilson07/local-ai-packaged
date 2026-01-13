"""Dependencies for Conversation workflow.

The conversation workflow uses PersonaDeps from capabilities for its dependencies,
as it orchestrates conversations that involve persona state management.
"""

import logging
from dataclasses import dataclass

from capabilities.persona.ai.dependencies import PersonaDeps

logger = logging.getLogger(__name__)


@dataclass
class ConversationDeps(PersonaDeps):
    """Dependencies for Conversation workflow.

    Inherits from PersonaDeps since conversation orchestration
    requires persona state management capabilities.
    """

    # ConversationDeps is essentially PersonaDeps, so we inherit all methods
    # No additional initialization or cleanup needed beyond PersonaDeps


__all__ = ["ConversationDeps"]
