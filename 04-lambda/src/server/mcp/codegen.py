"""MCP code generation module.

This module generates MCP server modules for code execution.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_all_servers(servers_dir: Path) -> None:
    """
    Generate all MCP server modules.

    Args:
        servers_dir: Directory to store generated server modules.
    """
    servers_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"MCP servers directory ensured: {servers_dir}")
    # No-op for now - can be extended to generate server code if needed
