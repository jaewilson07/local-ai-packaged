"""Google Drive service facade providing unified high-level interface.

This module combines authentication, search, and export operations into
a single facade for easier use. Follows the Facade design pattern.
"""

from pathlib import Path
from typing import Literal

from .classes import (
    GoogleDoc,
    GoogleDrive,
    GoogleAuth,
)
from .classes.google_drive_api import DEFAULT_FOLDER_ID
from .models import GoogleDocumentTab, GoogleDriveFile, SearchResult


class GoogleDriveService:
    """Unified service for Google Drive search, document export, and file download operations."""

    def __init__(
        self,
        credentials_json: str | None = None,
        token_json: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        """
        Initialize the Google Drive service.

        Supports multiple credential formats:
        1. JSON strings (GDOC_CLIENT and GDOC_TOKEN env vars)
        2. Separate client_id and client_secret (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, etc.)

        Args:
            credentials_json: OAuth client configuration JSON (from GDOC_CLIENT env var)
            token_json: Serialized token JSON (from GDOC_TOKEN env var)
            client_id: OAuth client ID (alternative to JSON)
            client_secret: OAuth client secret (alternative to JSON)

        Raises:
            ValueError: If credentials are missing or invalid
        """
        self.authenticator = GoogleAuth(
            credentials_json=credentials_json,
            token_json=token_json,
            client_id=client_id,
            client_secret=client_secret
        )
        self.api = GoogleDrive(self.authenticator)
        self.docs_api = GoogleDoc(self.authenticator)

    def search_files(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> SearchResult:
        """
        Search Google Drive for files matching a query.

        Args:
            query: Search query string (Drive query syntax or keywords)
            top_n: Maximum number of results to return
            folder_id: Optional folder ID to restrict search to
            folder_name: Optional folder name to restrict search to
            on_duplicates: How to handle duplicate folder names

        Returns:
            SearchResult with matching files
        """
        return self.api.search(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )

    def search_document_ids(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> list[str]:
        """
        Search for documents and return a list of document IDs.

        Args:
            query: Search query string
            top_n: Maximum number of results
            folder_id: Optional folder ID to search within
            folder_name: Optional folder name to search within
            on_duplicates: How to handle duplicate folder names

        Returns:
            List of document IDs
        """
        return self.api.search_ids(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )

    def search_documents(
        self,
        query: str,
        top_n: int = 10,
        folder_id: str | None = None,
        folder_name: str | None = None,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> list[GoogleDriveFile]:
        """
        Search for documents and return full file metadata.

        Args:
            query: Search query string
            top_n: Maximum number of results
            folder_id: Optional folder ID to search within
            folder_name: Optional folder name to search within
            on_duplicates: How to handle duplicate folder names

        Returns:
            List of GoogleDriveFile objects
        """
        result = self.search_files(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        return result.files

    def download_file(self, file_id: str) -> bytes:
        """
        Download a file from Google Drive as binary data.
        
        This method is useful for downloading binary files like LoRA models,
        images, or other non-text files.
        
        Args:
            file_id: File ID in Google Drive
        
        Returns:
            File content as bytes
        
        Raises:
            ValueError: If download fails
        """
        return self.api.download_file(file_id)

    def export_as_markdown(
        self,
        document_id: str,
        include_metadata: bool = True,
        output_path: str | Path | None = None,
    ) -> str:
        """
        Export a Google Drive document as markdown with optional YAML frontmatter.

        Args:
            document_id: The Google Drive document ID
            include_metadata: Whether to include YAML frontmatter with metadata
            output_path: Optional path to write the markdown file to

        Returns:
            The markdown content as a string

        Raises:
            ValueError: If document cannot be exported or doesn't exist
        """
        return self.api.export_as_markdown(
            document_id=document_id,
            include_metadata=include_metadata,
            output_path=output_path,
        )

    def export_tabs(self, document_id: str) -> list[GoogleDocumentTab]:
        """Export a Google Doc into per-tab markdown sections.

        Returns a list of GoogleDocumentTab models, one per split tab.
        """
        return self.docs_api.export_tabs(document_id)


__all__ = ["GoogleDriveService"]
