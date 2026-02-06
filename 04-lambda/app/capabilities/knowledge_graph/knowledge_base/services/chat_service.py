"""Chat service for RAG-enhanced conversation."""

import logging
from typing import Any

import httpx
import openai
from app.capabilities.knowledge_graph.knowledge_base.config import config

logger = logging.getLogger(__name__)

# System prompt for the knowledge base chat
KB_SYSTEM_PROMPT = """You are a helpful knowledge base assistant. Your role is to answer questions based on the provided context from articles and web search results.

Guidelines:
1. Base your answers primarily on the provided context
2. When citing sources, use inline citations like [1], [2], etc.
3. If the context doesn't contain enough information, say so honestly
4. Highlight when information might be outdated and suggest verification
5. If you notice conflicting information between sources, point it out
6. Keep answers clear, structured, and actionable

Format your response with:
- Clear headings for different sections (if applicable)
- Bullet points for lists
- Code blocks for any code examples (with language specified)
- Citations at the end with numbered sources

If you detect potentially outdated information, suggest the user propose an edit to update the article."""


class ChatService:
    """Service for RAG-enhanced chat functionality."""

    def __init__(self, openai_client: openai.AsyncOpenAI | None = None):
        """
        Initialize the chat service.

        Args:
            openai_client: OpenAI client for LLM queries
        """
        self.openai_client = openai_client or openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url,
        )

    def _format_rag_context(self, rag_results: list[dict[str, Any]]) -> str:
        """Format RAG results as context for the LLM."""
        if not rag_results:
            return ""

        context_parts = ["## Knowledge Base Context\n"]
        for i, result in enumerate(rag_results, 1):
            title = result.get("document_title") or result.get("title", "Untitled")
            content = result.get("content", "")
            source = result.get("document_source") or result.get("source_url", "")

            context_parts.append(f"### Source [{i}]: {title}")
            if source:
                context_parts.append(f"URL: {source}")
            context_parts.append(f"\n{content[:2000]}\n")  # Limit content length

        return "\n".join(context_parts)

    def _format_web_context(self, web_results: list[dict[str, Any]]) -> str:
        """Format web search results as context."""
        if not web_results:
            return ""

        context_parts = ["## Web Search Results\n"]
        for i, result in enumerate(web_results, 1):
            title = result.get("title", "Untitled")
            content = result.get("content", "")
            url = result.get("url", "")

            context_parts.append(f"### Web Source [{i}]: {title}")
            if url:
                context_parts.append(f"URL: {url}")
            context_parts.append(f"\n{content[:1000]}\n")  # Shorter for web results

        return "\n".join(context_parts)

    def _extract_citations(
        self,
        rag_results: list[dict[str, Any]],
        web_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Extract citation metadata from results."""
        citations = []

        # Add RAG citations
        for i, result in enumerate(rag_results, 1):
            citations.append(
                {
                    "index": i,
                    "title": result.get("document_title") or result.get("title", "Untitled"),
                    "source": result.get("document_source") or result.get("source_url", ""),
                    "article_id": result.get("document_id") or result.get("_id"),
                    "type": "knowledge_base",
                }
            )

        # Add web citations (continuing numbering)
        start_idx = len(rag_results) + 1
        for i, result in enumerate(web_results, start_idx):
            citations.append(
                {
                    "index": i,
                    "title": result.get("title", "Untitled"),
                    "source": result.get("url", ""),
                    "type": "web",
                }
            )

        return citations

    async def chat(
        self,
        query: str,
        rag_results: list[dict[str, Any]],
        web_results: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Generate a chat response using RAG context.

        Args:
            query: User question
            rag_results: Results from knowledge base search
            web_results: Optional web search results

        Returns:
            Dict with 'answer' and 'citations'
        """
        web_results = web_results or []

        # Build context
        rag_context = self._format_rag_context(rag_results)
        web_context = self._format_web_context(web_results)

        full_context = f"{rag_context}\n\n{web_context}".strip()

        if not full_context:
            full_context = "No relevant context found in the knowledge base or web search."

        # Build messages
        messages = [
            {"role": "system", "content": KB_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Context:\n{full_context}\n\n---\n\nQuestion: {query}",
            },
        ]

        try:
            response = await self.openai_client.chat.completions.create(
                model=config.llm_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
            )

            answer = response.choices[0].message.content or "I couldn't generate a response."

            # Extract citations
            citations = self._extract_citations(rag_results, web_results)

            return {
                "answer": answer,
                "citations": citations,
            }

        except Exception as e:
            logger.error(f"Chat error: {e}")
            return {
                "answer": f"Sorry, I encountered an error generating a response: {e!s}",
                "citations": [],
            }

    async def fetch_url_content(self, url: str) -> dict[str, Any]:
        """
        Fetch and parse content from a URL using Crawl4AI.

        Args:
            url: URL to fetch

        Returns:
            Dict with title, content, etc.
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try Crawl4AI first
                try:
                    response = await client.post(
                        f"{config.crawl4ai_url}/crawl",
                        json={"url": url, "return_markdown": True},
                    )
                    response.raise_for_status()
                    data = response.json()

                    return {
                        "title": data.get("title", "Untitled"),
                        "content": data.get("markdown", data.get("text", "")),
                        "source_url": url,
                        "source_type": "web_crawl",
                    }
                except Exception as e:
                    logger.warning(f"Crawl4AI failed, falling back to direct fetch: {e}")

                # Fallback to direct fetch
                response = await client.get(url)
                response.raise_for_status()

                # Basic HTML to text conversion
                import re
                from html import unescape

                text = response.text
                # Remove script and style tags
                text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL)
                text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
                # Remove HTML tags
                text = re.sub(r"<[^>]+>", " ", text)
                # Unescape HTML entities
                text = unescape(text)
                # Clean up whitespace
                text = re.sub(r"\s+", " ", text).strip()

                # Try to extract title
                title_match = re.search(r"<title>([^<]+)</title>", response.text, re.IGNORECASE)
                title = title_match.group(1) if title_match else "Untitled"

                return {
                    "title": title,
                    "content": text[:10000],  # Limit content
                    "source_url": url,
                    "source_type": "web_crawl",
                }

        except Exception as e:
            logger.error(f"Error fetching URL {url}: {e}")
            return {
                "title": "Error",
                "content": f"Could not fetch content from {url}: {e!s}",
                "source_url": url,
                "source_type": "error",
            }
