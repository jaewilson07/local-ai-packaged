"""Entity extraction from YouTube video transcripts using LLM."""

import json
import logging
from typing import Any

import openai

from server.projects.youtube_rag.config import config
from server.projects.youtube_rag.models import (
    EntityRelationship,
    ExtractedEntity,
    VideoTranscript,
)

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts entities and relationships from video transcripts using LLM."""

    def __init__(
        self,
        openai_client: openai.AsyncOpenAI | None = None,
        model: str | None = None,
    ):
        """
        Initialize the entity extractor.

        Args:
            openai_client: Optional OpenAI client (creates one if not provided)
            model: LLM model to use for extraction
        """
        self.client = openai_client or openai.AsyncOpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        self.model = model or config.llm_model

    async def extract_entities(
        self,
        transcript: VideoTranscript,
        video_title: str = "",
        video_description: str = "",
        max_entities: int = 20,
    ) -> list[ExtractedEntity]:
        """
        Extract named entities from a video transcript.

        Args:
            transcript: Video transcript
            video_title: Video title for context
            video_description: Video description for additional context
            max_entities: Maximum number of entities to extract

        Returns:
            List of ExtractedEntity objects
        """
        # Prepare the transcript text (truncate if too long)
        transcript_text = transcript.full_text
        if len(transcript_text) > 15000:
            transcript_text = transcript_text[:15000] + "..."

        system_prompt = """You are an expert at extracting named entities from video transcripts.
Extract the most important entities mentioned in the transcript.

Entity types to look for:
- person: People mentioned by name
- organization: Companies, institutions, groups
- product: Products, tools, technologies, software
- location: Places, cities, countries
- concept: Important concepts, theories, methodologies
- event: Events, conferences, launches

For each entity, provide:
- name: The entity name
- entity_type: One of the types above
- mentions: Approximate number of times mentioned
- context: A brief context of how it's discussed

Return a JSON array of entities, ordered by importance/frequency."""

        user_prompt = f"""Video Title: {video_title}

Video Description: {video_description[:500] if video_description else "N/A"}

Transcript:
{transcript_text}

Extract up to {max_entities} important entities from this transcript.
Return as a JSON array with objects containing: name, entity_type, mentions, context"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if not content:
                return []

            result = json.loads(content)

            # Handle both {"entities": [...]} and [...] formats
            entities_data = result.get("entities", result) if isinstance(result, dict) else result

            entities = []
            for entity_data in entities_data[:max_entities]:
                try:
                    entities.append(
                        ExtractedEntity(
                            name=entity_data.get("name", ""),
                            entity_type=entity_data.get("entity_type", "concept"),
                            mentions=entity_data.get("mentions", 1),
                            context=entity_data.get("context"),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error parsing entity: {e}")
                    continue

            return entities

        except Exception as e:
            logger.exception(f"Error extracting entities: {e}")
            return []

    async def extract_relationships(
        self,
        transcript: VideoTranscript,
        entities: list[ExtractedEntity],
        max_relationships: int = 15,
    ) -> list[EntityRelationship]:
        """
        Extract relationships between entities.

        Args:
            transcript: Video transcript
            entities: Previously extracted entities
            max_relationships: Maximum number of relationships to extract

        Returns:
            List of EntityRelationship objects
        """
        if len(entities) < 2:
            return []

        entity_names = [e.name for e in entities[:15]]  # Limit to top 15 entities

        system_prompt = """You are an expert at identifying relationships between entities.
Given a list of entities from a video transcript, identify meaningful relationships between them.

For each relationship, provide:
- source: The source entity name
- target: The target entity name
- relationship: A brief description of how they're related
- confidence: A score from 0 to 1 indicating confidence

Return a JSON array of relationships."""

        user_prompt = f"""Entities found in the video:
{json.dumps(entity_names)}

Transcript excerpt:
{transcript.full_text[:10000]}

Identify up to {max_relationships} meaningful relationships between these entities.
Return as a JSON array with objects containing: source, target, relationship, confidence"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if not content:
                return []

            result = json.loads(content)
            relationships_data = (
                result.get("relationships", result) if isinstance(result, dict) else result
            )

            relationships = []
            for rel_data in relationships_data[:max_relationships]:
                try:
                    relationships.append(
                        EntityRelationship(
                            source=rel_data.get("source", ""),
                            target=rel_data.get("target", ""),
                            relationship=rel_data.get("relationship", "related to"),
                            confidence=float(rel_data.get("confidence", 0.8)),
                        )
                    )
                except Exception as e:
                    logger.warning(f"Error parsing relationship: {e}")
                    continue

            return relationships

        except Exception as e:
            logger.exception(f"Error extracting relationships: {e}")
            return []

    async def extract_key_moments(
        self,
        transcript: VideoTranscript,
        video_title: str = "",
        max_moments: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Extract key moments from the video with timestamps.

        Args:
            transcript: Video transcript with timestamps
            video_title: Video title for context
            max_moments: Maximum number of key moments to extract

        Returns:
            List of key moment dictionaries with timestamp, title, and description
        """
        # Create transcript with timestamps for the LLM
        timestamped_text = []
        for segment in transcript.segments[:500]:  # Limit segments
            minutes = int(segment.start // 60)
            seconds = int(segment.start % 60)
            timestamped_text.append(f"[{minutes:02d}:{seconds:02d}] {segment.text}")

        transcript_with_times = "\n".join(timestamped_text)
        if len(transcript_with_times) > 15000:
            transcript_with_times = transcript_with_times[:15000] + "..."

        system_prompt = """You are an expert at identifying key moments in video content.
Analyze the timestamped transcript and identify the most important moments.

For each key moment, provide:
- timestamp: The timestamp in seconds
- title: A short title for the moment
- description: A brief description of what happens

Focus on:
- Important points or revelations
- Topic transitions
- Notable examples or demonstrations
- Key takeaways or conclusions

Return a JSON array of key moments, ordered chronologically."""

        user_prompt = f"""Video Title: {video_title}

Timestamped Transcript:
{transcript_with_times}

Identify up to {max_moments} key moments from this video.
Return as a JSON array with objects containing: timestamp (in seconds), title, description"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if not content:
                return []

            result = json.loads(content)
            moments_data = (
                result.get("key_moments", result.get("moments", result))
                if isinstance(result, dict)
                else result
            )

            moments = []
            for moment_data in moments_data[:max_moments]:
                try:
                    moments.append(
                        {
                            "timestamp": float(moment_data.get("timestamp", 0)),
                            "title": moment_data.get("title", ""),
                            "description": moment_data.get("description", ""),
                        }
                    )
                except Exception as e:
                    logger.warning(f"Error parsing key moment: {e}")
                    continue

            return moments

        except Exception as e:
            logger.exception(f"Error extracting key moments: {e}")
            return []
