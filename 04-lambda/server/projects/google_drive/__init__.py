"""Google Drive integration for searching, exporting, and downloading files.

This service provides a unified interface for:
- Searching files in Google Drive
- Exporting documents as markdown with optional metadata
- Downloading binary files (e.g., LoRA models)
- Resolving folder names to IDs
"""

from .classes import (
    DEFAULT_FOLDER_ID,
    GoogleAuth,
    GoogleDoc,
    GoogleDrive,
)
from .models import GoogleDocumentTab, GoogleDriveFile, SearchResult
from .service import GoogleDriveService

__all__ = [
    "DEFAULT_FOLDER_ID",
    "GoogleAuth",
    "GoogleDoc",
    "GoogleDocumentTab",
    "GoogleDrive",
    "GoogleDriveFile",
    "GoogleDriveService",
    "SearchResult",
]
