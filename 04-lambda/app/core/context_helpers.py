"""Helper functions for creating Pydantic AI RunContext.

Provides standardized RunContext creation for testing and tool execution.
"""

from typing import TypeVar

from pydantic_ai import RunContext

TDeps = TypeVar("TDeps")


def create_run_context(deps: TDeps) -> RunContext[TDeps]:
    """
    Create a RunContext for testing or direct tool invocation.
    
    This helper provides a type-safe way to create RunContext instances
    that can be passed to agent tools for testing or direct execution.
    
    Args:
        deps: The dependencies object for the context
        
    Returns:
        A properly typed RunContext instance
        
    Examples:
        >>> # Create context for testing
        >>> deps = AgentDeps()
        >>> await deps.initialize()
        >>> ctx = create_run_context(deps)
        >>> 
        >>> # Call tool directly
        >>> result = await semantic_search(ctx, query="test")
        >>> 
        >>> # Cleanup
        >>> await deps.cleanup()
        
    Note:
        This is primarily for testing and sample scripts.
        In production, agents create RunContext automatically.
    """
    # Create a minimal RunContext with the provided dependencies
    # The RunContext class expects certain internal state, so we create
    # it through the proper Pydantic AI mechanisms
    return RunContext[TDeps](deps=deps, retry=0, messages=[])
