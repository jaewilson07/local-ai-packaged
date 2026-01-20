#!/usr/bin/env python3
"""
Sample script demonstrating Q&A using Graphiti RAG on ingested YouTube videos.

This script shows how to:
1. Ask questions about ingested YouTube video content
2. Use Graphiti's temporal knowledge graph for context-aware answers
3. Run a series of test questions to validate the ingestion

Usage:
    python sample/youtube_rag/graphiti_qa.py [--video-id VIDEO_ID] [--interactive]

Examples:
    # Run predefined Q&A test suite
    python sample/youtube_rag/graphiti_qa.py

    # Interactive Q&A mode
    python sample/youtube_rag/graphiti_qa.py --interactive

    # Q&A for specific video
    python sample/youtube_rag/graphiti_qa.py --video-id A3DKwLORVe4
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
lambda_src_path = project_root / "04-lambda" / "src"
sys.path.insert(0, str(lambda_src_path))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Default test questions for YouTube video Q&A
DEFAULT_TEST_QUESTIONS = [
    "What is the main topic of this video?",
    "Who is the creator or presenter of this video?",
    "What are the key concepts discussed in the video?",
    "What tools or technologies are mentioned?",
    "What is the recommended approach or main takeaway?",
]


async def ask_graphiti_question(question: str, video_id: str | None = None) -> str:
    """
    Ask a question using Graphiti RAG.

    Args:
        question: The question to ask
        video_id: Optional video ID to scope the search

    Returns:
        Answer string
    """
    try:
        from capabilities.retrieval.graphiti_rag.dependencies import GraphitiRAGDeps
        from capabilities.retrieval.graphiti_rag.search.graph_search import graphiti_search
    except ImportError:
        return "❌ Graphiti dependencies not available. Install: pip install graphiti-core"

    deps = GraphitiRAGDeps.from_settings()
    await deps.initialize()

    try:
        if not deps.graphiti:
            return "❌ Graphiti not initialized - check NEO4J configuration"

        # Build context-aware query
        if video_id:
            scoped_question = f"In the YouTube video {video_id}: {question}"
        else:
            scoped_question = f"From YouTube videos: {question}"

        # Search Graphiti directly (bypasses RunContext requirement)
        search_results = await graphiti_search(
            graphiti=deps.graphiti,
            query=scoped_question,
            match_count=5,
        )

        if not search_results:
            return "📭 No relevant information found in the knowledge graph."

        # Combine facts into answer
        facts = []
        for result in search_results:
            if result.content:
                # Truncate long content
                content = (
                    result.content[:300] + "..." if len(result.content) > 300 else result.content
                )
                facts.append(f"• {content}")

        if facts:
            return "\n".join(facts)
        return "📭 No specific facts found for this question."

    finally:
        await deps.cleanup()


async def ask_mongodb_question(question: str, video_id: str | None = None) -> str:
    """
    Ask a question using MongoDB RAG (hybrid search).

    Args:
        question: The question to ask
        video_id: Optional video ID to filter by

    Returns:
        Answer string
    """
    try:
        from capabilities.retrieval.mongo_rag.dependencies import AgentDependencies
        from capabilities.retrieval.mongo_rag.tools import semantic_search

        from shared.context_helpers import create_run_context
    except ImportError:
        return "❌ MongoDB RAG dependencies not available"

    deps = AgentDependencies.from_settings()
    await deps.initialize()

    try:
        # Build filter for YouTube source
        filters = {"metadata.source_type": "youtube"}
        if video_id:
            filters["metadata.video_id"] = video_id

        # Create RunContext for tool call
        ctx = create_run_context(deps)

        # Search MongoDB using semantic search
        results = await semantic_search(
            ctx=ctx,
            query=question,
            match_count=5,
            filters=filters,
        )

        if not results or not results.get("results"):
            return "📭 No relevant content found in the knowledge base."

        # Format results
        chunks = []
        for result in results.get("results", []):
            if isinstance(result, dict):
                content = result.get("content", "")[:500]
                score = result.get("similarity", 0)
                chunks.append(f"[Score: {score:.2f}] {content}...")
            else:
                chunks.append(str(result)[:500])

        return "\n\n".join(chunks)

    except Exception as e:
        return f"❌ Error searching MongoDB: {e}"
    finally:
        await deps.cleanup()


async def run_qa_test_suite(
    questions: list[str],
    video_id: str | None = None,
    use_graphiti: bool = True,
) -> list[dict]:
    """
    Run a series of Q&A tests.

    Args:
        questions: List of questions to ask
        video_id: Optional video ID to scope queries
        use_graphiti: Whether to use Graphiti (vs MongoDB)

    Returns:
        List of Q&A results
    """
    print("\n" + "=" * 70)
    print("🎓 YouTube RAG Q&A Test Suite")
    print("=" * 70)
    if video_id:
        print(f"📹 Video ID: {video_id}")
    print(f"🔍 Search Engine: {'Graphiti' if use_graphiti else 'MongoDB'}")
    print(f"❓ Questions: {len(questions)}")
    print("=" * 70)

    results = []

    for i, question in enumerate(questions, 1):
        print(f"\n{'─' * 70}")
        print(f"❓ Question {i}/{len(questions)}:")
        print(f"   {question}")
        print("─" * 70)

        if use_graphiti:
            answer = await ask_graphiti_question(question, video_id)
        else:
            answer = await ask_mongodb_question(question, video_id)

        print("\n💡 Answer:")
        # Indent answer lines
        for line in answer.split("\n"):
            print(f"   {line}")

        results.append(
            {
                "question": question,
                "answer": answer,
                "source": "graphiti" if use_graphiti else "mongodb",
                "video_id": video_id,
            }
        )

    print("\n" + "=" * 70)
    print(f"✅ Q&A Test Complete: {len(results)} questions answered")
    print("=" * 70)

    return results


async def interactive_qa(video_id: str | None = None, use_graphiti: bool = True) -> None:
    """
    Run interactive Q&A session.

    Args:
        video_id: Optional video ID to scope queries
        use_graphiti: Whether to use Graphiti (vs MongoDB)
    """
    print("\n" + "=" * 70)
    print("🎓 Interactive YouTube RAG Q&A")
    print("=" * 70)
    if video_id:
        print(f"📹 Video ID: {video_id}")
    print(f"🔍 Search Engine: {'Graphiti' if use_graphiti else 'MongoDB'}")
    print("\nType 'quit' or 'exit' to end the session.")
    print("Type 'switch' to toggle between Graphiti and MongoDB.")
    print("=" * 70)

    while True:
        try:
            question = input("\n❓ Your question: ").strip()

            if not question:
                continue

            if question.lower() in ["quit", "exit", "q"]:
                print("👋 Goodbye!")
                break

            if question.lower() == "switch":
                use_graphiti = not use_graphiti
                print(f"🔄 Switched to: {'Graphiti' if use_graphiti else 'MongoDB'}")
                continue

            print("\n🔍 Searching...")

            if use_graphiti:
                answer = await ask_graphiti_question(question, video_id)
            else:
                answer = await ask_mongodb_question(question, video_id)

            print("\n💡 Answer:")
            for line in answer.split("\n"):
                print(f"   {line}")

        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Q&A using Graphiti RAG on ingested YouTube videos"
    )
    parser.add_argument(
        "--video-id",
        type=str,
        default=None,
        help="YouTube video ID to scope queries",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Run interactive Q&A session",
    )
    parser.add_argument(
        "--mongodb",
        action="store_true",
        help="Use MongoDB RAG instead of Graphiti",
    )
    parser.add_argument(
        "--questions",
        type=str,
        nargs="+",
        default=None,
        help="Custom questions to ask (space-separated)",
    )

    args = parser.parse_args()

    use_graphiti = not args.mongodb
    questions = args.questions or DEFAULT_TEST_QUESTIONS

    if args.interactive:
        asyncio.run(interactive_qa(args.video_id, use_graphiti))
    else:
        asyncio.run(run_qa_test_suite(questions, args.video_id, use_graphiti))
