"""Query decomposition for complex multi-part queries."""

import logging
from typing import List, Optional
import openai

from server.projects.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def decompose_query(
    query: str,
    llm_client: Optional[openai.AsyncOpenAI] = None
) -> tuple[bool, List[str]]:
    """
    Decompose complex queries into sub-queries.
    
    Analyzes the query to determine if it needs decomposition (e.g., 
    "What is X and how does Y relate to Z?"), and if so, breaks it into
    2-4 focused sub-queries for better retrieval.
    
    Args:
        query: Original query
        llm_client: Optional OpenAI client (creates one if not provided)
    
    Returns:
        Tuple of (needs_decomposition, sub_queries)
    """
    if not query or not query.strip():
        return False, [query]
    
    if not llm_client:
        # Create client if not provided
        llm_client = openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
    
    try:
        # Use cheaper model for decomposition decision
        model_name = config.llm_model
        
        # First, determine if decomposition is needed
        decision_prompt = f"""Analyze this query and determine if it should be broken down into multiple sub-queries.

A query needs decomposition if it:
- Asks about multiple distinct topics (e.g., "What is X and how does Y work?")
- Requires information from different domains
- Has multiple independent questions combined with "and" or "also"

Query: {query}

Respond with only "yes" or "no"."""

        decision_response = await llm_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": decision_prompt}],
            temperature=0,
        )
        decision_text = decision_response.choices[0].message.content or ""
        needs_decomposition = "yes" in decision_text.lower().strip()
        
        if not needs_decomposition:
            return False, [query]
        
        # Decompose the query
        decompose_prompt = f"""Break down this complex query into 2-4 focused sub-queries.
Each sub-query should be specific and answerable independently.

Original query: {query}

Provide the sub-queries, one per line, numbered (1., 2., etc.).
Do not include any other text, just the numbered sub-queries."""

        decompose_response = await llm_client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": decompose_prompt}],
            temperature=0,
        )
        response_text = decompose_response.choices[0].message.content or ""
        
        # Parse sub-queries from numbered list
        sub_queries: List[str] = []
        for line in response_text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Remove numbering (1., 2., etc.) and clean up
            for prefix in ["1.", "2.", "3.", "4.", "5.", "-", "*"]:
                if line.startswith(prefix):
                    line = line[len(prefix):].strip()
                    break
            if line:
                sub_queries.append(line)
        
        # Fallback: if parsing failed, use original query
        if not sub_queries:
            sub_queries = [query]
        
        # Limit to 4 sub-queries max
        sub_queries = sub_queries[:4]
        
        return True, sub_queries
    
    except Exception as e:
        logger.warning(f"Error decomposing query: {e}")
        # On error, don't decompose
        return False, [query]
