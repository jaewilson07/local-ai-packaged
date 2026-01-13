"""Knowledge Base project for article management and collaborative refinement."""

from capabilities.knowledge_graph.knowledge_base.models import (
    Article,
    ArticleEditProposal,
    ProposalStatus,
)

__all__ = ["Article", "ArticleEditProposal", "ProposalStatus"]
