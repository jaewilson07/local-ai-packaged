"""Document grading for corrective RAG."""

import logging
from typing import List, Dict, Any, Optional
import openai

from server.projects.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def grade_documents(
    query: str,
    documents: List[Dict[str, Any]],
    llm_client: Optional[openai.AsyncOpenAI] = None,
    threshold: float = 0.5
) -> tuple[List[Dict[str, Any]], List[float]]:
    """
    Grade documents for relevance to the question (corrective RAG).
    
    Filters out irrelevant documents before they reach generation,
    improving answer quality.
    
    Args:
        query: User query
        documents: List of document dicts with 'content' and 'metadata' keys
        llm_client: Optional OpenAI client
        threshold: Relevance threshold (0.0-1.0)
    
    Returns:
        Tuple of (filtered_documents, scores)
    """
    if not query or not documents:
        return documents, [1.0] * len(documents)
    
    if not llm_client:
        llm_client = openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
    
    filtered_docs: List[Dict[str, Any]] = []
    scores: List[float] = []
    
    model_name = config.llm_model
    
    for doc in documents:
        content = doc.get("content", doc.get("text", ""))
        if not content:
            continue
        
        # Create focused prompt for grading
        prompt = f"""You are a grader assessing relevance of a retrieved document to a user question.

Here is the retrieved document:
{content[:500]}...

Here is the user question: {query}

If the document contains keyword(s) or semantic meaning related to the user question, grade it as relevant.
Give a binary score 'yes' or 'no' to indicate whether the document is relevant to the question.

Answer only 'yes' or 'no'."""

        try:
            response = await llm_client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            response_text = response.choices[0].message.content or ""
            is_relevant = "yes" in response_text.lower().strip()
            
            score = 1.0 if is_relevant else 0.0
            
            if score >= threshold:
                filtered_docs.append(doc)
                scores.append(score)
            else:
                scores.append(score)
        except Exception as e:
            logger.warning(f"Error grading document: {e}")
            # On error, keep the document (safer to include than exclude)
            filtered_docs.append(doc)
            scores.append(0.5)
    
    return filtered_docs, scores
