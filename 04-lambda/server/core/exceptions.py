"""Custom exceptions for Lambda server."""

from fastapi import HTTPException, status


class DatabaseConnectionError(HTTPException):
    """Raised when database connection fails."""
    
    def __init__(self, detail: str = "Database connection failed"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class DocumentNotFoundError(HTTPException):
    """Raised when requested document is not found."""
    
    def __init__(self, detail: str = "Document not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class IngestionError(HTTPException):
    """Raised when document ingestion fails."""
    
    def __init__(self, detail: str = "Document ingestion failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class SearchError(HTTPException):
    """Raised when search operation fails."""
    
    def __init__(self, detail: str = "Search operation failed"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

