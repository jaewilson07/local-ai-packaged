"""Chat interface component for Gradio Knowledge Base."""

import gradio as gr


def format_citation_in_text(text: str, citations: list[dict]) -> str:
    """
    Format inline citations in response text.

    Converts [1], [2], etc. to clickable citation markers.
    """
    if not citations:
        return text

    # Replace citation markers with styled spans
    for i, cit in enumerate(citations, 1):
        marker = f"[{i}]"
        styled = f'<span class="citation" data-citation="{i}">{i}</span>'
        text = text.replace(marker, styled)

    return text


def format_citation_list(citations: list[dict]) -> list[list]:
    """Format citations for dataframe display."""
    return [
        [
            i,
            cit.get("title", "Untitled")[:50],
            cit.get("source", "")[:50],
        ]
        for i, cit in enumerate(citations, 1)
    ]


def create_chat_interface():
    """
    Create the chat interface component.

    Returns:
        Dict of chat-related components
    """
    with gr.Column(elem_classes=["chat-container"]) as container:
        # Chat display
        chatbot = gr.Chatbot(
            value=[],
            height=450,
            show_label=False,
            elem_id="chatbot",
            bubble_full_width=False,
            show_copy_button=True,
            render_markdown=True,
        )

        # Input area
        with gr.Row():
            msg_input = gr.Textbox(
                placeholder="Ask a question about your knowledge base...",
                show_label=False,
                scale=4,
                container=False,
                max_lines=3,
            )
            btn_send = gr.Button("Send", variant="primary", scale=1)

        # Quick actions
        with gr.Row():
            btn_clear = gr.Button("🗑️ Clear", size="sm", variant="secondary")
            btn_examples = gr.Button("💡 Examples", size="sm", variant="secondary")

        # Citation accordion (shown when citations exist)
        with gr.Accordion("📎 Sources", open=False, visible=False) as citation_accordion:
            citation_list = gr.Dataframe(
                headers=["#", "Title", "Source"],
                datatype=["number", "str", "str"],
                col_count=(3, "fixed"),
                interactive=False,
                elem_id="citation-list",
                wrap=True,
            )

        # Example queries (hidden by default)
        with gr.Column(visible=False) as examples_panel:
            gr.Markdown("### Example Questions")
            example_queries = gr.Dataset(
                components=[gr.Textbox(visible=False)],
                samples=[
                    ["How do I optimize ETL performance?"],
                    ["What are best practices for data modeling?"],
                    ["How does authentication work in this system?"],
                    ["Explain the architecture overview"],
                    ["What are common troubleshooting steps?"],
                ],
                label="Click an example to use it",
            )

    return {
        "container": container,
        "chatbot": chatbot,
        "msg_input": msg_input,
        "btn_send": btn_send,
        "btn_clear": btn_clear,
        "btn_examples": btn_examples,
        "citation_accordion": citation_accordion,
        "citation_list": citation_list,
        "examples_panel": examples_panel,
        "example_queries": example_queries,
    }


def clear_chat():
    """Clear chat history."""
    return [], [], gr.update(visible=False), []


def toggle_examples(visible: bool):
    """Toggle examples panel visibility."""
    return gr.update(visible=not visible)


def use_example(example: list):
    """Use an example query."""
    if example and len(example) > 0:
        return example[0]
    return ""
