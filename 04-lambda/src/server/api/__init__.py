"""API module - router registration handled directly in main.py.

This module previously imported routers which caused circular import issues.
Routers are now imported directly in main.py where they're registered.

See main.py for router registration and API_STRATEGY.md for routing conventions.
"""

__all__: list[str] = []
