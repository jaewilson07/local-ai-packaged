#!/usr/bin/env python3
"""Deep crawl example using Crawl4AI RAG.

This example demonstrates how to perform a deep crawl of a website,
following internal links recursively up to a specified depth, and
automatically ingesting all discovered pages into MongoDB RAG.

Deep crawling is useful for:
- Building knowledge bases from documentation sites
- Indexing entire websites for search
- Discovering and ingesting related content automatically

Prerequisites:
- MongoDB running
- Environment variables configured (MONGODB_URI, LLM_BASE_URL, EMBEDDING_BASE_URL, etc.)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add server to path so we can import from the project
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from pydantic_ai import RunContext
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_deep
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Perform deep crawl of a website."""
    # Configuration
    url = "https://www.bluesmuse.dance/"  # Example website
    max_depth = 3  # Crawl up to 3 levels deep
    chunk_size = 1000
    chunk_overlap = 200
    max_concurrent = 10  # Maximum concurrent browser sessions
    
    # Domain filtering (optional)
    # allowed_domains = ["bluesmuse.dance"]  # Only crawl this domain
    # allowed_subdomains = ["www", "docs"]  # Only crawl these subdomains
    allowed_domains = None  # Allow all domains from starting URL
    allowed_subdomains = None  # Allow all subdomains
    
    print("="*80)
    print("Crawl4AI RAG - Deep Crawl Example")
    print("="*80)
    print()
    print("This example demonstrates deep crawling of a website.")
    print("Deep crawling:")
    print("  - Follows internal links recursively")
    print("  - Respects depth limits to control scope")
    print("  - Can filter by domain and subdomain")
    print("  - Automatically ingests all discovered pages")
    print()
    print(f"Configuration:")
    print(f"  Starting URL: {url}")
    print(f"  Max depth: {max_depth}")
    print(f"  Chunk size: {chunk_size}")
    print(f"  Chunk overlap: {chunk_overlap}")
    print(f"  Max concurrent: {max_concurrent}")
    if allowed_domains:
        print(f"  Allowed domains: {allowed_domains}")
    if allowed_subdomains:
        print(f"  Allowed subdomains: {allowed_subdomains}")
    print()
    
    # Initialize dependencies
    deps = Crawl4AIDependencies()
    await deps.initialize()
    
    try:
        # Create run context
        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        
        # Perform deep crawl and ingestion
        logger.info(f"🚀 Starting deep crawl of {url}")
        result = await crawl_and_ingest_deep(
            ctx=ctx,
            start_url=url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=allowed_subdomains,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_concurrent=max_concurrent
        )
        
        # Display results
        print("\n" + "="*80)
        print("CRAWL RESULTS")
        print("="*80)
        print(f"Success: {result['success']}")
        print(f"Starting URL: {result['url']}")
        print(f"Pages Crawled: {result['pages_crawled']}")
        print(f"Chunks Created: {result['chunks_created']}")
        print(f"Documents Created: {len(result['document_ids'])}")
        
        if result['document_ids']:
            print(f"\nFirst 10 Document IDs:")
            for doc_id in result['document_ids'][:10]:
                print(f"  - {doc_id}")
            if len(result['document_ids']) > 10:
                print(f"  ... and {len(result['document_ids']) - 10} more")
        
        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result['errors'][:10]:
                print(f"  - {error}")
            if len(result['errors']) > 10:
                print(f"  ... and {len(result['errors']) - 10} more errors")
        else:
            print("\n✅ No errors!")
        
        print("\n" + "="*80)
        print("NOTE: If Graphiti is enabled (USE_GRAPHITI=true),")
        print("      all crawled content has also been ingested into Graphiti!")
        print("="*80)
        
        if result['success']:
            print("\n✅ Deep crawl completed successfully!")
            print()
            print("All crawled pages are now searchable via MongoDB RAG.")
            print("Run semantic_search_example.py or hybrid_search_example.py to test.")
            sys.exit(0)
        else:
            print("\n⚠️  Deep crawl completed with errors")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"❌ Error during deep crawl: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
