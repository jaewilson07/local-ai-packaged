#!/usr/bin/env python3
"""Direct script to crawl a website using crawl4ai-rag."""

import asyncio
import sys
import os

# Add /app to path so imports work
sys.path.insert(0, '/app')

from server.projects.crawl4ai_rag.models import CrawlDeepRequest
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.services.crawler import crawl_deep
from server.projects.crawl4ai_rag.ingestion.adapter import CrawledContentIngester


async def main():
    """Crawl a website and ingest into MongoDB."""
    if len(sys.argv) < 2:
        print("Usage: python crawl_website.py <url> [max_depth] [allowed_domains]")
        print("Example: python crawl_website.py https://www.bluesmuse.dance/ 3")
        sys.exit(1)
    
    url = sys.argv[1]
    max_depth = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    allowed_domains = sys.argv[3].split(',') if len(sys.argv) > 3 else None
    
    print(f"Starting deep crawl of {url} with max_depth={max_depth}")
    if allowed_domains:
        print(f"Allowed domains: {allowed_domains}")
    
    deps = Crawl4AIDependencies()
    await deps.initialize()
    
    try:
        # Perform deep crawl
        crawled_pages = await crawl_deep(
            crawler=deps.crawler,
            start_url=url,
            max_depth=max_depth,
            allowed_domains=allowed_domains,
            allowed_subdomains=None,
            max_concurrent=10
        )
        
        if not crawled_pages:
            print("❌ No pages were crawled")
            return
        
        print(f"✓ Crawled {len(crawled_pages)} pages")
        
        # Ingest all crawled pages
        ingester = CrawledContentIngester(
            mongo_client=deps.mongo_client,
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Initialize Graphiti if enabled
        await ingester.initialize()
        
        ingestion_results = await ingester.ingest_crawled_batch(
            pages=crawled_pages,
            chunk_size=1000,
            chunk_overlap=200
        )
        
        # Aggregate results
        total_chunks = sum(r.chunks_created for r in ingestion_results)
        document_ids = [r.document_id for r in ingestion_results if r.document_id]
        all_errors = []
        for i, r in enumerate(ingestion_results):
            all_errors.extend(r.errors)
            if r.document_id:
                page_url = crawled_pages[i].get('url', 'unknown') if i < len(crawled_pages) else 'unknown'
                print(f"  ✓ Ingested: {page_url} ({r.chunks_created} chunks)")
            else:
                page_url = crawled_pages[i].get('url', 'unknown') if i < len(crawled_pages) else 'unknown'
                print(f"  ✗ Failed to ingest: {page_url}")
                if r.errors:
                    for error in r.errors:
                        print(f"     Error: {error}")
        
        print(f"\n✅ Crawl complete!")
        print(f"   Pages crawled: {len(crawled_pages)}")
        print(f"   Chunks created: {total_chunks}")
        print(f"   Documents created: {len(document_ids)}")
        if all_errors:
            print(f"   Errors: {len(all_errors)}")
            for error in all_errors[:5]:  # Show first 5 errors
                print(f"     - {error}")
    
    finally:
        await deps.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

