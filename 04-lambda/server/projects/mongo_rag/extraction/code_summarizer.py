"""Generate summaries for code examples using LLM."""

import logging
import os
from typing import Optional

import openai
from server.projects.mongo_rag.config import config

logger = logging.getLogger(__name__)


async def generate_code_example_summary(
    code: str,
    context_before: str,
    context_after: str
) -> str:
    """
    Generate a summary for a code example using its surrounding context.
    
    Args:
        code: The code example
        context_before: Context before the code
        context_after: Context after the code
    
    Returns:
        A summary of what the code example demonstrates
    """
    # Use LLM model from config
    model_choice = config.llm_model
    
    # Create the prompt
    prompt = f"""<context_before>
{context_before[-500:] if len(context_before) > 500 else context_before}
</context_before>

<code_example>
{code[:1500] if len(code) > 1500 else code}
</code_example>

<context_after>
{context_after[:500] if len(context_after) > 500 else context_after}
</context_after>

Based on the code example and its surrounding context, provide a concise summary (2-3 sentences) that describes what this code example demonstrates and its purpose. Focus on the practical application and key concepts illustrated.
"""
    
    try:
        # Initialize OpenAI client
        client = openai.AsyncOpenAI(
            api_key=config.llm_api_key,
            base_url=config.llm_base_url
        )
        
        response = await client.chat.completions.create(
            model=model_choice,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides concise code example summaries."
                },
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    except Exception as e:
        logger.error(f"Error generating code example summary: {e}")
        return "Code example for demonstration purposes."

