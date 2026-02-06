"""YouTube client for extracting video data."""

import logging
import re
from urllib.parse import parse_qs, urlparse

from app.workflows.ingestion.youtube_rag.config import config
from app.workflows.ingestion.youtube_rag.models import (
    TranscriptSegment,
    VideoChapter,
    VideoMetadata,
    VideoTranscript,
    YouTubeVideoData,
)

logger = logging.getLogger(__name__)


class YouTubeClientError(Exception):
    """Base exception for YouTube client errors."""


class VideoNotFoundError(YouTubeClientError):
    """Video not found or unavailable."""


class TranscriptNotAvailableError(YouTubeClientError):
    """Transcript not available for this video."""


class YouTubeClient:
    """Client for extracting data from YouTube videos."""

    def __init__(
        self,
        preferred_language: str | None = None,
        fallback_languages: list[str] | None = None,
    ):
        """
        Initialize the YouTube client.

        Args:
            preferred_language: Preferred transcript language code
            fallback_languages: Fallback language codes if preferred not available
        """
        self.preferred_language = preferred_language or config.default_transcript_language
        self.fallback_languages = fallback_languages or config.fallback_languages or ["en"]

    @staticmethod
    def extract_video_id(url: str) -> str:
        """
        Extract video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - https://m.youtube.com/watch?v=VIDEO_ID

        Args:
            url: YouTube URL

        Returns:
            Video ID string

        Raises:
            ValueError: If video ID cannot be extracted
        """
        parsed = urlparse(url)

        # Handle youtu.be short URLs
        if "youtu.be" in parsed.netloc:
            video_id = parsed.path.lstrip("/")
            if video_id:
                # Remove any query parameters or fragments
                return video_id.split("?")[0].split("&")[0]

        # Handle standard youtube.com URLs
        if "youtube.com" in parsed.netloc:
            # Check for /watch?v= format
            if parsed.path == "/watch":
                query_params = parse_qs(parsed.query)
                if "v" in query_params:
                    return query_params["v"][0]

            # Check for /embed/ or /v/ format
            embed_match = re.match(r"^/(embed|v)/([a-zA-Z0-9_-]+)", parsed.path)
            if embed_match:
                return embed_match.group(2)

            # Check for /shorts/ format
            shorts_match = re.match(r"^/shorts/([a-zA-Z0-9_-]+)", parsed.path)
            if shorts_match:
                return shorts_match.group(1)

        raise ValueError(f"Could not extract video ID from URL: {url}")

    async def get_transcript(
        self,
        video_id: str,
        language: str | None = None,
    ) -> VideoTranscript:
        """
        Get the transcript for a video.

        Args:
            video_id: YouTube video ID
            language: Preferred language code (uses default if not specified)

        Returns:
            VideoTranscript object with segments

        Raises:
            TranscriptNotAvailableError: If no transcript is available
        """
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                NoTranscriptFound,
                TranscriptsDisabled,
                VideoUnavailable,
            )
        except ImportError as e:
            raise YouTubeClientError(
                "youtube-transcript-api not installed. Run: pip install youtube-transcript-api"
            ) from e

        preferred = language or self.preferred_language
        languages_to_try = [preferred] + [
            lang for lang in self.fallback_languages if lang != preferred
        ]

        try:
            # First, try to get transcript list to see what's available
            # Note: youtube-transcript-api v1.x requires instantiation
            api = YouTubeTranscriptApi()
            transcript_list = api.list(video_id)

            # Try to find a manually created transcript first
            transcript = None
            is_generated = False

            for lang in languages_to_try:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    is_generated = False
                    break
                except NoTranscriptFound:
                    continue

            # If no manual transcript, try auto-generated
            if transcript is None:
                for lang in languages_to_try:
                    try:
                        transcript = transcript_list.find_generated_transcript([lang])
                        is_generated = True
                        break
                    except NoTranscriptFound:
                        continue

            # If still no transcript, try to get any available and translate
            if transcript is None:
                try:
                    # Get any available transcript
                    available = list(transcript_list)
                    if available:
                        transcript = available[0]
                        is_generated = transcript.is_generated
                        # Try to translate to preferred language
                        if transcript.is_translatable:
                            try:
                                transcript = transcript.translate(preferred)
                            except Exception:
                                pass  # Use original if translation fails
                except Exception:
                    pass

            if transcript is None:
                raise TranscriptNotAvailableError(f"No transcript available for video {video_id}")

            # Fetch the transcript data
            transcript_data = transcript.fetch()
            language_code = transcript.language_code

            # Convert to our model
            # Note: youtube-transcript-api v1.x returns FetchedTranscriptSnippet dataclass objects
            # with .text, .start, .duration attributes (not dicts)
            segments = [
                TranscriptSegment(
                    text=entry.text,
                    start=entry.start,
                    duration=entry.duration,
                )
                for entry in transcript_data
            ]

            return VideoTranscript(
                language=language_code,
                is_generated=is_generated,
                segments=segments,
            )

        except VideoUnavailable as e:
            raise VideoNotFoundError(f"Video {video_id} is unavailable") from e
        except TranscriptsDisabled as e:
            raise TranscriptNotAvailableError(
                f"Transcripts are disabled for video {video_id}"
            ) from e
        except NoTranscriptFound as e:
            raise TranscriptNotAvailableError(f"No transcript found for video {video_id}") from e

    async def get_metadata(self, video_id: str) -> VideoMetadata:
        """
        Get metadata for a video using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            VideoMetadata object

        Raises:
            VideoNotFoundError: If video is not found
            YouTubeClientError: For other errors
        """
        try:
            import yt_dlp
        except ImportError as e:
            raise YouTubeClientError("yt-dlp not installed. Run: pip install yt-dlp") from e

        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info is None:
                raise VideoNotFoundError(f"Video {video_id} not found")

            return VideoMetadata(
                video_id=video_id,
                title=info.get("title", ""),
                description=info.get("description", ""),
                channel_name=info.get("uploader", "") or info.get("channel", ""),
                channel_id=info.get("channel_id", ""),
                upload_date=info.get("upload_date"),
                duration_seconds=info.get("duration", 0) or 0,
                view_count=info.get("view_count"),
                like_count=info.get("like_count"),
                comment_count=info.get("comment_count"),
                tags=info.get("tags", []) or [],
                categories=info.get("categories", []) or [],
                thumbnail_url=info.get("thumbnail"),
                is_live=info.get("is_live", False) or False,
                is_age_restricted=info.get("age_limit", 0) > 0,
            )

        except yt_dlp.utils.DownloadError as e:
            if "Video unavailable" in str(e) or "Private video" in str(e):
                raise VideoNotFoundError(f"Video {video_id} is unavailable or private") from e
            raise YouTubeClientError(f"Error fetching video metadata: {e}") from e

    async def get_chapters(self, video_id: str) -> list[VideoChapter]:
        """
        Get chapter markers from a video using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            List of VideoChapter objects (empty if no chapters)
        """
        try:
            import yt_dlp
        except ImportError:
            logger.warning("yt-dlp not installed, cannot extract chapters")
            return []

        url = f"https://www.youtube.com/watch?v={video_id}"

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "skip_download": True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            if info is None:
                return []

            chapters_data = info.get("chapters", [])
            if not chapters_data:
                return []

            chapters = []
            for chapter in chapters_data:
                chapters.append(
                    VideoChapter(
                        title=chapter.get("title", "Untitled Chapter"),
                        start_time=chapter.get("start_time", 0),
                        end_time=chapter.get("end_time"),
                    )
                )

            return chapters

        except Exception as e:
            logger.warning(f"Error extracting chapters for {video_id}: {e}")
            return []

    async def get_video_data(
        self,
        url: str,
        include_transcript: bool = True,
        include_chapters: bool = True,
        preferred_language: str | None = None,
    ) -> YouTubeVideoData:
        """
        Get complete video data including metadata, transcript, and chapters.

        Args:
            url: YouTube video URL
            include_transcript: Whether to fetch transcript
            include_chapters: Whether to fetch chapters
            preferred_language: Preferred transcript language

        Returns:
            YouTubeVideoData with all extracted information
        """
        video_id = self.extract_video_id(url)
        logger.info(f"Extracting data for video: {video_id}")

        # Get metadata
        metadata = await self.get_metadata(video_id)
        logger.info(f"Got metadata for: {metadata.title}")

        # Get transcript if requested
        transcript = None
        if include_transcript:
            try:
                transcript = await self.get_transcript(video_id, preferred_language)
                logger.info(
                    f"Got transcript: {len(transcript.segments)} segments, "
                    f"language={transcript.language}, generated={transcript.is_generated}"
                )
            except TranscriptNotAvailableError as e:
                logger.warning(f"Transcript not available: {e}")

        # Get chapters if requested
        chapters = []
        if include_chapters:
            chapters = await self.get_chapters(video_id)
            logger.info(f"Got {len(chapters)} chapters")

        return YouTubeVideoData(
            url=url,
            metadata=metadata,
            transcript=transcript,
            chapters=chapters,
        )

    def format_transcript_with_timestamps(
        self,
        transcript: VideoTranscript,
        chapters: list[VideoChapter] | None = None,
    ) -> str:
        """
        Format transcript with timestamps and optional chapter markers.

        Args:
            transcript: The video transcript
            chapters: Optional chapter markers to include

        Returns:
            Formatted transcript string
        """
        lines = []
        chapter_idx = 0
        chapters = chapters or []

        for segment in transcript.segments:
            # Check if we need to add a chapter marker
            while chapter_idx < len(chapters):
                chapter = chapters[chapter_idx]
                if segment.start >= chapter.start_time:
                    if chapter_idx < len(chapters) - 1:
                        next_chapter = chapters[chapter_idx + 1]
                        if segment.start < next_chapter.start_time:
                            lines.append(f"\n## {chapter.title}\n")
                            chapter_idx += 1
                            break
                    else:
                        lines.append(f"\n## {chapter.title}\n")
                        chapter_idx += 1
                        break
                else:
                    break

            # Format timestamp
            minutes = int(segment.start // 60)
            seconds = int(segment.start % 60)
            timestamp = f"[{minutes:02d}:{seconds:02d}]"

            lines.append(f"{timestamp} {segment.text}")

        return "\n".join(lines)
