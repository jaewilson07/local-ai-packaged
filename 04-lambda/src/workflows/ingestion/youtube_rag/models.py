"""Pydantic models for YouTube RAG project."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class TranscriptSegment(BaseModel):
    """A segment of the video transcript with timing information."""

    text: str = Field(..., description="The transcript text for this segment")
    start: float = Field(..., description="Start time in seconds")
    duration: float = Field(..., description="Duration in seconds")
    end: float = Field(default=0.0, description="End time in seconds (calculated)")

    def model_post_init(self, __context: Any) -> None:
        """Calculate end time from start and duration."""
        if self.end == 0.0:
            object.__setattr__(self, "end", self.start + self.duration)


class VideoChapter(BaseModel):
    """A chapter marker in the video."""

    title: str = Field(..., description="Chapter title")
    start_time: float = Field(..., description="Chapter start time in seconds")
    end_time: float | None = Field(default=None, description="Chapter end time in seconds")


class ExtractedEntity(BaseModel):
    """An entity extracted from the video content."""

    name: str = Field(..., description="Entity name")
    entity_type: str = Field(
        ..., description="Entity type (person, organization, product, location, concept)"
    )
    mentions: int = Field(default=1, description="Number of mentions in the transcript")
    context: str | None = Field(default=None, description="Context where entity was mentioned")
    timestamp: float | None = Field(default=None, description="First mention timestamp in seconds")


class EntityRelationship(BaseModel):
    """A relationship between two entities."""

    source: str = Field(..., description="Source entity name")
    target: str = Field(..., description="Target entity name")
    relationship: str = Field(..., description="Relationship type/description")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")


class VideoMetadata(BaseModel):
    """Metadata about a YouTube video."""

    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    description: str = Field(default="", description="Video description")
    channel_name: str = Field(default="", description="Channel name")
    channel_id: str = Field(default="", description="Channel ID")
    upload_date: str | None = Field(default=None, description="Upload date (YYYYMMDD format)")
    duration_seconds: int = Field(default=0, description="Video duration in seconds")
    view_count: int | None = Field(default=None, description="Number of views")
    like_count: int | None = Field(default=None, description="Number of likes")
    comment_count: int | None = Field(default=None, description="Number of comments")
    tags: list[str] = Field(default_factory=list, description="Video tags")
    categories: list[str] = Field(default_factory=list, description="Video categories")
    thumbnail_url: str | None = Field(default=None, description="Thumbnail URL")
    is_live: bool = Field(default=False, description="Whether this is a live stream")
    is_age_restricted: bool = Field(default=False, description="Age restriction status")


class VideoTranscript(BaseModel):
    """The full transcript of a video."""

    language: str = Field(..., description="Transcript language code")
    is_generated: bool = Field(default=False, description="Whether auto-generated")
    segments: list[TranscriptSegment] = Field(
        default_factory=list, description="Transcript segments"
    )

    @property
    def full_text(self) -> str:
        """Get the full transcript as plain text."""
        return " ".join(seg.text for seg in self.segments)

    @property
    def duration(self) -> float:
        """Get total duration from segments."""
        if not self.segments:
            return 0.0
        return self.segments[-1].end


class YouTubeVideoData(BaseModel):
    """Complete data extracted from a YouTube video."""

    url: str = Field(..., description="Original YouTube URL")
    metadata: VideoMetadata = Field(..., description="Video metadata")
    transcript: VideoTranscript | None = Field(default=None, description="Video transcript")
    chapters: list[VideoChapter] = Field(default_factory=list, description="Video chapters")
    entities: list[ExtractedEntity] = Field(default_factory=list, description="Extracted entities")
    relationships: list[EntityRelationship] = Field(
        default_factory=list, description="Entity relationships"
    )
    topics: list[str] = Field(default_factory=list, description="Classified topics")
    key_moments: list[dict[str, Any]] = Field(
        default_factory=list, description="Key moments with timestamps"
    )
    extracted_at: datetime = Field(default_factory=datetime.now, description="Extraction timestamp")


# Request/Response Models


class IngestYouTubeRequest(BaseModel):
    """Request to ingest a YouTube video."""

    url: str = Field(..., description="YouTube video URL")
    extract_chapters: bool = Field(default=True, description="Extract chapter markers")
    extract_entities: bool = Field(default=False, description="Extract entities using LLM")
    extract_topics: bool = Field(default=False, description="Classify topics using LLM")
    extract_key_moments: bool = Field(default=False, description="Extract key moments using LLM")
    chunk_by_chapters: bool = Field(
        default=True, description="Chunk transcript by chapters if available"
    )
    chunk_size: int = Field(default=1000, ge=100, le=5000, description="Chunk size for splitting")
    chunk_overlap: int = Field(default=200, ge=0, le=500, description="Chunk overlap size")
    preferred_language: str | None = Field(
        default=None, description="Preferred transcript language"
    )

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that the URL is a YouTube URL."""
        valid_hosts = [
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "m.youtube.com",
        ]
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if not any(host in parsed.netloc for host in valid_hosts):
            raise ValueError("URL must be a valid YouTube URL")
        return v


class IngestYouTubeResponse(BaseModel):
    """Response from ingesting a YouTube video."""

    success: bool = Field(..., description="Whether ingestion succeeded")
    url: str = Field(..., description="Original YouTube URL")
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(default="", description="Video title")
    document_id: str | None = Field(default=None, description="MongoDB document ID")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    transcript_language: str | None = Field(default=None, description="Transcript language used")
    chapters_found: int = Field(default=0, description="Number of chapters found")
    entities_extracted: int = Field(default=0, description="Number of entities extracted")
    topics_classified: list[str] = Field(default_factory=list, description="Classified topics")
    processing_time_ms: float = Field(default=0, description="Processing time in milliseconds")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")


class GetYouTubeMetadataRequest(BaseModel):
    """Request to get YouTube video metadata without ingesting."""

    url: str = Field(..., description="YouTube video URL")
    include_transcript: bool = Field(default=False, description="Include transcript in response")

    @field_validator("url")
    @classmethod
    def validate_youtube_url(cls, v: str) -> str:
        """Validate that the URL is a YouTube URL."""
        valid_hosts = [
            "youtube.com",
            "www.youtube.com",
            "youtu.be",
            "m.youtube.com",
        ]
        from urllib.parse import urlparse

        parsed = urlparse(v)
        if not any(host in parsed.netloc for host in valid_hosts):
            raise ValueError("URL must be a valid YouTube URL")
        return v


class GetYouTubeMetadataResponse(BaseModel):
    """Response containing YouTube video metadata."""

    success: bool = Field(..., description="Whether metadata retrieval succeeded")
    url: str = Field(..., description="Original YouTube URL")
    metadata: VideoMetadata | None = Field(default=None, description="Video metadata")
    transcript: VideoTranscript | None = Field(default=None, description="Video transcript")
    chapters: list[VideoChapter] = Field(default_factory=list, description="Video chapters")
    errors: list[str] = Field(default_factory=list, description="Any errors encountered")


class SearchYouTubeRequest(BaseModel):
    """Request to search YouTube videos in the knowledge base."""

    query: str = Field(..., description="Search query")
    match_count: int = Field(default=5, ge=1, le=50, description="Number of results")
    search_type: Literal["semantic", "text", "hybrid"] = Field(
        default="hybrid", description="Search type"
    )
    channel_filter: str | None = Field(default=None, description="Filter by channel name")
    min_duration: int | None = Field(default=None, description="Minimum duration in seconds")
    max_duration: int | None = Field(default=None, description="Maximum duration in seconds")
