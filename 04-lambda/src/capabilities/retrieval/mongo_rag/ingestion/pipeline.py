"""
Main ingestion script for processing documents into MongoDB vector database.

This adapts the examples/ingestion/ingest.py pipeline to use MongoDB instead of PostgreSQL,
changing only the database layer while preserving all document processing logic.
"""

import argparse
import asyncio
import glob
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

# Load environment variables from project root (works from any directory)
# Path: ingestion/pipeline.py -> ingestion -> mongo_rag -> projects -> server -> 04-lambda -> root
from pathlib import Path
from typing import Any

from capabilities.retrieval.graphiti_rag.config import config as graphiti_config
from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
from capabilities.retrieval.graphiti_rag.ingestion.adapter import GraphitiIngestionAdapter
from capabilities.retrieval.mongo_rag.extraction.code_ingestion import ingest_code_examples
from capabilities.retrieval.mongo_rag.ingestion.chunker import (
    ChunkingConfig,
    DocumentChunk,
    create_chunker,
)
from capabilities.retrieval.mongo_rag.ingestion.embedder import create_embedder
from dotenv import load_dotenv
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE)
else:
    load_dotenv()  # Fallback for Docker container

logger = logging.getLogger(__name__)


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""

    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_chunk_size: int = 2000
    max_tokens: int = 512


@dataclass
class IngestionResult:
    """Result of document ingestion."""

    document_id: str
    title: str
    chunks_created: int
    processing_time_ms: float
    errors: list[str]


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into MongoDB vector database."""

    def __init__(
        self,
        config: IngestionConfig,
        documents_folder: str = "documents",
        clean_before_ingest: bool = True,
        user_id: str | None = None,
        user_email: str | None = None,
    ):
        """
        Initialize ingestion pipeline.

        Args:
            config: Ingestion configuration
            documents_folder: Folder containing documents
            clean_before_ingest: Whether to clean existing data before ingestion
            user_id: User UUID for RLS (optional, for user-scoped ingestion)
            user_email: User email for RLS (optional, for user-scoped ingestion)
        """
        self.config = config
        self.documents_folder = documents_folder
        self.clean_before_ingest = clean_before_ingest
        self.user_id = user_id
        self.user_email = user_email

        # Load settings - use RAG config for MongoDB/LLM settings
        from capabilities.retrieval.mongo_rag.config import config as rag_config

        self.settings = rag_config

        # Initialize MongoDB client and database references
        self.mongo_client: AsyncMongoClient | None = None
        self.db: Any | None = None

        # Initialize components
        self.chunker_config = ChunkingConfig(
            chunk_size=config.chunk_size,
            chunk_overlap=config.chunk_overlap,
            max_chunk_size=config.max_chunk_size,
            max_tokens=config.max_tokens,
        )

        self.chunker = create_chunker(self.chunker_config)
        self.embedder = create_embedder()

        # Graphiti ingestion adapter (optional)
        self.graphiti_adapter: GraphitiIngestionAdapter | None = None
        self.graphiti_deps: GraphitiRAGDeps | None = None

        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize MongoDB connections.

        Raises:
            ConnectionFailure: If MongoDB connection fails
            ServerSelectionTimeoutError: If MongoDB server selection times out
        """
        if self._initialized:
            return

        logger.info("Initializing ingestion pipeline...")

        try:
            # Initialize MongoDB client
            self.mongo_client = AsyncMongoClient(
                self.settings.mongodb_uri, serverSelectionTimeoutMS=5000
            )
            self.db = self.mongo_client[self.settings.mongodb_database]

            # Verify connection
            await self.mongo_client.admin.command("ping")
            logger.info(f"Connected to MongoDB database: {self.settings.mongodb_database}")

            # Initialize Graphiti if enabled
            if graphiti_config.use_graphiti:
                try:
                    self.graphiti_deps = GraphitiRAGDeps.from_settings()
                    await self.graphiti_deps.initialize()
                    if self.graphiti_deps.graphiti:
                        self.graphiti_adapter = GraphitiIngestionAdapter(
                            self.graphiti_deps.graphiti
                        )
                        logger.info("Graphiti ingestion adapter initialized")
                except Exception as e:
                    logger.warning(f"Failed to initialize Graphiti: {e}")
                    logger.info("Continuing without Graphiti ingestion")

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            logger.exception("mongodb_connection_failed", error=str(e))
            raise

        self._initialized = True
        logger.info("Ingestion pipeline initialized")

    async def close(self) -> None:
        """Close MongoDB and Graphiti connections."""
        if self._initialized:
            if self.mongo_client:
                await self.mongo_client.close()
                self.mongo_client = None
                self.db = None
                logger.info("MongoDB connection closed")

            if self.graphiti_deps:
                await self.graphiti_deps.cleanup()
                self.graphiti_adapter = None
                self.graphiti_deps = None

            self._initialized = False

    def _find_document_files(self) -> list[str]:
        """
        Find all supported document files in the documents folder.

        Returns:
            List of file paths
        """
        if not os.path.exists(self.documents_folder):
            logger.error(f"Documents folder not found: {self.documents_folder}")
            return []

        # Supported file patterns - Docling + text formats + audio
        patterns = [
            "*.md",
            "*.markdown",
            "*.txt",  # Text formats
            "*.pdf",  # PDF
            "*.docx",
            "*.doc",  # Word
            "*.pptx",
            "*.ppt",  # PowerPoint
            "*.xlsx",
            "*.xls",  # Excel
            "*.html",
            "*.htm",  # HTML
            "*.mp3",
            "*.wav",
            "*.m4a",
            "*.flac",  # Audio formats
        ]
        files = []

        for pattern in patterns:
            files.extend(
                glob.glob(os.path.join(self.documents_folder, "**", pattern), recursive=True)
            )

        return sorted(files)

    def _read_document(self, file_path: str) -> tuple[str, Any | None]:
        """
        Read document content from file - supports multiple formats via Docling.

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (markdown_content, docling_document).
            docling_document is None only for text files.
        """
        file_ext = os.path.splitext(file_path)[1].lower()

        # Audio formats - transcribe with Whisper ASR
        audio_formats = [".mp3", ".wav", ".m4a", ".flac"]
        if file_ext in audio_formats:
            # Returns tuple: (markdown_content, docling_document)
            return self._transcribe_audio(file_path)

        # Docling-supported formats (convert to markdown)
        docling_formats = [
            ".pdf",
            ".docx",
            ".doc",
            ".pptx",
            ".ppt",
            ".xlsx",
            ".xls",
            ".html",
            ".htm",
            ".md",
            ".markdown",  # Markdown files for HybridChunker
        ]

        if file_ext in docling_formats:
            from docling.document_converter import DocumentConverter

            logger.info(f"Converting {file_ext} file using Docling: {os.path.basename(file_path)}")

            converter = DocumentConverter()
            result = converter.convert(file_path)

            # Export to markdown for consistent processing
            markdown_content = result.document.export_to_markdown()
            logger.info(f"Successfully converted {os.path.basename(file_path)} to markdown")

            # Return both markdown and DoclingDocument for HybridChunker
            return (markdown_content, result.document)

        # Text-based formats (read directly)
        file_path_obj = Path(file_path)
        try:
            with file_path_obj.open(encoding="utf-8") as f:
                return (f.read(), None)
        except UnicodeDecodeError:
            # Try with different encoding
            with file_path_obj.open(encoding="latin-1") as f:
                return (f.read(), None)

    def _transcribe_audio(self, file_path: str) -> tuple[str, Any | None]:
        """
        Transcribe audio file using Whisper ASR via Docling.

        Args:
            file_path: Path to the audio file

        Returns:
            Tuple of (markdown_content, docling_document)
        """
        try:
            from pathlib import Path

            from docling.datamodel import asr_model_specs
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import AsrPipelineOptions
            from docling.document_converter import AudioFormatOption, DocumentConverter
            from docling.pipeline.asr_pipeline import AsrPipeline

            # Use Path object - Docling expects this
            audio_path = Path(file_path).resolve()
            logger.info(f"Transcribing audio file using Whisper Turbo: {audio_path.name}")

            # Verify file exists
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Configure ASR pipeline with Whisper Turbo model
            pipeline_options = AsrPipelineOptions()
            pipeline_options.asr_options = asr_model_specs.WHISPER_TURBO

            converter = DocumentConverter(
                format_options={
                    InputFormat.AUDIO: AudioFormatOption(
                        pipeline_cls=AsrPipeline,
                        pipeline_options=pipeline_options,
                    )
                }
            )

            # Transcribe the audio file
            result = converter.convert(audio_path)

            # Export to markdown with timestamps
            markdown_content = result.document.export_to_markdown()
            logger.info(f"Successfully transcribed {os.path.basename(file_path)}")

            # Return both markdown and DoclingDocument for HybridChunker
            return (markdown_content, result.document)

        except Exception:
            logger.exception("Failed to transcribe {file_path} with Whisper ASR")
            return (
                f"[Error: Could not transcribe audio file {os.path.basename(file_path)}]",
                None,
            )

    def _extract_title(self, content: str, file_path: str) -> str:
        """
        Extract title from document content or filename.

        Args:
            content: Document content
            file_path: Path to the document file

        Returns:
            Document title
        """
        # Try to find markdown title
        lines = content.split("\n")
        for raw_line in lines[:10]:  # Check first 10 lines
            line = raw_line.strip()
            if line.startswith("# "):
                return line[2:].strip()

        # Fallback to filename
        return os.path.splitext(os.path.basename(file_path))[0]

    def _extract_document_metadata(self, content: str, file_path: str) -> dict[str, Any]:
        """
        Extract metadata from document content.

        Args:
            content: Document content
            file_path: Path to the document file

        Returns:
            Document metadata dictionary
        """
        metadata = {
            "file_path": file_path,
            "file_size": len(content),
            "ingestion_date": datetime.now().isoformat(),
        }

        # Try to extract YAML frontmatter
        if content.startswith("---"):
            try:
                import yaml

                end_marker = content.find("\n---\n", 4)
                if end_marker != -1:
                    frontmatter = content[4:end_marker]
                    yaml_metadata = yaml.safe_load(frontmatter)
                    if isinstance(yaml_metadata, dict):
                        metadata.update(yaml_metadata)
            except Exception as e:
                logger.warning(f"Failed to parse frontmatter: {e}")

        # Extract some basic metadata from content
        lines = content.split("\n")
        metadata["line_count"] = len(lines)
        metadata["word_count"] = len(content.split())

        return metadata

    async def _save_to_mongodb(
        self,
        title: str,
        source: str,
        content: str,
        chunks: list[DocumentChunk],
        metadata: dict[str, Any],
    ) -> str:
        """
        Save document and chunks to MongoDB.

        Args:
            title: Document title
            source: Document source path
            content: Document content
            chunks: List of document chunks with embeddings
            metadata: Document metadata

        Returns:
            Document ID (ObjectId as string)

        Raises:
            Exception: If MongoDB operations fail
        """
        # Get collection references
        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Insert document with RLS fields
        document_dict = {
            "title": title,
            "source": source,
            "content": content,
            "metadata": metadata,
            "created_at": datetime.now(),
            # RLS fields
            "user_id": self.user_id or None,
            "user_email": self.user_email or None,
            "is_public": False,  # Default to private
            "shared_with": [],
            "group_ids": [],
        }

        document_result = await documents_collection.insert_one(document_dict)
        document_id = document_result.inserted_id

        logger.info(f"Inserted document with ID: {document_id}")

        # Insert chunks with embeddings as Python lists
        chunk_dicts = []
        for chunk in chunks:
            chunk_dict = {
                "document_id": document_id,
                "content": chunk.content,
                "embedding": chunk.embedding,  # Python list, NOT string!
                "chunk_index": chunk.index,
                "metadata": chunk.metadata,
                "token_count": chunk.token_count,
                "created_at": datetime.now(),
            }
            chunk_dicts.append(chunk_dict)

        # Batch insert with ordered=False for partial success
        if chunk_dicts:
            await chunks_collection.insert_many(chunk_dicts, ordered=False)
            logger.info(f"Inserted {len(chunk_dicts)} chunks")

        return str(document_id)

    async def _clean_databases(self) -> None:
        """Clean existing data from MongoDB collections."""
        logger.warning("Cleaning existing data from MongoDB...")

        # Get collection references
        documents_collection = self.db[self.settings.mongodb_collection_documents]
        chunks_collection = self.db[self.settings.mongodb_collection_chunks]

        # Delete all chunks first (to respect FK relationships)
        chunks_result = await chunks_collection.delete_many({})
        logger.info(f"Deleted {chunks_result.deleted_count} chunks")

        # Delete all documents
        docs_result = await documents_collection.delete_many({})
        logger.info(f"Deleted {docs_result.deleted_count} documents")

    async def _ingest_single_document(self, file_path: str) -> IngestionResult:
        """
        Ingest a single document.

        Args:
            file_path: Path to the document file

        Returns:
            Ingestion result
        """
        start_time = datetime.now()

        # Read document (returns tuple: content, docling_doc)
        document_content, docling_doc = self._read_document(file_path)
        document_title = self._extract_title(document_content, file_path)
        document_source = os.path.relpath(file_path, self.documents_folder)

        # Extract metadata from content
        document_metadata = self._extract_document_metadata(document_content, file_path)

        logger.info(f"Processing document: {document_title}")

        # Chunk the document - pass DoclingDocument for HybridChunker
        chunks = await self.chunker.chunk_document(
            content=document_content,
            title=document_title,
            source=document_source,
            metadata=document_metadata,
            docling_doc=docling_doc,  # Pass DoclingDocument for HybridChunker
        )

        if not chunks:
            logger.warning(f"No chunks created for {document_title}")
            return IngestionResult(
                document_id="",
                title=document_title,
                chunks_created=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                errors=["No chunks created"],
            )

        logger.info(f"Created {len(chunks)} chunks")

        # Generate embeddings
        embedded_chunks = await self.embedder.embed_chunks(chunks)
        logger.info(f"Generated embeddings for {len(embedded_chunks)} chunks")

        # Save to MongoDB
        document_id = await self._save_to_mongodb(
            document_title, document_source, document_content, embedded_chunks, document_metadata
        )

        logger.info(f"Saved document to MongoDB with ID: {document_id}")

        # Ingest into Graphiti if enabled
        graphiti_errors = []
        if self.graphiti_adapter:
            try:
                graphiti_result = await self.graphiti_adapter.ingest_document(
                    document_id=document_id,
                    chunks=embedded_chunks,
                    metadata=document_metadata,
                    title=document_title,
                    source=document_source,
                )
                if graphiti_result.get("errors"):
                    graphiti_errors.extend(graphiti_result["errors"])
                logger.info(
                    f"Graphiti ingestion: {graphiti_result.get('facts_added', 0)} facts "
                    f"from {graphiti_result.get('chunks_processed', 0)} chunks"
                )
            except Exception as e:
                error_msg = f"Graphiti ingestion failed: {e!s}"
                logger.exception(error_msg)
                graphiti_errors.append(error_msg)

        # Extract and store code examples if enabled
        code_errors = []
        if self.settings.use_agentic_rag:
            try:
                code_result = await ingest_code_examples(
                    self.mongo_client,
                    document_id,
                    document_content,
                    document_source,
                    document_metadata,
                )
                if code_result.get("errors"):
                    code_errors.extend(code_result["errors"])
                logger.info(
                    f"Code examples: {code_result.get('code_examples_stored', 0)} stored "
                    f"from {code_result.get('code_examples_extracted', 0)} extracted"
                )
            except Exception as e:
                error_msg = f"Code example extraction failed: {e!s}"
                logger.exception(error_msg)
                code_errors.append(error_msg)

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds() * 1000

        # Combine errors from MongoDB, Graphiti, and code extraction
        all_errors = graphiti_errors + code_errors  # MongoDB errors would be added here if any

        return IngestionResult(
            document_id=document_id,
            title=document_title,
            chunks_created=len(chunks),
            processing_time_ms=processing_time,
            errors=all_errors,
        )

    async def ingest_documents(
        self, progress_callback: Callable | None = None
    ) -> list[IngestionResult]:
        """
        Ingest all documents from the documents folder.

        Args:
            progress_callback: Optional callback for progress updates

        Returns:
            List of ingestion results
        """
        if not self._initialized:
            await self.initialize()

        # Clean existing data if requested
        if self.clean_before_ingest:
            await self._clean_databases()

        # Find all supported document files
        document_files = self._find_document_files()

        if not document_files:
            logger.warning(f"No supported document files found in {self.documents_folder}")
            return []

        logger.info(f"Found {len(document_files)} document files to process")

        results = []

        for i, file_path in enumerate(document_files):
            try:
                logger.info(f"Processing file {i + 1}/{len(document_files)}: {file_path}")

                result = await self._ingest_single_document(file_path)
                results.append(result)

                if progress_callback:
                    progress_callback(i + 1, len(document_files))

            except Exception as e:
                logger.exception("Failed to process {file_path}")
                results.append(
                    IngestionResult(
                        document_id="",
                        title=os.path.basename(file_path),
                        chunks_created=0,
                        processing_time_ms=0,
                        errors=[str(e)],
                    )
                )

        # Log summary
        total_chunks = sum(r.chunks_created for r in results)
        total_errors = sum(len(r.errors) for r in results)

        logger.info(
            f"Ingestion complete: {len(results)} documents, "
            f"{total_chunks} chunks, {total_errors} errors"
        )

        return results


async def main() -> None:
    """Main function for running ingestion."""
    parser = argparse.ArgumentParser(description="Ingest documents into MongoDB vector database")
    parser.add_argument("--documents", "-d", default="documents", help="Documents folder path")
    parser.add_argument(
        "--no-clean", action="store_true", help="Skip cleaning existing data before ingestion"
    )
    parser.add_argument(
        "--chunk-size", type=int, default=1000, help="Chunk size for splitting documents"
    )
    parser.add_argument("--chunk-overlap", type=int, default=200, help="Chunk overlap size")
    parser.add_argument(
        "--max-tokens", type=int, default=512, help="Maximum tokens per chunk for embeddings"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create ingestion configuration
    config = IngestionConfig(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        max_chunk_size=args.chunk_size * 2,
        max_tokens=args.max_tokens,
    )

    # Create and run pipeline - clean by default unless --no-clean is specified
    pipeline = DocumentIngestionPipeline(
        config=config,
        documents_folder=args.documents,
        clean_before_ingest=not args.no_clean,  # Clean by default
    )

    def progress_callback(current: int, total: int) -> None:
        print(f"Progress: {current}/{total} documents processed")

    try:
        start_time = datetime.now()

        results = await pipeline.ingest_documents(progress_callback)

        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()

        # Print summary
        print("\n" + "=" * 50)
        print("INGESTION SUMMARY")
        print("=" * 50)
        print(f"Documents processed: {len(results)}")
        print(f"Total chunks created: {sum(r.chunks_created for r in results)}")
        print(f"Total errors: {sum(len(r.errors) for r in results)}")
        print(f"Total processing time: {total_time:.2f} seconds")
        print()

        # Print individual results
        for result in results:
            status = "[OK]" if not result.errors else "[FAILED]"
            print(f"{status} {result.title}: {result.chunks_created} chunks")

            if result.errors:
                for error in result.errors:
                    print(f"  Error: {error}")

        # Print next steps
        print("\n" + "=" * 50)
        print("NEXT STEPS")
        print("=" * 50)
        print("1. Create vector search index in Atlas UI:")
        print("   - Index name: vector_index")
        print("   - Collection: chunks")
        print("   - Field: embedding")
        print("   - Dimensions: 1536 (for text-embedding-3-small)")
        print()
        print("2. Create text search index in Atlas UI:")
        print("   - Index name: text_index")
        print("   - Collection: chunks")
        print("   - Field: content")
        print()
        print("See .claude/reference/mongodb-patterns.md for detailed instructions")

    except KeyboardInterrupt:
        print("\nIngestion interrupted by user")
    except Exception:
        logger.exception("Ingestion failed")
        raise
    finally:
        await pipeline.close()


if __name__ == "__main__":
    asyncio.run(main())
