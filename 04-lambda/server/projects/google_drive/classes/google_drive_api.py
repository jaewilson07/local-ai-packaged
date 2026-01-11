"""Google Drive API low-level wrapper."""

import io
from pathlib import Path
from typing import Any, Literal

import yaml
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from ..models import GoogleDriveFile, SearchResult
from .google_drive_authenticator import GoogleAuth

DEFAULT_FOLDER_ID = "13ICM72u7cnvCb0ATpVXdHWqxH1SmiG_Q"


class GoogleDrive:
    """Low-level wrapper for Google Drive API operations with integrated search and export."""

    def __init__(self, authenticator: GoogleAuth):
        """
        Initialize API client with authenticated credentials.

        Args:
            authenticator: GoogleAuth instance
        """
        self.authenticator = authenticator
        self.service = build("drive", "v3", credentials=authenticator.get_credentials())

    def execute_query(
        self,
        query: str,
        fields: str = "files(id, name, mimeType, createdTime, modifiedTime, webViewLink, parents, size)",
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
            HttpError: If API call fails
        """
        self.authenticator.refresh_if_needed()
        try:
            return (
                self.service.files()
                .list(q=query, spaces="drive", pageSize=page_size, fields=fields, orderBy=order_by)
                .execute()
            )
        except HttpError as e:
            raise ValueError(f"Failed to execute Drive API query: {e}")

    def get_file_metadata(self, file_id: str, fields: str = "*") -> dict[str, Any]:
        """
        Get metadata for a specific file.

        Args:
            file_id: File ID in Google Drive
            fields: Fields to retrieve

        Returns:
            File metadata as dictionary

        Raises:
            HttpError: If API call fails
        """
        self.authenticator.refresh_if_needed()
        try:
            return self.service.files().get(fileId=file_id, fields=fields).execute()
        except HttpError as e:
            raise ValueError(f"Failed to get file metadata for {file_id}: {e}")

    def export_as_media(self, file_id: str, mime_type: str):
        """
        Get export request for a file in specified MIME type.

        Args:
            file_id: File ID in Google Drive
            mime_type: MIME type to export as

        Returns:
            MediaFileUpload object for streaming download

        Raises:
            ValueError: If file cannot be exported to requested MIME type
        """
        self.authenticator.refresh_if_needed()
        try:
            return self.service.files().export_media(fileId=file_id, mimeType=mime_type)
        except HttpError as e:
            raise ValueError(f"Failed to prepare export for {file_id}: {e}")

    def get_file_media(self, file_id: str):
        """
        Get download request for a file.

        Args:
            file_id: File ID in Google Drive

        Returns:
            MediaFileUpload object for streaming download
        """
        self.authenticator.refresh_if_needed()
        return self.service.files().get_media(fileId=file_id)

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
        self.authenticator.refresh_if_needed()
        try:
            request = self.get_file_media(file_id)
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            return file_content.getvalue()
        except HttpError as e:
            raise ValueError(f"Failed to download file {file_id}: {e}")

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
        try:
            # Get file metadata
            file_metadata = self.get_file_metadata(
                document_id,
                fields="id,name,mimeType,createdTime,modifiedTime,webViewLink,owners,description",
            )

            mime_type = file_metadata["mimeType"]
            content = self._download_content(document_id, mime_type)

            if include_metadata:
                markdown_content = self._build_with_frontmatter(file_metadata, mime_type, content)
            else:
                markdown_content = content

            if output_path:
                self._write_file(output_path, markdown_content)

            return markdown_content

        except HttpError as e:
            raise ValueError(f"Failed to export document {document_id}: {e}")

    def _download_content(self, document_id: str, mime_type: str) -> str:
        """
        Download document content based on MIME type.

        Args:
            document_id: The Google Drive document ID
            mime_type: The MIME type of the document

        Returns:
            The document content as a string
        """
        try:
            if mime_type == "application/vnd.google-apps.document":
                request = self.export_as_media(document_id, "text/plain")
            elif mime_type == "text/markdown":
                request = self.get_file_media(document_id)
            elif mime_type.startswith("text/"):
                request = self.get_file_media(document_id)
            else:
                raise ValueError(
                    f"Cannot export file as markdown. Unsupported MIME type: {mime_type}"
                )

            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            return file_content.getvalue().decode("utf-8")

        except HttpError as e:
            raise ValueError(f"Failed to download content for {document_id}: {e}")

    def _build_with_frontmatter(
        self, file_metadata: dict, mime_type: str, content: str
    ) -> str:
        """
        Build markdown content with YAML frontmatter.

        Args:
            file_metadata: File metadata from Drive API
            mime_type: MIME type of the document
            content: Document content

        Returns:
            Markdown with YAML frontmatter
        """
        frontmatter = {
            "title": file_metadata["name"],
            "document_id": file_metadata["id"],
            "mime_type": mime_type,
            "created": file_metadata["createdTime"],
            "modified": file_metadata["modifiedTime"],
            "web_view_link": file_metadata["webViewLink"],
        }

        if "description" in file_metadata:
            frontmatter["description"] = file_metadata["description"]

        if "owners" in file_metadata and file_metadata["owners"]:
            frontmatter["owners"] = [
                owner.get("displayName", owner.get("emailAddress", "Unknown"))
                for owner in file_metadata["owners"]
            ]

        yaml_frontmatter = yaml.dump(
            frontmatter, default_flow_style=False, sort_keys=False
        )
        return f"---\n{yaml_frontmatter}---\n\n{content}"

    def _write_file(self, output_path: str | Path, content: str) -> None:
        """
        Write markdown content to a file, creating parent directories if needed.

        Args:
            output_path: Path where to write the file
            content: Content to write
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def resolve_folder(
        self,
        folder_name: str,
        on_duplicates: Literal["error", "newest"] = "error",
    ) -> str:
        """
        Resolve a folder name to its folder ID.

        Args:
            folder_name: Name of the folder to find
            on_duplicates: How to handle duplicate folder names:
                - "error": Raise an error if multiple folders match
                - "newest": Return the most recently modified folder

        Returns:
            Folder ID string

        Raises:
            ValueError: If no folder found or duplicates found with on_duplicates="error"
        """
        try:
            query = (
                f"mimeType='application/vnd.google-apps.folder' "
                f"and name='{folder_name}' "
                f"and trashed=false"
            )

            results = self.execute_query(
                query,
                fields="files(id, name, modifiedTime)",
                page_size=100,
                order_by="modifiedTime desc",
            )

            folders = results.get("files", [])

            if not folders:
                raise ValueError(f"No folder found with name: {folder_name}")

            if len(folders) > 1 and on_duplicates == "error":
                folder_list = "\n".join(
                    [f"  - {f['name']} (ID: {f['id']})" for f in folders]
                )
                raise ValueError(
                    f"Multiple folders found with name '{folder_name}':\n{folder_list}\n"
                    f"Use folder_id parameter directly or set on_duplicates='newest'"
                )

            return folders[0]["id"]

        except HttpError as e:
            raise ValueError(f"Failed to resolve folder name: {e}")

    def search(
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
            folder_name: Optional folder name to restrict search to (resolved to ID)
            on_duplicates: How to handle duplicate folder names (if folder_name used)

        Returns:
            SearchResult with matching files

        Raises:
            ValueError: If both folder_id and folder_name provided, or folder resolution fails
        """
        target_folder_id = folder_id
        if folder_name:
            if folder_id:
                raise ValueError(
                    "Cannot specify both folder_id and folder_name. Choose one."
                )
            target_folder_id = self.resolve_folder(folder_name, on_duplicates)

        if not target_folder_id:
            target_folder_id = DEFAULT_FOLDER_ID

        # Build Drive API query
        has_operators = any(
            op in query.lower()
            for op in [" = ", " != ", "contains", " in ", " and ", " or "]
        )
        if has_operators:
            drive_query = query
        else:
            drive_query = f"fullText contains '{query}'"

        if target_folder_id:
            drive_query = f"('{target_folder_id}' in parents) and ({drive_query})"

        drive_query = f"{drive_query} and trashed=false"

        try:
            results = self.execute_query(
                drive_query,
                page_size=top_n,
            )

            files_data = results.get("files", [])

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
                folder_id=target_folder_id,
                folder_name=folder_name,
                total_results=len(files),
                files=files,
            )

        except HttpError as e:
            raise ValueError(f"Failed to search Google Drive: {e}")

    def search_ids(
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
        result = self.search(
            query=query,
            top_n=top_n,
            folder_id=folder_id,
            folder_name=folder_name,
            on_duplicates=on_duplicates,
        )
        return [file.id for file in result.files]


__all__ = ["GoogleDrive", "DEFAULT_FOLDER_ID"]
