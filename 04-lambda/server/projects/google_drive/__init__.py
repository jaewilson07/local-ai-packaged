"""Google Drive integration for searching, exporting, and downloading files.

This service provides a unified interface for:
- Searching files in Google Drive
- Exporting documents as markdown with optional metadata
- Downloading binary files (e.g., LoRA models)
- Resolving folder names to IDs
"""

from .classes import (
    GoogleDoc,
    GoogleDrive,
    GoogleAuth,
    DEFAULT_FOLDER_ID,
)
from .models import GoogleDocumentTab, GoogleDriveFile, SearchResult
from .service import GoogleDriveService

__all__ = [
    "GoogleDriveService",
    "GoogleDrive",
    "GoogleAuth",
    "GoogleDoc",
    "GoogleDriveFile",
    "SearchResult",
    "GoogleDocumentTab",
    "DEFAULT_FOLDER_ID",
]
