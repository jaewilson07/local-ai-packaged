"""
Document embedding generation for vector search.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from dotenv import load_dotenv
import openai

from server.projects.mongo_rag.ingestion.chunker import DocumentChunk
from server.projects.mongo_rag.config import config

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Initialize client with settings
embedding_client = openai.AsyncOpenAI(
    api_key=config.embedding_api_key,
    base_url=config.embedding_base_url
)
EMBEDDING_MODEL = config.embedding_model


class EmbeddingGenerator:
    """Generates embeddings for document chunks."""

    def __init__(
        self,
        model: str = EMBEDDING_MODEL,
        batch_size: int = 100
    ):
        """
        Initialize embedding generator.

        Args:
            model: Embedding model to use
            batch_size: Number of texts to process in parallel
        """
        self.model = model
        self.batch_size = batch_size

        # Model-specific configurations
        self.model_configs = {
            "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
            "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
            "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191}
        }

        self.config = self.model_configs.get(
            model,
            {"dimensions": 1536, "max_tokens": 8191}
        )

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Truncate text if too long (rough estimation: 4 chars per token)
        if len(text) > self.config["max_tokens"] * 4:
            text = text[:self.config["max_tokens"] * 4]

        response = await embedding_client.embeddings.create(
            model=self.model,
            input=text
        )

        return response.data[0].embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Truncate texts if too long
        processed_texts = []
        for text in texts:
            if len(text) > self.config["max_tokens"] * 4:
                text = text[:self.config["max_tokens"] * 4]
            processed_texts.append(text)

        response = await embedding_client.embeddings.create(
            model=self.model,
            input=processed_texts
        )

        return [data.embedding for data in response.data]

    async def embed_chunks(
        self,
        chunks: List[DocumentChunk],
        progress_callback: Optional[callable] = None
    ) -> List[DocumentChunk]:
        """
        Generate embeddings for document chunks.

        Args:
            chunks: List of document chunks
            progress_callback: Optional callback for progress updates

        Returns:
            Chunks with embeddings added
        """
        if not chunks:
            return chunks

        logger.info(f"Generating embeddings for {len(chunks)} chunks")

        # Process chunks in batches
        embedded_chunks = []
        total_batches = (len(chunks) + self.batch_size - 1) // self.batch_size

        for i in range(0, len(chunks), self.batch_size):
            batch_chunks = chunks[i:i + self.batch_size]
            batch_texts = [chunk.content for chunk in batch_chunks]

            # Generate embeddings for this batch
            embeddings = await self.generate_embeddings_batch(batch_texts)

            # Add embeddings to chunks
            for chunk, embedding in zip(batch_chunks, embeddings):
                embedded_chunk = DocumentChunk(
                    content=chunk.content,
                    index=chunk.index,
                    start_char=chunk.start_char,
                    end_char=chunk.end_char,
                    metadata={
                        **chunk.metadata,
                        "embedding_model": self.model,
                        "embedding_generated_at": datetime.now().isoformat()
                    },
                    token_count=chunk.token_count
                )
                embedded_chunk.embedding = embedding
                embedded_chunks.append(embedded_chunk)

            # Progress update
            current_batch = (i // self.batch_size) + 1
            if progress_callback:
                progress_callback(current_batch, total_batches)

            logger.info(f"Processed batch {current_batch}/{total_batches}")

        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")
        return embedded_chunks

    async def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query.

        Args:
            query: Search query

        Returns:
            Query embedding
        """
        return await self.generate_embedding(query)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model."""
        return self.config["dimensions"]
    
    async def generate_contextual_embedding(
        self,
        full_document: str,
        chunk: str
    ) -> tuple[str, bool]:
        """
        Generate contextual information for a chunk within a document to improve retrieval.
        
        Args:
            full_document: The complete document text
            chunk: The specific chunk of text to generate context for
        
        Returns:
            Tuple containing:
            - The contextual text that situates the chunk within the document
            - Boolean indicating if contextual embedding was performed
        """
        if not config.use_contextual_embeddings:
            return chunk, False
        
        try:
            # Create the prompt for generating contextual information
            prompt = f"""<document> 
{full_document[:25000]} 
</document>
Here is the chunk we want to situate within the whole document 
<chunk> 
{chunk}
</chunk> 
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

            # Initialize OpenAI client for chat completions
            client = openai.AsyncOpenAI(
                api_key=config.llm_api_key,
                base_url=config.llm_base_url
            )
            
            # Call the LLM API to generate contextual information
            response = await client.chat.completions.create(
                model=config.llm_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that provides concise contextual information."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            # Extract the generated context
            context = response.choices[0].message.content.strip()
            
            # Combine the context with the original chunk
            contextual_text = f"{context}\n---\n{chunk}"
            
            return contextual_text, True
        
        except Exception as e:
            logger.error(f"Error generating contextual embedding: {e}. Using original chunk instead.")
            return chunk, False


def create_embedder(model: str = EMBEDDING_MODEL, **kwargs) -> EmbeddingGenerator:
    """
    Create embedding generator.

    Args:
        model: Embedding model to use
        **kwargs: Additional arguments for EmbeddingGenerator

    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model=model, **kwargs)
