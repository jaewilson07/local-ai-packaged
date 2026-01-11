"""Core crawling logic for Crawl4AI RAG."""

import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urlparse, urljoin, urldefrag
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, MemoryAdaptiveDispatcher

logger = logging.getLogger(__name__)


def normalize_url(url: str) -> str:
    """
    Normalize URL by removing fragment and trailing slash.
    
    Args:
        url: URL to normalize
        
    Returns:
        Normalized URL
    """
    url, _ = urldefrag(url)
    return url.rstrip('/')


def is_allowed_domain(url: str, allowed_domains: Optional[List[str]], base_domain: str) -> bool:
    """
    Check if URL's domain is allowed.
    
    Args:
        url: URL to check
        allowed_domains: List of allowed domains (exact match)
        base_domain: Base domain from starting URL
        
    Returns:
        True if domain is allowed
    """
    if allowed_domains is None:
        # If no whitelist, allow same domain as base
        parsed = urlparse(url)
        return parsed.netloc == base_domain or parsed.netloc.endswith(f'.{base_domain}')
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Check exact match
    if domain in [d.lower() for d in allowed_domains]:
        return True
    
    # Check if it's a subdomain of an allowed domain
    for allowed in allowed_domains:
        if domain.endswith(f'.{allowed.lower()}'):
            return True
    
    return False


def is_allowed_subdomain(url: str, allowed_subdomains: Optional[List[str]]) -> bool:
    """
    Check if URL's subdomain is allowed.
    
    Args:
        url: URL to check
        allowed_subdomains: List of allowed subdomain prefixes
        
    Returns:
        True if subdomain is allowed (or no filter specified)
    """
    if allowed_subdomains is None:
        return True
    
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    
    # Extract subdomain (everything before the main domain)
    parts = netloc.split('.')
    if len(parts) < 2:
        return True  # No subdomain
    
    # Check if any subdomain prefix matches
    for allowed in allowed_subdomains:
        allowed_lower = allowed.lower()
        # Check if netloc starts with allowed subdomain
        if netloc.startswith(allowed_lower) or netloc.endswith(f'.{allowed_lower}'):
            return True
        # Check if any part matches
        for part in parts:
            if part.startswith(allowed_lower):
                return True
    
    return False


def extract_base_domain(url: str) -> str:
    """
    Extract base domain from URL.
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Base domain (e.g., 'example.com')
    """
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    
    # Remove port if present
    if ':' in netloc:
        netloc = netloc.split(':')[0]
    
    # Extract base domain (last two parts)
    parts = netloc.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return netloc


def extract_crawl_metadata(result: Any, url: str, depth: Optional[int] = None, parent_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract metadata from crawl4ai result object.
    
    Args:
        result: Crawl4AI CrawlerResult object
        url: The crawled URL
        depth: Crawl depth (for deep crawls)
        parent_url: Parent URL that led to this page (for deep crawls)
        
    Returns:
        Dictionary with extracted metadata
    """
    metadata = {
        'crawl_timestamp': datetime.now().isoformat(),
        'url': url,
    }
    
    # Page metadata from result.metadata
    if hasattr(result, 'metadata') and result.metadata:
        page_meta = result.metadata
        if isinstance(page_meta, dict):
            # Extract common page metadata
            if 'title' in page_meta:
                metadata['page_title'] = page_meta['title']
            if 'description' in page_meta:
                metadata['page_description'] = page_meta['description']
            if 'language' in page_meta:
                metadata['page_language'] = page_meta['language']
            if 'keywords' in page_meta:
                metadata['page_keywords'] = page_meta['keywords']
            if 'author' in page_meta:
                metadata['page_author'] = page_meta['author']
            if 'og:title' in page_meta:
                metadata['og_title'] = page_meta['og:title']
            if 'og:description' in page_meta:
                metadata['og_description'] = page_meta['og:description']
            if 'og:image' in page_meta:
                metadata['og_image'] = page_meta['og:image']
    
    # Content metadata - images
    if hasattr(result, 'images') and result.images:
        metadata['images'] = result.images if isinstance(result.images, list) else []
        metadata['image_count'] = len(metadata['images'])
    
    # Content metadata - media
    if hasattr(result, 'media') and result.media:
        metadata['media'] = result.media if isinstance(result.media, list) else []
        metadata['media_count'] = len(metadata['media'])
    
    # Structured data (JSON-LD, microdata, etc.)
    if hasattr(result, 'json') and result.json:
        metadata['structured_data'] = result.json
    
    # Links metadata (already captured separately, but add counts)
    if hasattr(result, 'links') and result.links:
        links = result.links
        if isinstance(links, dict):
            metadata['link_counts'] = {
                'internal': len(links.get('internal', [])),
                'external': len(links.get('external', [])),
                'total': len(links.get('internal', [])) + len(links.get('external', []))
            }
    
    # Crawl metadata
    if depth is not None:
        metadata['crawl_depth'] = depth
    if parent_url:
        metadata['parent_url'] = parent_url
    
    return metadata


async def crawl_single_page(
    crawler: AsyncWebCrawler,
    url: str
) -> Dict[str, Any]:
    """
    Crawl a single web page.
    
    Args:
        crawler: AsyncWebCrawler instance
        url: URL to crawl
        
    Returns:
        Dictionary with 'url', 'markdown', 'links', and 'metadata' keys, or None if failed
    """
    try:
        # Optimized config for faster crawling
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=False,
            wait_until="domcontentloaded",  # Don't wait for all network activity
            page_timeout=30000,  # 30 second timeout per page
            wait_for_images=False,  # Don't wait for images to load
            exclude_external_links=True,  # Skip external links processing
            exclude_external_images=True,  # Skip external images
            word_count_threshold=50,  # Skip pages with very little content
            remove_overlay_elements=True,  # Auto-remove popups/modals
            magic=True  # Auto-handle common patterns
        )
        result = await crawler.arun(url=url, config=run_config)
        
        if result.success and result.markdown:
            # Extract metadata from crawl result
            crawl_metadata = extract_crawl_metadata(result, url)
            
            # Get HTML content (prefer cleaned_html, fallback to html)
            html_content = None
            if hasattr(result, 'cleaned_html') and result.cleaned_html:
                html_content = result.cleaned_html
            elif hasattr(result, 'html') and result.html:
                html_content = result.html
            
            return {
                'url': url,
                'markdown': result.markdown,
                'html': html_content,  # Store original HTML
                'links': result.links or {},
                'metadata': crawl_metadata
            }
        else:
            logger.warning(f"Failed to crawl {url}: {result.error_message}")
            return None
    except Exception as e:
        logger.exception(f"Error crawling {url}: {e}")
        return None


async def crawl_deep(
    crawler: AsyncWebCrawler,
    start_url: str,
    max_depth: int,
    allowed_domains: Optional[List[str]] = None,
    allowed_subdomains: Optional[List[str]] = None,
    max_concurrent: int = 10
) -> List[Dict[str, Any]]:
    """
    Recursively crawl a website with depth control and domain filtering.
    
    Args:
        crawler: AsyncWebCrawler instance
        start_url: Starting URL for crawl
        max_depth: Maximum crawl depth
        allowed_domains: List of allowed domains (exact match)
        allowed_subdomains: List of allowed subdomain prefixes
        max_concurrent: Maximum concurrent browser sessions
        
    Returns:
        List of dictionaries with 'url' and 'markdown' keys
    """
    # Extract base domain for filtering
    base_domain = extract_base_domain(start_url)
    
    # Normalize starting URL
    start_url_normalized = normalize_url(start_url)
    
    visited: Set[str] = set()
    results: List[Dict[str, Any]] = []
    # Track URL -> parent URL mapping for metadata
    url_to_parent: Dict[str, str] = {}
    current_level_urls: Set[str] = {start_url_normalized}
    
    crawl_start_time = datetime.now()
    
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=70.0,
        check_interval=1.0,
        max_session_permit=max_concurrent
    )
    
    for depth in range(max_depth):
        if not current_level_urls:
            break
        
        # Filter URLs by domain/subdomain
        urls_to_crawl = []
        for url in current_level_urls:
            if url in visited:
                continue
            
            # Check domain filter
            if not is_allowed_domain(url, allowed_domains, base_domain):
                continue
            
            # Check subdomain filter
            if not is_allowed_subdomain(url, allowed_subdomains):
                continue
            
            urls_to_crawl.append(url)
            visited.add(url)
        
        if not urls_to_crawl:
            logger.info(f"No URLs to crawl at depth {depth + 1}")
            break
        
        logger.info(f"📥 Crawling {len(urls_to_crawl)} URLs at depth {depth + 1}")
        depth_start_time = datetime.now()
        
        # Crawl all URLs at this level concurrently with optimized config (streaming mode)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            stream=True,  # Enable streaming to process results as they arrive
            wait_until="domcontentloaded",  # Don't wait for all network activity
            page_timeout=30000,  # 30 second timeout per page
            wait_for_images=False,  # Don't wait for images to load
            exclude_external_links=True,  # Skip external links processing
            exclude_external_images=True,  # Skip external images
            word_count_threshold=50,  # Skip pages with very little content
            remove_overlay_elements=True,  # Auto-remove popups/modals
            magic=True  # Auto-handle common patterns
        )
        
        # Process results and collect links for next level
        next_level_urls: Set[str] = set()
        crawl_results = []
        pages_processed = 0
        
        # Process results as they become available (streaming mode)
        async for result in await crawler.arun_many(
            urls=urls_to_crawl,
            config=run_config,
            dispatcher=dispatcher
        ):
            crawl_results.append(result)
            pages_processed += 1
            
            # Process each result immediately as it arrives (streaming mode)
            if result.success and result.markdown:
                normalized_url = normalize_url(result.url)
                logger.debug(f"📄 Streamed page {pages_processed}/{len(urls_to_crawl)}: {normalized_url}")
                
                # Get parent URL from mapping (or use start URL for first level)
                parent_url = url_to_parent.get(normalized_url, start_url_normalized if depth == 0 else None)
                
                # Extract metadata with crawl context
                crawl_metadata = extract_crawl_metadata(
                    result, 
                    normalized_url, 
                    depth=depth + 1,  # Current depth (0-indexed, so +1)
                    parent_url=parent_url
                )
                
                # Get HTML content (prefer cleaned_html, fallback to html)
                html_content = None
                if hasattr(result, 'cleaned_html') and result.cleaned_html:
                    html_content = result.cleaned_html
                elif hasattr(result, 'html') and result.html:
                    html_content = result.html
                
                results.append({
                    'url': normalized_url,
                    'markdown': result.markdown,
                    'html': html_content,  # Store original HTML
                    'links': result.links or {},
                    'metadata': crawl_metadata
                })
                
                # Collect internal links for next level and track parent relationships
                if depth < max_depth - 1:
                    for link in result.links.get("internal", []):
                        href = link.get("href", "")
                        if href:
                            # Convert relative URLs to absolute
                            absolute_url = urljoin(result.url, href)
                            normalized = normalize_url(absolute_url)
                            if normalized not in visited:
                                next_level_urls.add(normalized)
                                # Track parent relationship
                                url_to_parent[normalized] = normalized_url
            else:
                logger.warning(f"Failed to crawl {result.url}: {result.error_message}")
        
        current_level_urls = next_level_urls
        
        depth_duration = (datetime.now() - depth_start_time).total_seconds()
        logger.info(
            f"✅ Depth {depth + 1} complete: {len(results)} pages crawled so far "
            f"(took {depth_duration:.2f}s)"
        )
    
    total_crawl_time = (datetime.now() - crawl_start_time).total_seconds()
    logger.info(
        f"🎉 Deep crawl complete: {len(results)} pages crawled total "
        f"(total time: {total_crawl_time:.2f}s)"
    )
    return results

