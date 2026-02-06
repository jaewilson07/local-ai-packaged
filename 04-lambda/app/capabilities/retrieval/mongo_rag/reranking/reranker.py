"""Cross-encoder reranking for search results."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from capabilities.retrieval.mongo_rag.tools import SearchResult

from sentence_transformers import CrossEncoder

logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker for improving search result relevance."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker.

        Args:
            model_name: Name of the cross-encoder model to use
        """
        self.model_name = model_name
        self.model: CrossEncoder | None = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the cross-encoder model."""
        if self._initialized:
            return

        if CrossEncoder is None:
            logger.warning("sentence_transformers not available - reranking will be disabled")
            self.model = None
            return

        try:
            logger.info(f"Loading reranking model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            self._initialized = True
            logger.info("Reranking model loaded successfully")
        except Exception:
            logger.exception("Failed to load reranking model")
            self.model = None

    def rerank_results(
        self, query: str, results: list["SearchResult"], content_key: str = "content"
    ) -> list["SearchResult"]:
        """
        Rerank search results using a cross-encoder model.

        Args:
            query: The search query
            results: List of search results
            content_key: The key in each result that contains the text content

        Returns:
            Reranked list of results
        """
        # Import here to avoid circular import
        from capabilities.retrieval.mongo_rag.tools import SearchResult

        if not self.model or not results:
            return results

        try:
            # Extract content from results
            texts = [getattr(result, content_key, result.content) for result in results]

            # Create pairs of [query, document] for the cross-encoder
            pairs = [[query, text] for text in texts]

            # Get relevance scores from the cross-encoder
            scores = self.model.predict(pairs)

            # Add scores to results and sort by score (descending)
            reranked_results = []
            for i, result in enumerate(results):
                # Create new result with updated similarity (rerank score)
                reranked_result = SearchResult(
                    chunk_id=result.chunk_id,
                    document_id=result.document_id,
                    content=result.content,
                    similarity=float(scores[i]),
                    metadata={
                        **result.metadata,
                        "rerank_score": float(scores[i]),
                        "original_similarity": result.similarity,
                    },
                    document_title=result.document_title,
                    document_source=result.document_source,
                )
                reranked_results.append(reranked_result)

            # Sort by rerank score (descending)
            reranked_results.sort(key=lambda x: x.similarity, reverse=True)

            logger.info(f"Reranked {len(reranked_results)} results")
            return reranked_results

        except Exception:
            logger.exception("Error during reranking")
            return results


# Global reranker instance
_reranker: Reranker | None = None


def get_reranker() -> Reranker | None:
    """Get the global reranker instance."""
    return _reranker


def initialize_reranker(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> Reranker:
    """
    Initialize the global reranker instance.

    Args:
        model_name: Name of the cross-encoder model

    Returns:
        Initialized reranker instance
    """
    global _reranker
    _reranker = Reranker(model_name)
    _reranker.initialize()
    return _reranker
