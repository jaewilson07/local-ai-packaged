"""Result synthesis from multiple queries."""

import logging
from typing import List, Dict, Any, Optional
import openai

from server.projects.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def synthesize_results(
    query: str,
    sub_query_results: List[Dict[str, Any]],
    llm_client: Optional[openai.AsyncOpenAI] = None
) -> str:
    """
    Synthesize results from multiple sub-queries into a coherent answer.
    
    Uses LLM to combine results from multiple queries into a single,
    coherent response.
    
    Args:
        query: Original query
        sub_query_results: List of result dicts, each with 'query' and 'results'
        llm_client: Optional OpenAI client
    
    Returns:
        Synthesized answer as string
    """
    if not sub_query_results:
        return "No results found."
    
    if len(sub_query_results) == 1:
        # Single result, just format it
        results = sub_query_results[0].get("results", [])
        if not results:
            return "No results found."
        
        # Format single result
        formatted = []
        for result in results[:5]:  # Limit to top 5
            content = result.get("content", result.get("text", ""))
            formatted.append(content)
        
        return "\n\n".join(formatted)
    
    if not llm_client:
        llm_client = openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
    
    try:
        # Build synthesis prompt
        synthesis_parts = [f"Original question: {query}\n\n"]
        
        for i, sub_result in enumerate(sub_query_results, 1):
            sub_query = sub_result.get("query", "")
            results = sub_result.get("results", [])
            
            synthesis_parts.append(f"Sub-question {i}: {sub_query}")
            for j, result in enumerate(results[:3], 1):  # Top 3 per sub-query
                content = result.get("content", result.get("text", ""))
                synthesis_parts.append(f"  Result {j}: {content[:300]}...")
            synthesis_parts.append("")
        
        synthesis_prompt = "\n".join(synthesis_parts)
        synthesis_prompt += "\n\nSynthesize these results into a coherent answer to the original question."
        
        response = await llm_client.chat.completions.create(
            model=config.llm_model,
            messages=[{"role": "user", "content": synthesis_prompt}],
            temperature=0.3,
        )
        
        return response.choices[0].message.content or "Unable to synthesize results."
    
    except Exception as e:
        logger.warning(f"Error synthesizing results: {e}")
        # Fallback: concatenate results
        all_results = []
        for sub_result in sub_query_results:
            results = sub_result.get("results", [])
            for result in results:
                content = result.get("content", result.get("text", ""))
                if content:
                    all_results.append(content)
        
        return "\n\n".join(all_results[:10])  # Limit to 10 results
