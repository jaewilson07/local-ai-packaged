"""Source management for tracking document sources."""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from pymongo import AsyncMongoClient
from bson import ObjectId

from server.projects.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def get_available_sources(
    mongo_client: AsyncMongoClient
) -> List[Dict[str, Any]]:
    """
    Get all available sources from the sources collection.
    
    Args:
        mongo_client: MongoDB client
    
    Returns:
        List of source dictionaries with summaries and statistics
    """
    try:
        db = mongo_client[config.mongodb_database]
        sources_collection = db["sources"]
        
        # Query all sources
        cursor = sources_collection.find().sort("source_id", 1)
        sources = await cursor.to_list(length=None)
        
        # Format sources
        formatted_sources = []
        for source in sources:
            formatted_sources.append({
                "source_id": source.get("source_id"),
                "summary": source.get("summary", ""),
                "total_word_count": source.get("total_word_count", 0),
                "document_count": source.get("document_count", 0),
                "created_at": source.get("created_at"),
                "updated_at": source.get("updated_at")
            })
        
        logger.info(f"Retrieved {len(formatted_sources)} sources")
        return formatted_sources
        
    except Exception as e:
        logger.exception(f"Error retrieving sources: {e}")
        return []


async def update_source_info(
    mongo_client: AsyncMongoClient,
    source_id: str,
    summary: str,
    word_count: int,
    document_count: Optional[int] = None
) -> None:
    """
    Update or insert source information in the sources collection.
    
    Args:
        mongo_client: MongoDB client
        source_id: The source ID (domain or path)
        summary: Summary of the source
        word_count: Total word count for the source
        document_count: Number of documents from this source
    """
    try:
        db = mongo_client[config.mongodb_database]
        sources_collection = db["sources"]
        
        # Try to update existing source
        result = await sources_collection.update_one(
            {"source_id": source_id},
            {
                "$set": {
                    "summary": summary,
                    "total_word_count": word_count,
                    "updated_at": datetime.now()
                },
                "$setOnInsert": {
                    "created_at": datetime.now()
                }
            },
            upsert=True
        )
        
        # Update document count if provided
        if document_count is not None:
            await sources_collection.update_one(
                {"source_id": source_id},
                {"$set": {"document_count": document_count}}
            )
        
        if result.upserted_id:
            logger.info(f"Created new source: {source_id}")
        else:
            logger.debug(f"Updated source: {source_id}")
            
    except Exception as e:
        logger.error(f"Error updating source {source_id}: {e}")


async def extract_source_summary(
    mongo_client: AsyncMongoClient,
    source_id: str,
    content: str,
    max_length: int = 500
) -> str:
    """
    Extract a summary for a source from its content using an LLM.
    
    This function uses the LLM to generate a concise summary of the source content.
    
    Args:
        mongo_client: MongoDB client (for LLM access via config)
        source_id: The source ID (domain)
        content: The content to extract a summary from
        max_length: Maximum length of the summary
    
    Returns:
        A summary string
    """
    # Default summary if we can't extract anything meaningful
    default_summary = f"Content from {source_id}"
    
    if not content or len(content.strip()) == 0:
        return default_summary
    
    # Get the model choice from config
    model_choice = config.llm_model
    
    # Limit content length to avoid token limits
    truncated_content = content[:25000] if len(content) > 25000 else content
    
    # Create the prompt for generating the summary
    prompt = f"""<source_content>
{truncated_content}
</source_content>

The above content is from the documentation for '{source_id}'. Please provide a concise summary (3-5 sentences) that describes what this library/tool/framework is about. The summary should help understand what the library/tool/framework accomplishes and the purpose.
"""
    
    try:
        import openai
        
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
        
        # Call the LLM API to generate the summary
        response = await client.chat.completions.create(
            model=model_choice,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise library/tool/framework summaries."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        # Extract the generated summary
        summary = response.choices[0].message.content.strip()
        
        # Ensure the summary is not too long
        if len(summary) > max_length:
            summary = summary[:max_length] + "..."
            
        return summary
    
    except Exception as e:
        logger.error(f"Error generating summary with LLM for {source_id}: {e}. Using default summary.")
        return default_summary

