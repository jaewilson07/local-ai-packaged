"""Google Docs API low-level wrapper."""

import io
from typing import Any

from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from markdownify import markdownify as md

from ..models import GoogleDocumentTab
from .google_drive_api import GoogleDrive
from .google_drive_authenticator import GoogleAuth


class GoogleDoc(GoogleDrive):
    """Low-level wrapper for Google Docs API operations with integrated tab export.

    Inherits from GoogleDrive to access Drive API methods and file operations.
    Provides access to document structure and tabs metadata when available.
    """

    def __init__(self, authenticator: GoogleAuth):
        """
        Initialize Google Docs API client.

        Args:
            authenticator: GoogleAuth instance
        """
        super().__init__(authenticator)
        self.docs_service = build("docs", "v1", credentials=authenticator.get_credentials())

    def get_by_id(self, document_id: str, include_tabs: bool = False) -> dict[str, Any]:
        """Fetch a Google Doc with optional tabs content included.

        Args:
            document_id: The Google Docs document ID
            include_tabs: Attempt to include tabs content/metadata

        Returns:
            Raw Docs API response
        """
        self.authenticator.refresh_if_needed()
        try:
            if include_tabs:
                # Some environments may not support this param; surface errors clearly
                return (
                    self.docs_service.documents()
                    .get(documentId=document_id, includeTabsContent=True)
                    .execute()
                )
            return self.docs_service.documents().get(documentId=document_id).execute()
        except HttpError as e:
            raise ValueError(f"Failed to fetch Docs document {document_id}: {e}")

    def get_tabs_metadata(self, document_id: str) -> list[dict[str, Any]]:
        """Extract tabs metadata list from Docs API response when present.

        Returns an empty list if the response contains no tabs info.
        """
        doc = self.get_by_id(document_id, include_tabs=True)
        tabs = doc.get("tabs") or []
        # Normalize expected keys when present
        normalized: list[dict[str, Any]] = []
        for i, t in enumerate(tabs):
            normalized.append(
                {
                    "tabId": t.get("tabId") or str(i),
                    "title": t.get("title") or f"Tab {i + 1}",
                    "index": t.get("index", i),
                    "parentTabId": t.get("parentTabId"),
                }
            )
        return normalized

    def export_tabs(self, document_id: str) -> list[GoogleDocumentTab]:
        """Export a Google Doc into per-tab markdown sections.

        Strategy mirrors gdrive_sync approach:
        - Export full HTML
        - Split on '<p class="title"' delimiter
        - Extract title/ids from the first title element per chunk
        - Map metadata from Docs API tabs when available

        Args:
            document_id: Google Docs document ID

        Returns:
            List of GoogleDocumentTab models with markdown content
        """
        # Fetch tabs metadata (best-effort)
        tabs_meta = self._safe_get_tabs_metadata(document_id)
        title_to_meta: dict[str, dict[str, Any]] = {
            (t.get("title") or "").strip(): t for t in tabs_meta
        }

        # Fetch document web view link for potential deep links
        file_meta = self.get_file_metadata(
            document_id,
            fields="id,name,webViewLink",
        )
        base_url = file_meta.get("webViewLink")

        # Export full HTML
        html = self._download_html(document_id)
        chunks = self._split_on_title(html)

        tabs: list[GoogleDocumentTab] = []
        for idx, chunk_html in enumerate(chunks):
            title, heading_id = self._extract_title_and_id(chunk_html)
            # Map metadata by title when available
            meta = title_to_meta.get(title or "")
            tab_id = (meta.get("tabId") if meta else None) or heading_id or str(idx)
            parent_tab_id = meta.get("parentTabId") if meta else None

            markdown = md(chunk_html or "")
            tab_url = f"{base_url}#{heading_id}" if base_url and heading_id else None

            tabs.append(
                GoogleDocumentTab(
                    tab_id=str(tab_id),
                    title=title or f"Tab {idx + 1}",
                    index=idx,
                    parent_tab_id=str(parent_tab_id) if parent_tab_id else None,
                    markdown_content=markdown,
                    tab_url=tab_url,
                )
            )

        return tabs

    def _download_html(self, document_id: str) -> str:
        """Download document as HTML (returns ZIP for large docs)."""
        import zipfile

        # Use application/zip as per Google docs - returns a .zip for HTML export
        request = self.export_as_media(document_id, "application/zip")
        buf = io.BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()

        # Extract HTML from the zip file
        buf.seek(0)
        with zipfile.ZipFile(buf, "r") as zip_file:
            # Find the main HTML file (usually the first .html file)
            html_files = [name for name in zip_file.namelist() if name.endswith(".html")]
            if not html_files:
                raise ValueError("No HTML file found in exported ZIP")
            # Read the first HTML file
            with zip_file.open(html_files[0]) as html_file:
                return html_file.read().decode("utf-8", errors="ignore")

    def _split_on_title(self, html: str) -> list[str]:
        """Split HTML on title delimiter."""
        # Split using the known delimiter; discard any pre-title header content
        delimiter = '<p class="title"'
        if delimiter not in html:
            # Fallback: single chunk
            return [html]
        parts = html.split(delimiter)
        # Reattach the delimiter to each subsequent part
        chunks = [f"{delimiter}{p}" for p in parts[1:]]
        return chunks

    def _extract_title_and_id(self, html_chunk: str) -> tuple[str | None, str | None]:
        """Extract title text and heading ID from HTML chunk."""
        soup = BeautifulSoup(html_chunk, "html.parser")
        title_p = soup.find("p", {"class": "title"})
        if not title_p:
            return None, None
        title_text = title_p.get_text(strip=True) if title_p else None
        heading_id = title_p.get("id") or None
        return title_text, heading_id

    def _safe_get_tabs_metadata(self, document_id: str) -> list[dict[str, Any]]:
        """Get tabs metadata with fallback."""
        try:
            return self.get_tabs_metadata(document_id)
        except Exception:
            # If Docs API tabs are unavailable, proceed without metadata
            return []


__all__ = ["GoogleDoc"]
