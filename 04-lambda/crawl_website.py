#!/usr/bin/env python3
"""Direct script to crawl a website using crawl4ai-rag."""

import asyncio
import sys
import os

# Add server to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'server'))

from server.projects.crawl4ai_rag.models import CrawlDeepRequest
from server.projects.crawl4ai_rag.dependencies import Crawl4AIDependencies
from server.projects.crawl4ai_rag.crawler import crawl_deep
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
        ingester = CrawledContentIngester()
        total_chunks = 0
        document_ids = []
        errors = []
        
        for page_data in crawled_pages:
            try:
                result = await ingester.ingest(
                    url=page_data['url'],
                    markdown=page_data['markdown'],
                    chunk_size=1000,
                    chunk_overlap=200,
                    crawl_metadata=page_data.get('metadata')
                )
                
                if result:
                    total_chunks += result.get('chunks_created', 0)
                    if result.get('document_id'):
                        document_ids.append(result['document_id'])
                    print(f"  ✓ Ingested: {page_data['url']} ({result.get('chunks_created', 0)} chunks)")
                else:
                    errors.append(f"Failed to ingest {page_data['url']}")
                    print(f"  ✗ Failed to ingest: {page_data['url']}")
            except Exception as e:
                error_msg = f"Error ingesting {page_data['url']}: {str(e)}"
                errors.append(error_msg)
                print(f"  ✗ {error_msg}")
        
        print(f"\n✅ Crawl complete!")
        print(f"   Pages crawled: {len(crawled_pages)}")
        print(f"   Chunks created: {total_chunks}")
        print(f"   Documents created: {len(document_ids)}")
        if errors:
            print(f"   Errors: {len(errors)}")
            for error in errors[:5]:  # Show first 5 errors
                print(f"     - {error}")
    
    finally:
        await deps.cleanup()


if __name__ == "__main__":
    asyncio.run(main())


