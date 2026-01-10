# Copilot tools

If your Copilot environment supports function-style tools, implement adapters here that call into repository code (e.g., `examples/tools.py`). Keep them small and type-safe.

Examples to expose:

- `semantic_search(query: str, k: int = 10)`
- `hybrid_search(query: str, k: int = 10)`
