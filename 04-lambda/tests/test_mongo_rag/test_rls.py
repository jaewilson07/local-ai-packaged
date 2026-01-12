"""Tests for MongoDB RAG Row-Level Security (RLS) functions."""

from server.projects.mongo_rag.rls import (
    add_sharing_to_document,
    build_access_filter,
    build_chunk_access_filter,
    can_access_document,
    remove_sharing_from_document,
)


class TestBuildAccessFilter:
    """Test build_access_filter function."""

    def test_regular_user_own_documents(self):
        """Test regular user can see their own documents."""
        user_id = "user-123"
        user_email = "user@example.com"

        filter_dict = build_access_filter(user_id, user_email)

        assert "$or" in filter_dict
        conditions = filter_dict["$or"]

        # Should include ownership conditions
        assert {"user_id": user_id} in conditions
        assert {"user_email": user_email} in conditions
        # Should include public documents
        assert {"is_public": True} in conditions
        # Should include shared documents
        assert {"shared_with": {"$in": [user_id, user_email]}} in conditions

    def test_regular_user_with_groups(self):
        """Test regular user with groups can see group-shared documents."""
        user_id = "user-123"
        user_email = "user@example.com"
        groups = ["group-1", "group-2"]

        filter_dict = build_access_filter(user_id, user_email, user_groups=groups)

        assert "$or" in filter_dict
        conditions = filter_dict["$or"]

        # Should include group sharing
        assert {"group_ids": {"$in": groups}} in conditions

    def test_admin_bypass(self):
        """Test admin users bypass all filtering."""
        user_id = "admin-123"
        user_email = "admin@example.com"

        filter_dict = build_access_filter(user_id, user_email, is_admin=True)

        # Admin should get empty filter (sees all)
        assert filter_dict == {}

    def test_empty_user_id(self):
        """Test handling of empty user_id."""
        user_id = ""
        user_email = "user@example.com"

        filter_dict = build_access_filter(user_id, user_email)

        # Should still work, just won't match user_id
        assert "$or" in filter_dict
        conditions = filter_dict["$or"]
        assert {"user_email": user_email} in conditions

    def test_no_groups(self):
        """Test user without groups doesn't include group filter."""
        user_id = "user-123"
        user_email = "user@example.com"

        filter_dict = build_access_filter(user_id, user_email, user_groups=None)

        conditions = filter_dict["$or"]
        # Should not have group_ids condition
        group_conditions = [c for c in conditions if "group_ids" in c]
        assert len(group_conditions) == 0


class TestBuildChunkAccessFilter:
    """Test build_chunk_access_filter function."""

    def test_chunk_filter_delegates_to_document_filter(self):
        """Test chunk filter uses document filter logic."""
        user_id = "user-123"
        user_email = "user@example.com"

        chunk_filter = build_chunk_access_filter(user_id, user_email)
        doc_filter = build_access_filter(user_id, user_email)

        # Should return same filter (chunks inherit from documents)
        assert chunk_filter == doc_filter


class TestCanAccessDocument:
    """Test can_access_document function."""

    def test_own_document_by_user_id(self):
        """Test user can access their own document by user_id."""
        document = {"user_id": "user-123", "title": "My Document"}

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is True
        )

    def test_own_document_by_user_email(self):
        """Test user can access their own document by user_email."""
        document = {"user_email": "user@example.com", "title": "My Document"}

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is True
        )

    def test_public_document(self):
        """Test user can access public document."""
        document = {"user_id": "other-user", "is_public": True, "title": "Public Document"}

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is True
        )

    def test_shared_document_by_user_id(self):
        """Test user can access document shared with their user_id."""
        document = {
            "user_id": "other-user",
            "shared_with": ["user-123", "other-user-2"],
            "title": "Shared Document",
        }

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is True
        )

    def test_shared_document_by_email(self):
        """Test user can access document shared with their email."""
        document = {
            "user_id": "other-user",
            "shared_with": ["user@example.com"],
            "title": "Shared Document",
        }

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is True
        )

    def test_group_shared_document(self):
        """Test user can access document shared with their group."""
        document = {
            "user_id": "other-user",
            "group_ids": ["group-1", "group-2"],
            "title": "Group Shared Document",
        }

        assert (
            can_access_document(
                document,
                current_user_id="user-123",
                current_user_email="user@example.com",
                user_groups=["group-1"],
            )
            is True
        )

    def test_denied_access(self):
        """Test user cannot access document they don't own or share."""
        document = {
            "user_id": "other-user",
            "is_public": False,
            "shared_with": [],
            "group_ids": [],
            "title": "Private Document",
        }

        assert (
            can_access_document(
                document, current_user_id="user-123", current_user_email="user@example.com"
            )
            is False
        )

    def test_admin_access(self):
        """Test admin can access any document."""
        document = {"user_id": "other-user", "is_public": False, "title": "Private Document"}

        assert (
            can_access_document(
                document,
                current_user_id="admin-123",
                current_user_email="admin@example.com",
                is_admin=True,
            )
            is True
        )


class TestAddSharingToDocument:
    """Test add_sharing_to_document function."""

    def test_add_public_flag(self):
        """Test adding is_public flag."""
        document = {"title": "Document"}

        result = add_sharing_to_document(document, is_public=True)

        assert result["is_public"] is True

    def test_add_shared_with(self):
        """Test adding users to shared_with list."""
        document = {"title": "Document"}

        result = add_sharing_to_document(document, shared_with=["user-1", "user-2"])

        assert "user-1" in result["shared_with"]
        assert "user-2" in result["shared_with"]

    def test_merge_shared_with(self):
        """Test merging with existing shared_with list."""
        document = {"title": "Document", "shared_with": ["user-1"]}

        result = add_sharing_to_document(document, shared_with=["user-2", "user-3"])

        assert "user-1" in result["shared_with"]
        assert "user-2" in result["shared_with"]
        assert "user-3" in result["shared_with"]
        # Should deduplicate
        assert len(result["shared_with"]) == 3

    def test_add_group_ids(self):
        """Test adding group IDs."""
        document = {"title": "Document"}

        result = add_sharing_to_document(document, group_ids=["group-1", "group-2"])

        assert "group-1" in result["group_ids"]
        assert "group-2" in result["group_ids"]

    def test_merge_group_ids(self):
        """Test merging with existing group_ids."""
        document = {"title": "Document", "group_ids": ["group-1"]}

        result = add_sharing_to_document(document, group_ids=["group-2"])

        assert "group-1" in result["group_ids"]
        assert "group-2" in result["group_ids"]


class TestRemoveSharingFromDocument:
    """Test remove_sharing_from_document function."""

    def test_remove_from_shared_with(self):
        """Test removing users from shared_with."""
        document = {"title": "Document", "shared_with": ["user-1", "user-2", "user-3"]}

        result = remove_sharing_from_document(document, shared_with=["user-2"])

        assert "user-1" in result["shared_with"]
        assert "user-2" not in result["shared_with"]
        assert "user-3" in result["shared_with"]

    def test_remove_from_group_ids(self):
        """Test removing groups from group_ids."""
        document = {"title": "Document", "group_ids": ["group-1", "group-2", "group-3"]}

        result = remove_sharing_from_document(document, group_ids=["group-2"])

        assert "group-1" in result["group_ids"]
        assert "group-2" not in result["group_ids"]
        assert "group-3" in result["group_ids"]

    def test_remove_nonexistent(self):
        """Test removing non-existent entries is safe."""
        document = {"title": "Document", "shared_with": ["user-1"]}

        result = remove_sharing_from_document(document, shared_with=["user-999"])

        # Should not error, just ignore
        assert "user-1" in result["shared_with"]

    def test_remove_from_empty(self):
        """Test removing from empty list is safe."""
        document = {"title": "Document"}

        result = remove_sharing_from_document(document, shared_with=["user-1"])

        assert result.get("shared_with", []) == []
