"""Code generator for MCP tools as Python modules."""

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Tool to server mapping
TOOL_SERVER_MAP = {
    "search_knowledge_base": "mongo_rag",
    "ingest_documents": "mongo_rag",
    "agent_query": "mongo_rag",
    "crawl_single_page": "crawl4ai_rag",
    "crawl_deep": "crawl4ai_rag",
    "web_search": "searxng",
}


def json_schema_to_python_type(schema: dict[str, Any], param_name: str = "") -> str:
    """
    Convert JSON Schema type to Python type hint.

    Args:
        schema: JSON Schema definition
        param_name: Parameter name for better error messages

    Returns:
        Python type hint string
    """
    schema_type = schema.get("type")

    if schema_type == "string":
        return "str"
    elif schema_type == "integer":
        return "int"
    elif schema_type == "number":
        return "float"
    elif schema_type == "boolean":
        return "bool"
    elif schema_type == "array":
        items = schema.get("items", {})
        if isinstance(items, dict) and items.get("type"):
            item_type = json_schema_to_python_type(items, f"{param_name}_item")
            return f"List[{item_type}]"
        return "List[Any]"
    elif schema_type == "object":
        return "dict"
    elif "enum" in schema:
        # Create Literal type from enum
        enum_values = schema["enum"]
        enum_str = ", ".join([f'"{v}"' for v in enum_values])
        return f"Literal[{enum_str}]"
    else:
        return "Any"


def get_python_default(schema: dict[str, Any]) -> str | None:
    """Get Python default value from JSON Schema."""
    if "default" in schema:
        default = schema["default"]
        if isinstance(default, str):
            return f'"{default}"'
        elif isinstance(default, bool):
            return "True" if default else "False"
        elif default is None:
            return "None"
        else:
            return str(default)
    return None


def generate_parameter_signature(
    prop_name: str, prop_schema: dict[str, Any], required: list[str]
) -> str:
    """
    Generate function parameter signature from JSON Schema property.

    Args:
        prop_name: Parameter name
        prop_schema: JSON Schema property definition
        required: List of required parameter names

    Returns:
        Parameter signature string (e.g., "query: str" or "match_count: Optional[int] = 5")
    """
    param_type = json_schema_to_python_type(prop_schema, prop_name)

    # Check if parameter is required
    is_required = prop_name in required

    # Get default value
    default = get_python_default(prop_schema)

    # Build signature
    if is_required:
        return f"{prop_name}: {param_type}"
    else:
        # Optional type for non-required parameters
        if param_type.startswith("Literal"):
            # Literal types need special handling
            param_type = f"Optional[{param_type}]"
        elif not param_type.startswith("Optional"):
            param_type = f"Optional[{param_type}]"

        if default is not None:
            return f"{prop_name}: {param_type} = {default}"
        else:
            return f"{prop_name}: {param_type} = None"


def generate_tool_module(tool: dict[str, Any], server_name: str) -> str:
    """
    Generate Python module code for a single MCP tool.

    Args:
        tool: Tool definition from list_tools()
        server_name: Server/project name (e.g., "mongo_rag")

    Returns:
        Python module code as string
    """
    tool_name = tool["name"]
    description = tool.get("description", "")
    input_schema = tool.get("inputSchema", {})
    properties = input_schema.get("properties", {})
    required = input_schema.get("required", [])

    # Generate function name (same as tool name)
    func_name = tool_name

    # Generate parameter signatures
    param_signatures = []
    for prop_name, prop_schema in properties.items():
        param_sig = generate_parameter_signature(prop_name, prop_schema, required)
        param_signatures.append(param_sig)

    # Generate parameter docstrings
    param_docs = []
    for prop_name, prop_schema in properties.items():
        prop_desc = prop_schema.get("description", "")
        prop_type = json_schema_to_python_type(prop_schema, prop_name)
        default = get_python_default(prop_schema)

        doc_line = f"        {prop_name} ({prop_type}): {prop_desc}"
        if default is not None:
            doc_line += f" Default: {default}."
        if prop_name in required:
            doc_line += " Required."
        param_docs.append(doc_line)

    # Build imports
    imports = [
        "from typing import Optional, List, Any, Literal",
        "from server.mcp.servers.client import call_mcp_tool",
    ]

    # Generate function code
    function_code = f'''"""{description}"""
{chr(10).join(imports)}

async def {func_name}(
    {", ".join(param_signatures)}
) -> dict:
    """
    {description}

    Args:
{chr(10).join(param_docs)}

    Returns:
        Tool response as dictionary.
    """
    return await call_mcp_tool(
        "{tool_name}",
        {{
{chr(10).join(f'            "{prop_name}": {prop_name},' for prop_name in properties)}
        }}
    )
'''

    return function_code


def generate_server_index(server_name: str, tools: list[dict[str, Any]]) -> str:
    """
    Generate __init__.py for a server module.

    Args:
        server_name: Server/project name
        tools: List of tool definitions for this server

    Returns:
        __init__.py content as string
    """
    tool_names = [tool["name"] for tool in tools]
    imports = [f"from .{tool_name} import {tool_name}" for tool_name in tool_names]

    exports = f"__all__ = {tool_names!r}"

    return f'''"""MCP tools for {server_name} server."""
{chr(10).join(imports)}

{exports}
'''


def group_tools_by_server(tools: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """
    Group tools by server/project.

    Args:
        tools: List of tool definitions

    Returns:
        Dictionary mapping server names to tool lists
    """
    grouped = defaultdict(list)

    for tool in tools:
        tool_name = tool["name"]
        server_name = TOOL_SERVER_MAP.get(tool_name)

        if not server_name:
            # Fallback: try to infer from tool name
            if "crawl" in tool_name:
                server_name = "crawl4ai_rag"
            elif any(keyword in tool_name for keyword in ["search", "ingest", "agent"]):
                server_name = "mongo_rag"
            else:
                server_name = "default"

        grouped[server_name].append(tool)

    return dict(grouped)


def get_tool_definitions() -> list[dict[str, Any]]:
    """
    Extract tool definitions from the FastMCP server.

    Returns:
        List of tool definitions in MCP format
    """
    import asyncio

    from server.mcp.fastmcp_server import mcp

    # Get tools from FastMCP server (get_tools() is async, returns list[Tool])
    # Try to use existing event loop, or create new one if none exists
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is running, we need to use nest_asyncio or create a task
            # For now, create a new event loop in a thread
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, mcp.get_tools())
                fastmcp_tools = future.result()
        else:
            fastmcp_tools = loop.run_until_complete(mcp.get_tools())
    except RuntimeError:
        # No event loop, create new one
        fastmcp_tools = asyncio.run(mcp.get_tools())

    # Convert FastMCP tool format to MCP tool definition format
    # get_tools() returns list[Tool], not dict
    tools = []
    for tool in fastmcp_tools:
        # Skip non-Tool objects (e.g., strings or other types)
        if not hasattr(tool, "to_mcp_tool"):
            logger.debug(f"Skipping non-Tool object: {type(tool).__name__}")
            continue

        try:
            # Convert FastMCP Tool to MCP tool definition using to_mcp_tool()
            mcp_tool = tool.to_mcp_tool()
            tool_def = {
                "name": mcp_tool.name,
                "description": mcp_tool.description or "",
                "inputSchema": mcp_tool.inputSchema,
            }
            tools.append(tool_def)
        except Exception as e:
            tool_name = getattr(tool, "name", "unknown")
            logger.warning(f"Failed to extract tool definition for {tool_name}: {e}")
            # Fallback: basic tool definition
            tools.append(
                {
                    "name": tool_name,
                    "description": getattr(tool, "description", "") or "",
                    "inputSchema": {},
                }
            )

    return tools


def generate_all_servers(output_dir: Path) -> None:
    """
    Generate all server modules from current tool definitions.

    Args:
        output_dir: Directory to write generated modules
    """
    # Get tool definitions
    tools = get_tool_definitions()

    if not tools:
        logger.error("No tools found to generate")
        return

    # Group tools by server
    grouped = group_tools_by_server(tools)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate modules for each server
    for server_name, server_tools in grouped.items():
        server_dir = output_dir / server_name
        server_dir.mkdir(parents=True, exist_ok=True)

        # Generate __init__.py
        init_content = generate_server_index(server_name, server_tools)
        (server_dir / "__init__.py").write_text(init_content)

        # Generate module for each tool
        for tool in server_tools:
            tool_name = tool["name"]
            module_content = generate_tool_module(tool, server_name)
            (server_dir / f"{tool_name}.py").write_text(module_content)
            logger.info(f"Generated module: {server_dir / f'{tool_name}.py'}")

    logger.info(f"Generated {len(grouped)} server modules with {len(tools)} tools total")
