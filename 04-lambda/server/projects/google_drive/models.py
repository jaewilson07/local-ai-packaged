"""Dataclass models for Google Drive resources."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class GoogleDriveFile:
    """Represents a file or folder in Google Drive."""

    id: str
    name: str
    mime_type: str
    created_time: datetime
    modified_time: datetime
    web_view_link: str
    parents: Optional[list[str]] = None
    size: Optional[int] = None
    _raw: Any = field(default=None, repr=False)
    
    @property
    def raw(self) -> Any:
        """Get the raw API response dict for accessing extended attributes."""
        return self._raw
    
    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> GoogleDriveFile:
        """
        Create GoogleDriveFile from API response dictionary.
        
        Args:
            obj: Dictionary containing the API response data
            **kwargs: Additional context
        
        Returns:
            GoogleDriveFile instance
        """
        # Parse datetime fields
        # Handle ISO format with or without timezone
        created_str = obj["createdTime"]
        modified_str = obj["modifiedTime"]
        
        # Replace Z with +00:00 for ISO parsing
        if created_str.endswith("Z"):
            created_str = created_str.replace("Z", "+00:00")
        if modified_str.endswith("Z"):
            modified_str = modified_str.replace("Z", "+00:00")
        
        created_time = datetime.fromisoformat(created_str)
        modified_time = datetime.fromisoformat(modified_str)
        
        return cls(
            id=obj["id"],
            name=obj["name"],
            mime_type=obj["mimeType"],
            created_time=created_time,
            modified_time=modified_time,
            web_view_link=obj["webViewLink"],
            parents=obj.get("parents"),
            size=obj.get("size"),
            _raw=obj,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert file to dictionary (excludes raw)."""
        return {
            "id": self.id,
            "name": self.name,
            "mime_type": self.mime_type,
            "created_time": self.created_time.isoformat(),
            "modified_time": self.modified_time.isoformat(),
            "web_view_link": self.web_view_link,
            "parents": self.parents,
            "size": self.size,
        }


@dataclass
class SearchResult:
    """Result of a Google Drive search query."""

    query: str
    folder_id: Optional[str] = None
    folder_name: Optional[str] = None
    total_results: int = 0
    files: list[GoogleDriveFile] = field(default_factory=list)
    _raw: Any = field(default=None, repr=False)
    
    @property
    def raw(self) -> Any:
        """Get the raw API response for accessing extended attributes."""
        return self._raw
    
    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> SearchResult:
        """
        Create SearchResult from dictionary.
        
        Args:
            obj: Dictionary containing search result data
            **kwargs: Additional context
        
        Returns:
            SearchResult instance
        """
        # Recursively deserialize files
        files = [GoogleDriveFile.from_dict(f) for f in obj.get("files", [])]
        
        return cls(
            query=obj["query"],
            folder_id=obj.get("folder_id"),
            folder_name=obj.get("folder_name"),
            total_results=obj.get("total_results", len(files)),
            files=files,
            _raw=obj,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert search result to dictionary (excludes raw)."""
        return {
            "query": self.query,
            "folder_id": self.folder_id,
            "folder_name": self.folder_name,
            "total_results": self.total_results,
            "files": [f.to_dict() for f in self.files],
        }


@dataclass
class GoogleDocumentTab:
    """Represents a Google Doc tab/section split from exported HTML."""

    tab_id: str
    title: str
    index: int
    markdown_content: str
    parent_tab_id: Optional[str] = None
    tab_url: Optional[str] = None
    _raw: Any = field(default=None, repr=False)
    
    @property
    def raw(self) -> Any:
        """Get the raw data for accessing extended attributes."""
        return self._raw
    
    @classmethod
    def from_dict(cls, obj: dict[str, Any], **kwargs) -> GoogleDocumentTab:
        """
        Create GoogleDocumentTab from dictionary.
        
        Args:
            obj: Dictionary containing tab data
            **kwargs: Additional context
        
        Returns:
            GoogleDocumentTab instance
        """
        return cls(
            tab_id=obj["tab_id"],
            title=obj["title"],
            index=obj["index"],
            markdown_content=obj["markdown_content"],
            parent_tab_id=obj.get("parent_tab_id"),
            tab_url=obj.get("tab_url"),
            _raw=obj,
        )
    
    def to_dict(self) -> dict[str, Any]:
        """Convert tab to dictionary (excludes raw)."""
        return {
            "tab_id": self.tab_id,
            "title": self.title,
            "index": self.index,
            "markdown_content": self.markdown_content,
            "parent_tab_id": self.parent_tab_id,
            "tab_url": self.tab_url,
        }


__all__ = ["GoogleDriveFile", "SearchResult", "GoogleDocumentTab"]
