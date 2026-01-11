"""Row-Level Security (RLS) filter builder for MongoDB RAG.

Provides consistent access control filtering across all MongoDB queries,
supporting user ownership, public sharing, direct sharing, and group sharing.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def build_access_filter(
    current_user_id: str,
    current_user_email: str,
    user_groups: list[str] | None = None,
    is_admin: bool = False,
) -> dict[str, Any]:
    """
    Build MongoDB filter for RLS with sharing support.

    This filter ensures users can only access:
    - Their own documents (user_id or user_email match)
    - Public documents (is_public = True)
    - Documents shared directly with them (shared_with contains user_id/email)
    - Documents shared with their groups (group_ids contains any of user_groups)

    Admin users bypass all filtering (empty filter = see all).

    Args:
        current_user_id: Current user's UUID (from Supabase profiles)
        current_user_email: Current user's email address
        user_groups: List of group IDs the user belongs to (optional)
        is_admin: Whether user is an admin (bypasses filtering if True)

    Returns:
        MongoDB query filter dictionary
    """
    if is_admin:
        # Admins see all documents
        return {}

    # Build access filter for regular users
    filter_conditions = [
        # Own documents
        {"user_id": current_user_id},
        {"user_email": current_user_email},
        # Public documents
        {"is_public": True},
        # Directly shared documents
        {"shared_with": {"$in": [current_user_id, current_user_email]}},
    ]

    # Group-shared documents (if user has groups)
    if user_groups:
        filter_conditions.append({"group_ids": {"$in": user_groups}})

    return {"$or": filter_conditions}


def build_chunk_access_filter(
    current_user_id: str,
    current_user_email: str,
    user_groups: list[str] | None = None,
    is_admin: bool = False,
) -> dict[str, Any]:
    """
    Build MongoDB filter for chunks with RLS.

    Chunks inherit access control from their parent documents via document_id lookup.
    This filter is used in aggregation pipelines that join chunks with documents.

    Args:
        current_user_id: Current user's UUID
        current_user_email: Current user's email address
        user_groups: List of group IDs (optional)
        is_admin: Whether user is an admin

    Returns:
        MongoDB filter for document lookup (used in $lookup stages)
    """
    # Chunks are filtered by joining with documents and applying document-level RLS
    # This filter is applied to the document collection in $lookup stages
    return build_access_filter(current_user_id, current_user_email, user_groups, is_admin)


def can_access_document(
    document: dict[str, Any],
    current_user_id: str,
    current_user_email: str,
    user_groups: list[str] | None = None,
    is_admin: bool = False,
) -> bool:
    """
    Check if a user can access a specific document (application-level check).

    Useful for validating access before operations or in application logic.

    Args:
        document: Document dictionary from MongoDB
        current_user_id: Current user's UUID
        current_user_email: Current user's email address
        user_groups: List of group IDs (optional)
        is_admin: Whether user is an admin

    Returns:
        True if user can access document, False otherwise
    """
    if is_admin:
        return True

    # Check ownership
    if document.get("user_id") == current_user_id:
        return True
    if document.get("user_email") == current_user_email:
        return True

    # Check public access
    if document.get("is_public", False):
        return True

    # Check direct sharing
    shared_with = document.get("shared_with", [])
    if current_user_id in shared_with or current_user_email in shared_with:
        return True

    # Check group sharing
    if user_groups:
        document_groups = document.get("group_ids", [])
        if any(gid in document_groups for gid in user_groups):
            return True

    return False


def add_sharing_to_document(
    document: dict[str, Any],
    is_public: bool | None = None,
    shared_with: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Add sharing fields to a document dictionary.

    Args:
        document: Document dictionary
        is_public: Whether document should be public
        shared_with: List of user IDs/emails to share with
        group_ids: List of group IDs to share with

    Returns:
        Updated document dictionary
    """
    if is_public is not None:
        document["is_public"] = is_public

    if shared_with is not None:
        # Merge with existing shared_with list
        existing = document.get("shared_with", [])
        document["shared_with"] = list(set(existing + shared_with))

    if group_ids is not None:
        # Merge with existing group_ids list
        existing = document.get("group_ids", [])
        document["group_ids"] = list(set(existing + group_ids))

    return document


def remove_sharing_from_document(
    document: dict[str, Any],
    shared_with: list[str] | None = None,
    group_ids: list[str] | None = None,
) -> dict[str, Any]:
    """
    Remove sharing from a document.

    Args:
        document: Document dictionary
        shared_with: List of user IDs/emails to remove from sharing
        group_ids: List of group IDs to remove from sharing

    Returns:
        Updated document dictionary
    """
    if shared_with is not None:
        existing = document.get("shared_with", [])
        document["shared_with"] = [uid for uid in existing if uid not in shared_with]

    if group_ids is not None:
        existing = document.get("group_ids", [])
        document["group_ids"] = [gid for gid in existing if gid not in group_ids]

    return document
