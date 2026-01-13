"""Article viewer component for Gradio Knowledge Base."""

import gradio as gr


def format_article_meta(article: dict | None) -> str:
    """Format article metadata for display."""
    if not article:
        return ""

    parts = []

    # Author
    author = article.get("author_email", "Unknown author")
    parts.append(f"**Author:** {author}")

    # Date
    updated = article.get("updated_at")
    if updated:
        # Format date nicely
        if isinstance(updated, str):
            parts.append(f"**Updated:** {updated[:10]}")
        else:
            parts.append(f"**Updated:** {updated}")

    # Source type
    source_type = article.get("source_type")
    if source_type:
        emoji = {
            "circle_so": "🔵",
            "dev_to": "🖥️",
            "reddit": "🔴",
            "gdrive": "📁",
            "manual": "✏️",
            "web_crawl": "🌐",
        }.get(source_type, "📄")
        parts.append(f"{emoji} {source_type}")

    # Version
    version = article.get("version")
    if version:
        parts.append(f"v{version}")

    return " | ".join(parts)


def format_article_tags(tags: list[str] | None) -> str:
    """Format tags as badge-style elements."""
    if not tags:
        return ""

    tag_html = " ".join(f'<span class="tag">#{tag}</span>' for tag in tags)
    return f'<div class="article-tags">{tag_html}</div>'


def create_article_viewer():
    """
    Create the article viewer component.

    Returns:
        Tuple of (container, title, meta, content, actions, state components)
    """
    with gr.Column(elem_classes=["article-viewer"]) as container:
        # Title
        title = gr.Markdown(
            "## Select an article or ask a question",
            elem_id="article-title",
        )

        # Metadata line (author, date, etc.)
        meta = gr.Markdown(
            "",
            elem_id="article-meta",
            visible=False,
        )

        # Tags
        tags = gr.HTML(
            "",
            elem_id="article-tags",
            visible=False,
        )

        # Main content
        content = gr.Markdown(
            """
            <div class="empty-state">
                <h2>No article selected</h2>
                <p>Ask a question in the chat to get started, or browse articles.</p>
            </div>
            """,
            elem_id="article-content",
        )

        # Source URL (if external)
        source_link = gr.Markdown(
            "",
            elem_id="source-link",
            visible=False,
        )

        # Action buttons
        with gr.Row(visible=False) as actions:
            btn_propose_edit = gr.Button(
                "✏️ Propose Edit",
                variant="secondary",
                size="sm",
            )
            btn_view_history = gr.Button(
                "📜 History",
                variant="secondary",
                size="sm",
            )
            btn_view_source = gr.Button(
                "🔗 Source",
                variant="secondary",
                size="sm",
            )
            btn_refresh = gr.Button(
                "🔄 Refresh",
                variant="secondary",
                size="sm",
            )

    return {
        "container": container,
        "title": title,
        "meta": meta,
        "tags": tags,
        "content": content,
        "source_link": source_link,
        "actions": actions,
        "btn_propose_edit": btn_propose_edit,
        "btn_view_history": btn_view_history,
        "btn_view_source": btn_view_source,
        "btn_refresh": btn_refresh,
    }


def update_article_viewer(article: dict | None) -> tuple:
    """
    Update article viewer with new article data.

    Args:
        article: Article data dict or None

    Returns:
        Tuple of updates for (title, meta, tags, content, source_link, actions)
    """
    if not article:
        return (
            gr.update(value="## Select an article or ask a question"),
            gr.update(value="", visible=False),
            gr.update(value="", visible=False),
            gr.update(
                value="""
                <div class="empty-state">
                    <h2>No article selected</h2>
                    <p>Ask a question in the chat to get started.</p>
                </div>
                """
            ),
            gr.update(value="", visible=False),
            gr.update(visible=False),
        )

    # Format title
    title = article.get("title", "Untitled")
    title_md = f"## {title}"

    # Format metadata
    meta_md = format_article_meta(article)

    # Format tags
    tags_html = format_article_tags(article.get("tags"))

    # Get content
    content_md = article.get("content", "No content available.")

    # Format source link
    source_url = article.get("source_url")
    source_md = ""
    if source_url:
        source_md = f"[View original source]({source_url})"

    return (
        gr.update(value=title_md),
        gr.update(value=meta_md, visible=bool(meta_md)),
        gr.update(value=tags_html, visible=bool(tags_html)),
        gr.update(value=content_md),
        gr.update(value=source_md, visible=bool(source_url)),
        gr.update(visible=True),
    )
