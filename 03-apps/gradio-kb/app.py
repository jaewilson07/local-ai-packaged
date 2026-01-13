"""
Gradio Knowledge Base - Interactive Knowledge Refinement System.

A split-screen UI where users ask questions via chat (right), the LLM searches
RAG + web for answers with citations, and cited articles render in an article
viewer (left). Users can propose edits that go through owner approval.
"""

import logging
import os

import gradio as gr
from services.api_client import KnowledgeBaseClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
LAMBDA_API_URL = os.getenv("LAMBDA_API_URL", "http://lambda-server:8000")
GRADIO_SERVER_PORT = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
GRADIO_SERVER_NAME = os.getenv("GRADIO_SERVER_NAME", "0.0.0.0")

# Initialize API client
api_client = KnowledgeBaseClient(base_url=LAMBDA_API_URL)

# Custom CSS for Circle.so/DEV.to-like styling
CUSTOM_CSS = """
/* Main container */
.main-container {
    max-width: 1600px;
    margin: 0 auto;
    padding: 20px;
}

/* Article viewer styling */
.article-viewer {
    background: var(--background-fill-primary);
    border-radius: 12px;
    padding: 24px;
    min-height: 600px;
    overflow-y: auto;
}

.article-viewer h1 {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 16px;
    line-height: 1.3;
}

.article-viewer h2 {
    font-size: 1.5rem;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 12px;
}

.article-viewer p {
    line-height: 1.7;
    margin-bottom: 16px;
}

.article-viewer pre {
    background: var(--neutral-800);
    border-radius: 8px;
    padding: 16px;
    overflow-x: auto;
    margin: 16px 0;
}

.article-viewer code {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 0.9em;
}

/* Article metadata */
.article-meta {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 1px solid var(--border-color-primary);
}

.article-meta .author {
    font-weight: 600;
}

.article-meta .date {
    color: var(--body-text-color-subdued);
}

.article-meta .tags {
    display: flex;
    gap: 8px;
}

.article-meta .tag {
    background: var(--primary-50);
    color: var(--primary-600);
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 0.85rem;
}

/* Chat styling */
.chat-container {
    background: var(--background-fill-primary);
    border-radius: 12px;
    height: 100%;
}

/* Citation styling */
.citation {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: var(--primary-500);
    color: white;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-size: 0.75rem;
    cursor: pointer;
    margin: 0 2px;
    vertical-align: super;
}

.citation:hover {
    background: var(--primary-600);
}

/* Citation list */
.citation-list {
    margin-top: 16px;
    padding: 12px;
    background: var(--background-fill-secondary);
    border-radius: 8px;
}

.citation-item {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    padding: 8px 0;
    border-bottom: 1px solid var(--border-color-primary);
    cursor: pointer;
}

.citation-item:hover {
    background: var(--background-fill-primary);
}

.citation-item:last-child {
    border-bottom: none;
}

/* Proposal diff styling */
.diff-view {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
}

.diff-original, .diff-proposed {
    background: var(--background-fill-secondary);
    border-radius: 8px;
    padding: 16px;
}

.diff-original {
    border-left: 4px solid var(--error-500);
}

.diff-proposed {
    border-left: 4px solid var(--success-500);
}

/* Action buttons */
.action-buttons {
    display: flex;
    gap: 12px;
    margin-top: 16px;
}

/* Empty state */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 400px;
    color: var(--body-text-color-subdued);
}

.empty-state h2 {
    font-size: 1.5rem;
    margin-bottom: 8px;
}

/* Responsive adjustments */
@media (max-width: 1024px) {
    .main-container {
        padding: 12px;
    }
}
"""


def create_app():
    """Create the main Gradio application."""
    with gr.Blocks(
        title="Knowledge Base",
    ) as app:
        # State variables
        current_article = gr.State(value=None)
        chat_history = gr.State(value=[])
        citations = gr.State(value=[])
        proposal_data = gr.State(value=None)

        # Header
        gr.Markdown(
            """
            # 📚 Knowledge Base
            Ask questions, explore articles, and help refine our knowledge together.
            """
        )

        with gr.Row(equal_height=True):
            # Left panel: Article viewer (60%)
            with gr.Column(scale=3, elem_classes=["article-viewer"]):
                article_title = gr.Markdown(
                    "## Select an article or ask a question",
                    elem_id="article-title",
                )
                article_meta = gr.Markdown(
                    "",
                    elem_id="article-meta",
                    visible=False,
                )
                article_content = gr.Markdown(
                    """
                    <div class="empty-state">
                        <h2>No article selected</h2>
                        <p>Ask a question in the chat to get started, or browse articles.</p>
                    </div>
                    """,
                    elem_id="article-content",
                )

                with gr.Row(visible=False) as article_actions:
                    btn_propose_edit = gr.Button(
                        "✏️ Propose Edit",
                        variant="secondary",
                        size="sm",
                    )
                    btn_view_history = gr.Button(
                        "📜 Version History",
                        variant="secondary",
                        size="sm",
                    )
                    btn_refresh = gr.Button(
                        "🔄 Refresh",
                        variant="secondary",
                        size="sm",
                    )

            # Right panel: Chat interface (40%)
            with gr.Column(scale=2, elem_classes=["chat-container"]):
                chatbot = gr.Chatbot(
                    value=[],
                    height=450,
                    show_label=False,
                    elem_id="chatbot",
                )

                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="Ask a question about your knowledge base...",
                        show_label=False,
                        scale=4,
                        container=False,
                    )
                    btn_send = gr.Button("Send", variant="primary", scale=1)

                # Citation panel (shown when citations exist)
                with gr.Accordion("📎 Sources", open=False, visible=False) as citation_accordion:
                    citation_list = gr.Dataframe(
                        headers=["#", "Title", "Source"],
                        datatype=["number", "str", "str"],
                        col_count=(3, "fixed"),
                        interactive=False,
                        elem_id="citation-list",
                    )

        # Proposal modal (hidden by default)
        with gr.Column(visible=False) as proposal_modal:
            gr.Markdown("## Propose Article Edit")
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### Original")
                    original_content = gr.Textbox(
                        lines=10,
                        interactive=False,
                        show_label=False,
                    )
                with gr.Column():
                    gr.Markdown("### Your Proposed Changes")
                    proposed_content = gr.Textbox(
                        lines=10,
                        interactive=True,
                        show_label=False,
                    )

            change_reason = gr.Textbox(
                label="Reason for change",
                placeholder="Explain why this change improves the article...",
                lines=3,
            )
            supporting_sources = gr.Textbox(
                label="Supporting sources (URLs, one per line)",
                placeholder="https://example.com/source1\nhttps://example.com/source2",
                lines=2,
            )

            with gr.Row():
                btn_cancel_proposal = gr.Button("Cancel", variant="secondary")
                btn_submit_proposal = gr.Button("Submit Proposal", variant="primary")

        # ============================================================
        # Event handlers
        # ============================================================

        async def handle_chat_message(message: str, history: list, article_state: dict | None):
            """Handle user chat message."""
            if not message.strip():
                return history, article_state, [], gr.update(visible=False), gr.update()

            # Add user message to history
            history = history + [[message, None]]

            try:
                # Search RAG + web and get response
                response = await api_client.chat_query(message)

                # Extract response text and citations
                answer = response.get("answer", "I couldn't find relevant information.")
                response_citations = response.get("citations", [])

                # Update history with assistant response
                history[-1][1] = answer

                # Format citations for display
                citation_data = []
                for i, cit in enumerate(response_citations, 1):
                    citation_data.append([i, cit.get("title", "Untitled"), cit.get("source", "")])

                # Update citation visibility
                citation_visible = len(citation_data) > 0

                return (
                    history,
                    article_state,
                    response_citations,
                    gr.update(visible=citation_visible),
                    citation_data if citation_data else gr.update(),
                )

            except Exception as e:
                logger.error(f"Chat error: {e}")
                history[-1][1] = f"Sorry, I encountered an error: {e!s}"
                return history, article_state, [], gr.update(visible=False), gr.update()

        async def handle_citation_click(evt: gr.SelectData, citations_state: list):
            """Handle citation click to load article."""
            if not citations_state or evt.index[0] >= len(citations_state):
                return gr.update(), gr.update(), gr.update(), gr.update(visible=False)

            citation = citations_state[evt.index[0]]
            article_id = citation.get("article_id")
            source_url = citation.get("source")

            try:
                # Fetch article content
                if article_id:
                    article = await api_client.get_article(article_id)
                elif source_url:
                    # Fetch external URL content
                    article = await api_client.fetch_url_content(source_url)
                else:
                    return gr.update(), gr.update(), gr.update(), gr.update(visible=False)

                # Format article for display
                title = f"## {article.get('title', 'Untitled')}"
                meta = f"**Author:** {article.get('author_email', 'Unknown')} | **Updated:** {article.get('updated_at', 'Unknown')}"
                content = article.get("content", "No content available.")

                return title, meta, content, gr.update(visible=True), article

            except Exception as e:
                logger.error(f"Article fetch error: {e}")
                return (
                    "## Error Loading Article",
                    "",
                    f"Could not load article: {e!s}",
                    gr.update(visible=False),
                    None,
                )

        async def open_proposal_modal(article_state: dict | None):
            """Open the proposal modal with current article content."""
            if not article_state:
                gr.Warning("No article selected to edit.")
                return gr.update(visible=False), "", "", None

            content = article_state.get("content", "")
            return gr.update(visible=True), content, content, article_state

        def close_proposal_modal():
            """Close the proposal modal."""
            return gr.update(visible=False), "", "", "", ""

        async def submit_proposal(
            article_state: dict | None,
            original: str,
            proposed: str,
            reason: str,
            sources: str,
        ):
            """Submit an edit proposal."""
            if not article_state:
                gr.Warning("No article selected.")
                return gr.update(visible=False), "", "", "", ""

            if original == proposed:
                gr.Warning("No changes detected.")
                return gr.update(visible=True), original, proposed, reason, sources

            if not reason.strip():
                gr.Warning("Please provide a reason for the change.")
                return gr.update(visible=True), original, proposed, reason, sources

            try:
                # Parse supporting sources
                source_list = [s.strip() for s in sources.split("\n") if s.strip()]

                # Submit proposal via API
                result = await api_client.submit_proposal(
                    article_id=article_state.get("_id") or article_state.get("id"),
                    original_content=original,
                    proposed_content=proposed,
                    change_reason=reason,
                    supporting_sources=source_list,
                )

                if result.get("success"):
                    gr.Info("Proposal submitted! The article owner will review your changes.")
                    return gr.update(visible=False), "", "", "", ""
                gr.Warning(f"Failed to submit: {result.get('error', 'Unknown error')}")
                return gr.update(visible=True), original, proposed, reason, sources

            except Exception as e:
                logger.error(f"Proposal submission error: {e}")
                gr.Warning(f"Error submitting proposal: {e!s}")
                return gr.update(visible=True), original, proposed, reason, sources

        # Wire up events
        btn_send.click(
            handle_chat_message,
            inputs=[msg_input, chatbot, current_article],
            outputs=[chatbot, current_article, citations, citation_accordion, citation_list],
        ).then(lambda: "", outputs=[msg_input])

        msg_input.submit(
            handle_chat_message,
            inputs=[msg_input, chatbot, current_article],
            outputs=[chatbot, current_article, citations, citation_accordion, citation_list],
        ).then(lambda: "", outputs=[msg_input])

        citation_list.select(
            handle_citation_click,
            inputs=[citations],
            outputs=[
                article_title,
                article_meta,
                article_content,
                article_actions,
                current_article,
            ],
        )

        btn_propose_edit.click(
            open_proposal_modal,
            inputs=[current_article],
            outputs=[proposal_modal, original_content, proposed_content, proposal_data],
        )

        btn_cancel_proposal.click(
            close_proposal_modal,
            outputs=[
                proposal_modal,
                original_content,
                proposed_content,
                change_reason,
                supporting_sources,
            ],
        )

        btn_submit_proposal.click(
            submit_proposal,
            inputs=[
                proposal_data,
                original_content,
                proposed_content,
                change_reason,
                supporting_sources,
            ],
            outputs=[
                proposal_modal,
                original_content,
                proposed_content,
                change_reason,
                supporting_sources,
            ],
        )

    return app


def main():
    """Run the Gradio application."""
    logger.info(f"Starting Gradio Knowledge Base on {GRADIO_SERVER_NAME}:{GRADIO_SERVER_PORT}")
    app = create_app()

    # In Gradio 6.0, css and theme are passed to launch()
    app.launch(
        server_name=GRADIO_SERVER_NAME,
        server_port=GRADIO_SERVER_PORT,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
