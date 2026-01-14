"""Exception hierarchy for Google Drive API operations."""


class GoogleDriveException(Exception):
    """Base exception for Google Drive API operations.
    
    All Google Drive related exceptions should inherit from this class
    to enable consistent error handling patterns.
    """
    
    def __init__(self, message: str, original_error: Exception | None = None):
        """Initialize with message and optional original error.
        
        Args:
            message: Human-readable error description
            original_error: Optional original exception that caused this error
        """
        super().__init__(message)
        self.original_error = original_error


class GoogleDriveAuthError(GoogleDriveException):
    """Authentication or authorization failed for Google Drive API."""
    pass


class GoogleDriveNotFoundError(GoogleDriveException):
    """Requested file or folder was not found in Google Drive."""
    pass


class GoogleDriveExportError(GoogleDriveException):
    """Failed to export or download content from Google Drive."""
    pass


class GoogleDriveSearchError(GoogleDriveException):
    """Failed to execute search query against Google Drive API."""
    pass


class GoogleDriveFolderResolutionError(GoogleDriveException):
    """Failed to resolve folder name to folder ID."""
    pass


__all__ = [
    "GoogleDriveException",
    "GoogleDriveAuthError", 
    "GoogleDriveNotFoundError",
    "GoogleDriveExportError",
    "GoogleDriveSearchError",
    "GoogleDriveFolderResolutionError"
]