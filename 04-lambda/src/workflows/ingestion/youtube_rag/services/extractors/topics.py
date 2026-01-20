"""Topic classification for YouTube videos using LLM."""

import json
import logging

import openai
from workflows.ingestion.youtube_rag.config import config
from workflows.ingestion.youtube_rag.models import VideoMetadata, VideoTranscript

logger = logging.getLogger(__name__)


class TopicExtractor:
    """Classifies topics from video content using LLM."""

    # Predefined topic categories
    TOPIC_CATEGORIES = [
        "Technology",
        "Programming",
        "AI/Machine Learning",
        "Web Development",
        "Data Science",
        "DevOps",
        "Cloud Computing",
        "Cybersecurity",
        "Mobile Development",
        "Game Development",
        "Business",
        "Entrepreneurship",
        "Marketing",
        "Finance",
        "Education",
        "Tutorial",
        "Review",
        "News",
        "Entertainment",
        "Science",
        "Health",
        "Lifestyle",
        "Travel",
        "Food",
        "Sports",
        "Music",
        "Art",
        "Design",
        "Photography",
        "DIY/Crafts",
    ]

    def __init__(
        self,
        openai_client: openai.AsyncOpenAI | None = None,
        model: str | None = None,
    ):
        """
        Initialize the topic extractor.

        Args:
            openai_client: Optional OpenAI client (creates one if not provided)
            model: LLM model to use for classification
        """
        self.client = openai_client or openai.AsyncOpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url,
        )
        self.model = model or config.llm_model

    async def classify_topics(
        self,
        transcript: VideoTranscript | None,
        metadata: VideoMetadata,
        max_topics: int = 5,
        custom_categories: list[str] | None = None,
    ) -> list[str]:
        """
        Classify the video into topic categories.

        Args:
            transcript: Video transcript (optional but recommended)
            metadata: Video metadata including title and description
            max_topics: Maximum number of topics to assign
            custom_categories: Optional custom category list to use instead of defaults

        Returns:
            List of topic strings
        """
        categories = custom_categories or self.TOPIC_CATEGORIES

        # Prepare content for classification
        content_parts = [f"Title: {metadata.title}"]

        if metadata.description:
            content_parts.append(f"Description: {metadata.description[:1000]}")

        if metadata.tags:
            content_parts.append(f"Tags: {', '.join(metadata.tags[:20])}")

        if transcript:
            # Include transcript excerpt
            transcript_text = transcript.full_text
            if len(transcript_text) > 5000:
                transcript_text = transcript_text[:5000] + "..."
            content_parts.append(f"Transcript excerpt: {transcript_text}")

        content = "\n\n".join(content_parts)

        system_prompt = f"""You are an expert content classifier.
Analyze the video content and classify it into the most appropriate topics.

Available topic categories:
{json.dumps(categories)}

Rules:
1. Select 1-{max_topics} topics that best describe the video content
2. Only use topics from the provided category list
3. Order topics by relevance (most relevant first)
4. Be specific - prefer more specific categories when applicable

Return a JSON object with a "topics" array containing the selected topic strings."""

        user_prompt = f"""Classify this video into topics:

{content}

Return up to {max_topics} topics as a JSON object with a "topics" array."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
            )

            result_content = response.choices[0].message.content
            if not result_content:
                return self._fallback_classification(metadata)

            result = json.loads(result_content)
            topics = result.get("topics", [])

            # Validate topics are from the category list
            valid_topics = [t for t in topics if t in categories]

            if not valid_topics:
                return self._fallback_classification(metadata)

            return valid_topics[:max_topics]

        except Exception as e:
            logger.exception(f"Error classifying topics: {e}")
            return self._fallback_classification(metadata)

    def _fallback_classification(self, metadata: VideoMetadata) -> list[str]:
        """
        Fallback classification based on keywords in title/description.

        Args:
            metadata: Video metadata

        Returns:
            List of topics based on keyword matching
        """
        text = f"{metadata.title} {metadata.description}".lower()
        tags_text = " ".join(metadata.tags).lower() if metadata.tags else ""
        combined_text = f"{text} {tags_text}"

        topics = []

        # Keyword mappings
        keyword_map = {
            "Technology": ["tech", "technology", "gadget", "device"],
            "Programming": ["programming", "coding", "code", "developer", "software"],
            "AI/Machine Learning": [
                "ai",
                "artificial intelligence",
                "machine learning",
                "ml",
                "deep learning",
                "neural",
            ],
            "Web Development": [
                "web dev",
                "frontend",
                "backend",
                "javascript",
                "react",
                "vue",
                "html",
                "css",
            ],
            "Tutorial": ["tutorial", "how to", "learn", "guide", "course"],
            "Review": ["review", "unboxing", "comparison", "vs"],
            "Business": ["business", "startup", "company", "entrepreneur"],
            "Education": ["education", "learn", "teaching", "course", "class"],
            "Entertainment": ["entertainment", "funny", "comedy", "vlog"],
        }

        for topic, keywords in keyword_map.items():
            if any(kw in combined_text for kw in keywords):
                topics.append(topic)

        # Return at least one topic
        if not topics:
            topics = ["Education"]  # Default fallback

        return topics[:5]

    async def generate_summary(
        self,
        transcript: VideoTranscript,
        metadata: VideoMetadata,
        max_length: int = 200,
    ) -> str:
        """
        Generate a concise summary of the video content.

        Args:
            transcript: Video transcript
            metadata: Video metadata
            max_length: Maximum summary length in words

        Returns:
            Summary string
        """
        transcript_text = transcript.full_text
        if len(transcript_text) > 10000:
            transcript_text = transcript_text[:10000] + "..."

        system_prompt = """You are an expert at summarizing video content.
Create a concise, informative summary that captures the main points and value of the video.
The summary should be clear, engaging, and help someone decide if they want to watch the full video."""

        user_prompt = f"""Video Title: {metadata.title}

Transcript:
{transcript_text}

Write a summary of this video in approximately {max_length} words.
Focus on the main topics, key points, and any notable insights or conclusions."""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=max_length * 2,  # Approximate tokens
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.exception(f"Error generating summary: {e}")
            return metadata.description[:500] if metadata.description else ""
