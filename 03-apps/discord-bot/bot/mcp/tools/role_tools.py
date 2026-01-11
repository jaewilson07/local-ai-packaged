"""Role management MCP tools."""

import logging

import discord

from bot.mcp.server import get_discord_client, mcp

logger = logging.getLogger(__name__)


@mcp.tool
async def add_role(server_id: str, user_id: str, role_id: str) -> dict:
    """
    Add a role to a user in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        user_id: The Discord user ID to add the role to.
        role_id: The Discord role ID to add.

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    member = guild.get_member(int(user_id))
    if not member:
        try:
            member = await guild.fetch_member(int(user_id))
        except discord.NotFound:
            raise ValueError(f"User {user_id} not found in server {server_id}")

    role = guild.get_role(int(role_id))
    if not role:
        raise ValueError(f"Role {role_id} not found in server {server_id}")

    # Check if user already has the role
    if role in member.roles:
        return {"success": True, "message": f"User {user_id} already has role {role_id}"}

    try:
        await member.add_roles(role, reason="Added via MCP tool")
        return {
            "success": True,
            "message": f"Added role {role.name} to user {member.display_name}",
            "user_id": user_id,
            "role_id": role_id,
        }
    except discord.Forbidden:
        raise RuntimeError("Bot lacks permissions to add roles (requires MANAGE_ROLES permission)")
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to add role: {e}")


@mcp.tool
async def remove_role(server_id: str, user_id: str, role_id: str) -> dict:
    """
    Remove a role from a user in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        user_id: The Discord user ID to remove the role from.
        role_id: The Discord role ID to remove.

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    member = guild.get_member(int(user_id))
    if not member:
        try:
            member = await guild.fetch_member(int(user_id))
        except discord.NotFound:
            raise ValueError(f"User {user_id} not found in server {server_id}")

    role = guild.get_role(int(role_id))
    if not role:
        raise ValueError(f"Role {role_id} not found in server {server_id}")

    # Check if user has the role
    if role not in member.roles:
        return {"success": True, "message": f"User {user_id} does not have role {role_id}"}

    try:
        await member.remove_roles(role, reason="Removed via MCP tool")
        return {
            "success": True,
            "message": f"Removed role {role.name} from user {member.display_name}",
            "user_id": user_id,
            "role_id": role_id,
        }
    except discord.Forbidden:
        raise RuntimeError(
            "Bot lacks permissions to remove roles (requires MANAGE_ROLES permission)"
        )
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to remove role: {e}")


@mcp.tool
async def list_roles(server_id: str) -> list[dict]:
    """
    List all roles in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.

    Returns:
        List of role information dictionaries, sorted by position (highest first).
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    roles = []
    # Sort roles by position (highest first, which is Discord's default)
    for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
        roles.append(
            {
                "id": str(role.id),
                "name": role.name,
                "color": role.color.value if role.color.value != 0 else None,
                "position": role.position,
                "mentionable": role.mentionable,
                "hoist": role.hoist,
                "managed": role.managed,
                "permissions": str(role.permissions.value),
                "created_at": role.created_at.isoformat(),
            }
        )

    return roles


@mcp.tool
async def get_role_info(server_id: str, role_id: str) -> dict:
    """
    Get detailed information about a specific role in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        role_id: The Discord role ID.

    Returns:
        Dictionary containing detailed role information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    role = guild.get_role(int(role_id))
    if not role:
        raise ValueError(f"Role {role_id} not found in server {server_id}")

    # Count members with this role
    member_count = sum(1 for member in guild.members if role in member.roles)

    return {
        "id": str(role.id),
        "name": role.name,
        "color": role.color.value if role.color.value != 0 else None,
        "color_hex": f"#{role.color.value:06x}" if role.color.value != 0 else None,
        "position": role.position,
        "mentionable": role.mentionable,
        "hoist": role.hoist,
        "managed": role.managed,
        "permissions": str(role.permissions.value),
        "permissions_value": role.permissions.value,
        "member_count": member_count,
        "created_at": role.created_at.isoformat(),
        "mention": role.mention,
    }


@mcp.tool
async def create_role(
    server_id: str,
    name: str,
    color: int | None = None,
    hoist: bool = False,
    mentionable: bool = False,
    permissions: int | None = None,
) -> dict:
    """
    Create a new role in a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        name: The name for the new role.
        color: Optional color value (integer, 0xRRGGBB format).
        hoist: Whether to display role members separately (default: False).
        mentionable: Whether the role is mentionable (default: False).
        permissions: Optional permissions value (bitwise flags).

    Returns:
        Dictionary containing the created role information.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    # Prepare role creation parameters
    kwargs = {
        "name": name,
        "hoist": hoist,
        "mentionable": mentionable,
    }

    if color is not None:
        kwargs["color"] = discord.Color(color)

    if permissions is not None:
        kwargs["permissions"] = discord.Permissions(permissions=permissions)

    try:
        role = await guild.create_role(**kwargs, reason="Created via MCP tool")
        return {
            "id": str(role.id),
            "name": role.name,
            "color": role.color.value if role.color.value != 0 else None,
            "position": role.position,
            "mentionable": role.mentionable,
            "hoist": role.hoist,
            "managed": role.managed,
            "permissions": str(role.permissions.value),
        }
    except discord.Forbidden:
        raise RuntimeError(
            "Bot lacks permissions to create roles (requires MANAGE_ROLES permission)"
        )
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to create role: {e}")


@mcp.tool
async def delete_role(server_id: str, role_id: str) -> dict:
    """
    Delete a role from a Discord server.

    Args:
        server_id: The Discord server (guild) ID.
        role_id: The Discord role ID to delete.

    Returns:
        Dictionary with success status.
    """
    client = get_discord_client()
    guild = client.get_guild(int(server_id))
    if not guild:
        raise ValueError(f"Server {server_id} not found or bot is not a member")

    role = guild.get_role(int(role_id))
    if not role:
        raise ValueError(f"Role {role_id} not found in server {server_id}")

    # Prevent deletion of @everyone role
    if role.is_default():
        raise ValueError("Cannot delete the @everyone role")

    # Prevent deletion of managed roles (bot roles, integration roles)
    if role.managed:
        raise ValueError(f"Cannot delete managed role {role.name}")

    role_name = role.name
    try:
        await role.delete(reason="Deleted via MCP tool")
        return {
            "success": True,
            "message": f"Deleted role {role_name}",
            "role_id": role_id,
        }
    except discord.Forbidden:
        raise RuntimeError(
            "Bot lacks permissions to delete roles (requires MANAGE_ROLES permission and role must be below bot's highest role)"
        )
    except discord.HTTPException as e:
        raise RuntimeError(f"Failed to delete role: {e}")
