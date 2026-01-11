#!/usr/bin/env python3
"""Crawl Blues Muse website and validate MongoDB RAG ingestion (Direct Python).

This script performs:
1. Shallow 1-page scrape of https://www.bluesmuse.dance/
2. Deep scrape of the site (depth 2)
3. Validates content is ingested into MongoDB RAG

Uses direct Python imports instead of REST API.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add server to path
project_root = Path(__file__).parent.parent.parent
lambda_path = project_root / "04-lambda"
sys.path.insert(0, str(lambda_path))

from pydantic_ai import RunContext
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.tools import crawl_and_ingest_single_page, crawl_and_ingest_deep
from server.projects.mongo_rag.search import search_knowledge_base
import logging

# Configuration
BLUES_MUSE_URL = "https://www.bluesmuse.dance/"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
MAX_DEPTH = 2  # Shallow deep crawl to avoid timeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def crawl_single_page_direct(url: str, deps: Crawl4AIDependencies) -> Dict[str, Any]:
    """Crawl a single page and ingest into MongoDB RAG (direct)."""
    print(f"\n{'='*80}")
    print("SHALLOW CRAWL: Single Page")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print()
    
    try:
        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        
        print("📡 Starting crawl and ingestion...")
        result = await crawl_and_ingest_single_page(
            ctx=ctx,
            url=url,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )
        
        print("✅ Single page crawl successful!")
        print(f"\nResults:")
        print(f"  - Success: {result.get('success', False)}")
        print(f"  - Pages crawled: {result.get('pages_crawled', 0)}")
        print(f"  - Chunks created: {result.get('chunks_created', 0)}")
        print(f"  - Document ID: {result.get('document_id', 'N/A')}")
        
        if result.get('errors'):
            print(f"  - Errors: {len(result['errors'])}")
            for error in result['errors'][:3]:
                print(f"    • {error}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during single page crawl: {e}")
        logger.exception("Error details:")
        return {"success": False, "error": str(e)}


async def crawl_deep_direct(url: str, max_depth: int, deps: Crawl4AIDependencies) -> Dict[str, Any]:
    """Perform deep crawl and ingest into MongoDB RAG (direct)."""
    print(f"\n{'='*80}")
    print("DEEP CRAWL: Recursive")
    print(f"{'='*80}")
    print(f"URL: {url}")
    print(f"Max depth: {max_depth}")
    print(f"Chunk size: {CHUNK_SIZE}, Overlap: {CHUNK_OVERLAP}")
    print()
    
    try:
        ctx = RunContext(deps=deps, state={}, agent=None, run_id="")
        
        print("📡 Starting deep crawl and ingestion...")
        result = await crawl_and_ingest_deep(
            ctx=ctx,
            start_url=url,
            max_depth=max_depth,
            allowed_domains=["bluesmuse.dance", "www.bluesmuse.dance"],
            allowed_subdomains=None,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
            max_concurrent=10
        )
        
        print("✅ Deep crawl successful!")
        print(f"\nResults:")
        print(f"  - Success: {result.get('success', False)}")
        print(f"  - Pages crawled: {result.get('pages_crawled', 0)}")
        print(f"  - Chunks created: {result.get('chunks_created', 0)}")
        print(f"  - Documents created: {len(result.get('document_ids', []))}")
        
        if result.get('errors'):
            print(f"  - Errors: {len(result['errors'])}")
            for error in result['errors'][:5]:
                print(f"    • {error}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during deep crawl: {e}")
        logger.exception("Error details:")
        return {"success": False, "error": str(e)}


async def validate_mongodb_ingestion_direct(search_query: str, deps: Crawl4AIDependencies) -> Dict[str, Any]:
    """Validate that crawled content is searchable in MongoDB RAG (direct)."""
    print(f"\n{'='*80}")
    print("VALIDATION: MongoDB RAG Search")
    print(f"{'='*80}")
    print(f"Search query: '{search_query}'")
    print()
    
    try:
        from server.projects.mongo_rag.dependencies import AgentDependencies
        
        # Create agent dependencies for search
        agent_deps = AgentDependencies()
        await agent_deps.initialize()
        
        try:
            print("📡 Searching MongoDB RAG...")
            results = await search_knowledge_base(
                deps=agent_deps,
                query=search_query,
                search_type="hybrid",
                match_count=10
            )
            
            matches = results.get('results', [])
            print(f"✅ Found {len(matches)} matches")
            
            if matches:
                print(f"\nTop {min(3, len(matches))} results:")
                for i, match in enumerate(matches[:3], 1):
                    score = match.get('score', 0)
                    source = match.get('source', 'Unknown')
                    text_preview = match.get('text', '')[:150]
                    print(f"\n  {i}. Score: {score:.4f}")
                    print(f"     Source: {source}")
                    print(f"     Preview: {text_preview}...")
            
            return {
                "success": True,
                "matches": len(matches),
                "results": matches
            }
        finally:
            await agent_deps.cleanup()
            
    except Exception as e:
        print(f"❌ Error during validation: {e}")
        logger.exception("Error details:")
        return {"success": False, "error": str(e)}


async def main():
    """Main execution."""
    from datetime import datetime
    
    print("="*80)
    print("BLUES MUSE CRAWL & RAG VALIDATION (Direct Python)")
    print("="*80)
    print(f"Target URL: {BLUES_MUSE_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Initialize dependencies
    print("🔧 Initializing dependencies...")
    deps = Crawl4AIDependencies()
    await deps.initialize()
    print("✅ Dependencies initialized")
    
    try:
        # Step 1: Shallow crawl (single page)
        single_result = await crawl_single_page_direct(BLUES_MUSE_URL, deps)
        
        if not single_result.get('success'):
            print("\n⚠️  Single page crawl failed, but continuing with deep crawl...")
        
        # Wait a bit between crawls
        await asyncio.sleep(2)
        
        # Step 2: Deep crawl
        deep_result = await crawl_deep_direct(BLUES_MUSE_URL, MAX_DEPTH, deps)
        
        if not deep_result.get('success'):
            print("\n⚠️  Deep crawl failed")
        
        # Wait a bit for ingestion to complete
        await asyncio.sleep(3)
        
        # Step 3: Validate MongoDB RAG ingestion
        validation_result = await validate_mongodb_ingestion_direct("Blues Muse", deps)
        
        # Summary
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        print(f"Single page crawl: {'✅ Success' if single_result.get('success') else '❌ Failed'}")
        if single_result.get('success'):
            print(f"  - Chunks: {single_result.get('chunks_created', 0)}")
        
        print(f"Deep crawl: {'✅ Success' if deep_result.get('success') else '❌ Failed'}")
        if deep_result.get('success'):
            print(f"  - Pages: {deep_result.get('pages_crawled', 0)}")
            print(f"  - Chunks: {deep_result.get('chunks_created', 0)}")
        
        print(f"MongoDB RAG validation: {'✅ Success' if validation_result.get('success') else '❌ Failed'}")
        if validation_result.get('success'):
            print(f"  - Matches found: {validation_result.get('matches', 0)}")
        
        print(f"\n{'='*80}")
        
        # Exit code
        if single_result.get('success') and deep_result.get('success') and validation_result.get('success'):
            print("✅ All operations completed successfully!")
            sys.exit(0)
        else:
            print("⚠️  Some operations failed. Check output above for details.")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        await deps.cleanup()
        logger.info("🧹 Dependencies cleaned up")


if __name__ == "__main__":
    asyncio.run(main())
