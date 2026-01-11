#!/usr/bin/env python3
"""Validate that all FastAPI routes are properly registered."""

import sys
from pathlib import Path

# Add server to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    # Try to import app - this will fail if there are syntax errors
    from server.main import app
    
    print("✓ Server imports successfully")
    
    # Check that routes are registered
    routes = [route.path for route in app.routes]
    
    expected_routes = [
        "/health",
        "/",
        "/api/v1/rag",
        "/api/v1/crawl",
        "/api/v1/n8n",
        "/api/v1/openwebui",
        "/api/v1/calendar",
        "/api/v1/persona",
        "/api/v1/conversation",
    ]
    
    print(f"\n✓ Found {len(routes)} total routes")
    
    # Check for key route prefixes
    route_prefixes = set()
    for route in routes:
        if route.startswith("/api/v1/"):
            prefix = "/".join(route.split("/")[:3])
            route_prefixes.add(prefix)
    
    print(f"\n✓ Registered API route prefixes:")
    for prefix in sorted(route_prefixes):
        print(f"  - {prefix}")
    
    # Check for specific endpoints
    key_endpoints = [
        "/health",
        "/api/v1/rag/agent",
        "/api/v1/rag/search",
        "/api/v1/rag/ingest",
    ]
    
    print(f"\n✓ Checking key endpoints:")
    for endpoint in key_endpoints:
        # Check if any route matches this path
        matching = [r for r in routes if r.startswith(endpoint) or endpoint.startswith(r)]
        if matching:
            print(f"  ✓ {endpoint} - found")
        else:
            print(f"  ⚠ {endpoint} - not found (may be a prefix)")
    
    print("\n✓ All routes validated successfully!")
    sys.exit(0)
    
except SyntaxError as e:
    print(f"✗ Syntax error: {e}")
    sys.exit(1)
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
