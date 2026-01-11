"""Example queries to test the Linear Researcher agent.

This file contains a collection of interesting queries that demonstrate
different aspects of the research agent's capabilities.
"""

EXAMPLE_QUERIES = [
    # Company/Person queries
    "Who is the CEO of Anthropic?",
    "Who founded OpenAI and when?",
    "What is the current valuation of Anthropic?",
    # Technology queries
    "What is the latest news about LK-99 superconductor?",
    "Explain how quantum computing works",
    "What are the main features of GPT-4?",
    # Scientific queries
    "What is the current status of fusion energy research?",
    "Explain the theory of relativity",
    "What are the health benefits of intermittent fasting?",
    # Current events
    "What are the latest developments in AI safety?",
    "What is happening with climate change in 2024?",
    "What are the current trends in renewable energy?",
    # Technical deep dives
    "How does LangGraph work?",
    "What is the architecture of MongoDB?",
    "Explain the RAG (Retrieval-Augmented Generation) pattern",
]

if __name__ == "__main__":
    """Print example queries."""
    print("Example queries for the Linear Researcher agent:")
    print("=" * 80)
    print()

    for i, query in enumerate(EXAMPLE_QUERIES, 1):
        print(f"{i:2d}. {query}")

    print()
    print("=" * 80)
    print()
    print("To run a query, use:")
    print('  python sample/deep_research/run_research.py "<query>"')
    print()
    print("Example:")
    print('  python sample/deep_research/run_research.py "Who is the CEO of Anthropic?"')
    print()
