"""Chapter extraction from YouTube videos."""

import logging
import re

from app.workflows.ingestion.youtube_rag.models import (
    TranscriptSegment,
    VideoChapter,
    VideoTranscript,
)

logger = logging.getLogger(__name__)


class ChapterExtractor:
    """Extracts and processes chapter information from YouTube videos."""

    @staticmethod
    def extract_chapters_from_description(description: str) -> list[VideoChapter]:
        """
        Extract chapter markers from video description.

        Many creators put chapter markers in the description in formats like:
        - 0:00 Introduction
        - 00:00 Introduction
        - 0:00:00 Introduction
        - [0:00] Introduction

        Args:
            description: Video description text

        Returns:
            List of VideoChapter objects
        """
        if not description:
            return []

        # Pattern to match timestamps at the start of lines
        # Supports: 0:00, 00:00, 0:00:00, 00:00:00, [0:00], (0:00)
        timestamp_pattern = re.compile(
            r"^[\[\(]?(\d{1,2}):(\d{2})(?::(\d{2}))?[\]\)]?\s*[-–—:]?\s*(.+?)$",
            re.MULTILINE,
        )

        chapters = []
        matches = list(timestamp_pattern.finditer(description))

        for i, match in enumerate(matches):
            hours_or_minutes = int(match.group(1))
            minutes_or_seconds = int(match.group(2))
            seconds = int(match.group(3)) if match.group(3) else 0

            # Determine if format is H:MM:SS or M:SS
            if match.group(3):  # Has three parts (H:MM:SS)
                start_time = hours_or_minutes * 3600 + minutes_or_seconds * 60 + seconds
            else:  # Two parts (M:SS)
                start_time = hours_or_minutes * 60 + minutes_or_seconds

            title = match.group(4).strip()

            # Calculate end time from next chapter
            end_time = None
            if i + 1 < len(matches):
                next_match = matches[i + 1]
                next_hours_or_minutes = int(next_match.group(1))
                next_minutes_or_seconds = int(next_match.group(2))
                next_seconds = int(next_match.group(3)) if next_match.group(3) else 0

                if next_match.group(3):
                    end_time = (
                        next_hours_or_minutes * 3600 + next_minutes_or_seconds * 60 + next_seconds
                    )
                else:
                    end_time = next_hours_or_minutes * 60 + next_minutes_or_seconds

            chapters.append(
                VideoChapter(
                    title=title,
                    start_time=float(start_time),
                    end_time=float(end_time) if end_time else None,
                )
            )

        return chapters

    @staticmethod
    def get_transcript_for_chapter(
        transcript: VideoTranscript,
        chapter: VideoChapter,
    ) -> list[TranscriptSegment]:
        """
        Get transcript segments that belong to a specific chapter.

        Args:
            transcript: Full video transcript
            chapter: Chapter to get segments for

        Returns:
            List of transcript segments within the chapter
        """
        segments = []
        for segment in transcript.segments:
            # Check if segment starts within chapter bounds
            if segment.start >= chapter.start_time:
                if chapter.end_time is None or segment.start < chapter.end_time:
                    segments.append(segment)
                elif chapter.end_time and segment.start >= chapter.end_time:
                    break

        return segments

    @staticmethod
    def chunk_transcript_by_chapters(
        transcript: VideoTranscript,
        chapters: list[VideoChapter],
    ) -> list[dict]:
        """
        Split transcript into chunks based on chapter boundaries.

        Args:
            transcript: Full video transcript
            chapters: List of chapters

        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not chapters:
            # No chapters, return entire transcript as one chunk
            return [
                {
                    "content": transcript.full_text,
                    "metadata": {
                        "chapter_title": None,
                        "start_time": 0,
                        "end_time": transcript.duration,
                    },
                }
            ]

        chunks = []
        for chapter in chapters:
            segments = ChapterExtractor.get_transcript_for_chapter(transcript, chapter)
            if segments:
                content = " ".join(seg.text for seg in segments)
                chunks.append(
                    {
                        "content": content,
                        "metadata": {
                            "chapter_title": chapter.title,
                            "start_time": chapter.start_time,
                            "end_time": chapter.end_time or segments[-1].end,
                        },
                    }
                )

        return chunks

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        """
        Format seconds as MM:SS or HH:MM:SS.

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"
