"""Google Drive API low-level wrapper with composition-based architecture."""

import io
from pathlib import Path
from typing import Any, Literal

import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..models import GoogleDriveFile, SearchResult
from .config import DEFAULT_FIELDS, DEFAULT_FOLDER_ID, GOOGLE_DOC_MIME_TYPE
from .exceptions import (
    GoogleDriveException,
    GoogleDriveExportError,
    GoogleDriveFolderResolutionError,
    GoogleDriveNotFoundError,
    GoogleDriveSearchError,
)
from .google_auth import GoogleAuth
from .google_base import GoogleBaseAPI, GoogleBaseExport, GoogleBaseSearch


class GoogleDrive(GoogleBaseAPI):
    """Low-level wrapper for Google Drive API operations with composition-based architecture.

    Uses inner classes for Search and Export operations following SOLID principles.
    Provides access to Drive API operations through composed functionality.
    """

    def __init__(self, authenticator: GoogleAuth):
        """
        Initialize API client with authenticated credentials.

        Args:
            authenticator: GoogleAuth instance
        """
        super().__init__(authenticator)
        self._service = None

        # Composition: Initialize inner class instances
        self.Search = GoogleDrive.Search(self)
        self.Export = GoogleDrive.Export(self)

    @property
    def service(self):
        """Lazy-loaded Google Drive API service client."""
        if self._service is None:
            self._service = build("drive", "v3", credentials=self.authenticator.get_credentials())
        return self._service

    def execute_query(
        self,
        query: str,
        fields: str = DEFAULT_FIELDS,
        page_size: int = 10,
        order_by: str = "modifiedTime desc",
    ) -> dict[str, Any]:
        """
        Execute a raw Drive API query.

        Args:
            query: Drive API query string
            fields: Fields to retrieve
            page_size: Maximum results per page
            order_by: Ordering for results

        Returns:
            Raw API response as dictionary

        Raises:
            GoogleDriveSearchError: If API call fails
        """
        self.refresh_credentials_if_needed()
        try:
            return (
                self.service.files()
                .list(q=query, spaces="drive", pageSize=page_size, fields=fields, orderBy=order_by)
                .execute()
            )
        except HttpError as e:
            raise GoogleDriveSearchError(f"Failed to execute Drive API query: {e}", e) from e

    def get_file_metadata(self, file_id: str, fields: str = "*") -> dict[str, Any]:
        """
        Get metadata for a specific file.

        Args:
            file_id: File ID in Google Drive
            fields: Fields to retrieve

        Returns:
            File metadata as dictionary

        Raises:
            GoogleDriveNotFoundError: If file not found
            GoogleDriveException: If API call fails
        """
        self.refresh_credentials_if_needed()
        try:
            return self.service.files().get(fileId=file_id, fields=fields).execute()
        except HttpError as e:
            if e.resp.status == 404:
                raise GoogleDriveNotFoundError(f"File not found: {file_id}", e) from e
            raise GoogleDriveException(f"Failed to get file metadata for {file_id}: {e}", e) from e

    def export_as_media(self, file_id: str, mime_type: str):
        """
        Get export request for a file in specified MIME type.

        Args:
            file_id: File ID in Google Drive
            mime_type: MIME type to export as

        Returns:
            MediaFileUpload object for streaming download

        Raises:
            GoogleDriveExportError: If file cannot be exported to requested MIME type
        """
        self.refresh_credentials_if_needed()
        try:
            return self.service.files().export_media(fileId=file_id, mimeType=mime_type)
        except HttpError as e:
            raise GoogleDriveExportError(f"Failed to prepare export for {file_id}: {e}", e) from e

    def get_file_media(self, file_id: str):
        """
        Get download request for a file.

        Args:
            file_id: File ID in Google Drive

        Returns:
            MediaFileUpload object for streaming download
        """
        self.refresh_credentials_if_needed()
        return self.service.files().get_media(fileId=file_id)

    class Search(GoogleBaseSearch):
        """Google Drive search operations with folder resolution and query building."""

        def _execute_search(self, query: str, **kwargs) -> dict[str, Any]:
            """Execute Drive API search query.

            Args:
                query: Search query string
                **kwargs: Additional parameters (page_size, order_by, fields)

            Returns:
                Raw Drive API response
            """
            return self._parent.execute_query(
                query,
                page_size=kwargs.get("page_size", 10),
                order_by=kwargs.get("order_by", "modifiedTime desc"),
                fields=kwargs.get("fields", DEFAULT_FIELDS),
            )

        def _format_results(
            self, raw_results: dict[str, Any], query: str, **kwargs
        ) -> SearchResult:
            """Format Drive API results into SearchResult object.

            Args:
                raw_results: Raw Drive API response
                query: Original search query
                **kwargs: Additional context (folder_id, folder_name)

            Returns:
                SearchResult with GoogleDriveFile objects
            """
            files_data = raw_results.get("files", [])

            files = [
                GoogleDriveFile(
                    id=f["id"],
                    name=f["name"],
                    mime_type=f["mimeType"],
                    created_time=f["createdTime"],
                    modified_time=f["modifiedTime"],
                    web_view_link=f["webViewLink"],
                    parents=f.get("parents"),
                    size=f.get("size"),
                )
                for f in files_data
            ]

            return SearchResult(
                query=query,
                folder_id=kwargs.get("folder_id"),
                folder_name=kwargs.get("folder_name"),
                total_results=len(files),
                files=files,
            )

        def resolve_folder(
            self,
            folder_name: str,
            on_duplicates: Literal["error", "newest"] = "error",
        ) -> str:
            """Resolve a folder name to its folder ID.

            Args:
                folder_name: Name of the folder to find
                on_duplicates: How to handle duplicate folder names

            Returns:
                Folder ID string

            Raises:
                GoogleDriveFolderResolutionError: If folder resolution fails
            """
            try:
                query = (
                    f"mimeType='application/vnd.google-apps.folder' "
                    f"and name='{folder_name}' "
                    f"and trashed=false"
                )

                results = self._parent.execute_query(
                    query,
                    fields="files(id, name, modifiedTime)",
                    page_size=100,
                    order_by="modifiedTime desc",
                )

                folders = results.get("files", [])

                if not folders:
                    raise GoogleDriveFolderResolutionError(
                        f"No folder found with name: {folder_name}"
                    )

                if len(folders) > 1 and on_duplicates == "error":
                    folder_list = "\\n".join([f"  - {f['name']} (ID: {f['id']})" for f in folders])
                    raise GoogleDriveFolderResolutionError(
                        f"Multiple folders found with name '{folder_name}':\\n{folder_list}\\n"
                        f"Use folder_id parameter directly or set on_duplicates='newest'"
                    )

                return folders[0]["id"]

            except HttpError as e:
                raise GoogleDriveFolderResolutionError(
                    f"Failed to resolve folder name: {e}", e
                ) from e

        def search(
            self,
            query: str,
            top_n: int = 10,
            folder_id: str | None = None,
            folder_name: str | None = None,
            on_duplicates: Literal["error", "newest"] = "error",
        ) -> SearchResult:
            """Search Google Drive for files matching a query.

            Args:
                query: Search query string (Drive query syntax or keywords)
                top_n: Maximum number of results to return
                folder_id: Optional folder ID to restrict search to
                folder_name: Optional folder name to restrict search to (resolved to ID)
                on_duplicates: How to handle duplicate folder names (if folder_name used)

            Returns:
                SearchResult with matching files

            Raises:
                GoogleDriveSearchError: If search fails
                GoogleDriveFolderResolutionError: If folder resolution fails
            """
            target_folder_id = folder_id
            if folder_name:
                if folder_id:
                    raise GoogleDriveSearchError(
                        "Cannot specify both folder_id and folder_name. Choose one."
                    )
                target_folder_id = self.resolve_folder(folder_name, on_duplicates)

            if not target_folder_id:
                target_folder_id = DEFAULT_FOLDER_ID

            # Build Drive API query
            has_operators = any(
                op in query.lower() for op in [" = ", " != ", "contains", " in ", " and ", " or "]
            )
            drive_query = query if has_operators else f"fullText contains '{query}'"

            if target_folder_id:
                drive_query = f"('{target_folder_id}' in parents) and ({drive_query})"

            drive_query = f"{drive_query} and trashed=false"

            try:
                results = self._execute_search(drive_query, page_size=top_n)
                return self._format_results(
                    results, query, folder_id=target_folder_id, folder_name=folder_name
                )
            except HttpError as e:
                raise GoogleDriveSearchError(f"Failed to search Google Drive: {e}", e) from e

        def search_ids(
            self,
            query: str,
            top_n: int = 10,
            folder_id: str | None = None,
            folder_name: str | None = None,
            on_duplicates: Literal["error", "newest"] = "error",
        ) -> list[str]:
            """Search for documents and return a list of document IDs.

            Args:
                query: Search query string
                top_n: Maximum number of results
                folder_id: Optional folder ID to search within
                folder_name: Optional folder name to search within
                on_duplicates: How to handle duplicate folder names

            Returns:
                List of document IDs
            """
            result = self.search(
                query=query,
                top_n=top_n,
                folder_id=folder_id,
                folder_name=folder_name,
                on_duplicates=on_duplicates,
            )
            return [file.id for file in result.files]

    class Export(GoogleBaseExport):
        """Google Drive export and download operations."""

        def _download_content(self, file_id: str, mime_type: str) -> str:
            """Download content from Google Drive API.

            Args:
                file_id: File identifier
                mime_type: MIME type of the file

            Returns:
                File content as string

            Raises:
                GoogleDriveExportError: If download fails
            """
            try:
                if mime_type == GOOGLE_DOC_MIME_TYPE:
                    request = self._parent.export_as_media(file_id, "text/plain")
                elif mime_type == "text/markdown" or mime_type.startswith("text/"):
                    request = self._parent.get_file_media(file_id)
                else:
                    raise GoogleDriveExportError(
                        f"Cannot export file as markdown. Unsupported MIME type: {mime_type}"
                    )

                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while not done:
                    _status, done = downloader.next_chunk()

                return file_content.getvalue().decode("utf-8")

            except HttpError as e:
                raise GoogleDriveExportError(
                    f"Failed to download content for {file_id}: {e}", e
                ) from e

        def _build_with_frontmatter(self, metadata: dict[str, Any], content: str) -> str:
            """Build markdown content with YAML frontmatter.

            Args:
                metadata: File metadata from Drive API
                content: Document content

            Returns:
                Markdown with YAML frontmatter
            """
            frontmatter = {
                "title": metadata["name"],
                "document_id": metadata["id"],
                "mime_type": metadata["mimeType"],
                "created": metadata["createdTime"],
                "modified": metadata["modifiedTime"],
                "web_view_link": metadata["webViewLink"],
            }

            if "description" in metadata:
                frontmatter["description"] = metadata["description"]

            if metadata.get("owners"):
                frontmatter["owners"] = [
                    owner.get("displayName", owner.get("emailAddress", "Unknown"))
                    for owner in metadata["owners"]
                ]

            yaml_frontmatter = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
            return f"---\\n{yaml_frontmatter}---\\n\\n{content}"

        def download_file(self, file_id: str) -> bytes:
            """Download a file from Google Drive as binary data.

            This method is useful for downloading binary files like LoRA models,
            images, or other non-text files.

            Args:
                file_id: File ID in Google Drive

            Returns:
                File content as bytes

            Raises:
                GoogleDriveExportError: If download fails
            """
            try:
                request = self._parent.get_file_media(file_id)
                file_content = io.BytesIO()
                downloader = MediaIoBaseDownload(file_content, request)
                done = False
                while not done:
                    _status, done = downloader.next_chunk()

                return file_content.getvalue()
            except HttpError as e:
                raise GoogleDriveExportError(f"Failed to download file {file_id}: {e}", e) from e

        def export_as_markdown(
            self,
            document_id: str,
            include_metadata: bool = True,
            output_path: str | Path | None = None,
        ) -> str:
            """Export a Google Drive document as markdown with optional YAML frontmatter.

            Args:
                document_id: The Google Drive document ID
                include_metadata: Whether to include YAML frontmatter with metadata
                output_path: Optional path to write the markdown file to

            Returns:
                The markdown content as a string

            Raises:
                GoogleDriveExportError: If document cannot be exported or doesn't exist
            """
            try:
                # Get file metadata
                file_metadata = self._parent.get_file_metadata(
                    document_id,
                    fields="id,name,mimeType,createdTime,modifiedTime,webViewLink,owners,description",
                )

                mime_type = file_metadata["mimeType"]
                content = self._download_content(document_id, mime_type)

                if include_metadata:
                    markdown_content = self._build_with_frontmatter(file_metadata, content)
                else:
                    markdown_content = content

                if output_path:
                    self._write_file(output_path, markdown_content)

                return markdown_content

            except HttpError as e:
                raise GoogleDriveExportError(
                    f"Failed to export document {document_id}: {e}", e
                ) from e

        def _write_file(self, output_path: str | Path, content: str) -> None:
            """Write markdown content to a file, creating parent directories if needed.

            Args:
                output_path: Path where to write the file
                content: Content to write
            """
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(content, encoding="utf-8")


__all__ = ["GoogleDrive"]
