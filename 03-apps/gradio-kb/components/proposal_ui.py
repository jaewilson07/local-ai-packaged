"""Proposal UI components for Gradio Knowledge Base."""

import difflib

import gradio as gr


def generate_diff_html(original: str, proposed: str) -> str:
    """
    Generate HTML diff view between original and proposed content.

    Args:
        original: Original content
        proposed: Proposed content

    Returns:
        HTML string with diff highlighting
    """
    differ = difflib.HtmlDiff(wrapcolumn=80)
    diff_table = differ.make_table(
        original.splitlines(),
        proposed.splitlines(),
        fromdesc="Original",
        todesc="Proposed",
        context=True,
        numlines=3,
    )

    # Add custom styling
    styled_diff = f"""
    <style>
        .diff_header {{
            background-color: var(--neutral-200);
            font-weight: bold;
        }}
        .diff_next {{
            background-color: var(--neutral-100);
        }}
        .diff_add {{
            background-color: var(--success-100);
        }}
        .diff_chg {{
            background-color: var(--warning-100);
        }}
        .diff_sub {{
            background-color: var(--error-100);
        }}
        table.diff {{
            font-family: monospace;
            border-collapse: collapse;
            width: 100%;
        }}
        table.diff td {{
            padding: 4px 8px;
            border: 1px solid var(--border-color-primary);
            vertical-align: top;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
    </style>
    {diff_table}
    """
    return styled_diff


def calculate_change_stats(original: str, proposed: str) -> dict:
    """
    Calculate statistics about the proposed changes.

    Args:
        original: Original content
        proposed: Proposed content

    Returns:
        Dict with change statistics
    """
    original_lines = original.splitlines()
    proposed_lines = proposed.splitlines()

    matcher = difflib.SequenceMatcher(None, original_lines, proposed_lines)
    opcodes = matcher.get_opcodes()

    stats = {
        "lines_added": 0,
        "lines_removed": 0,
        "lines_changed": 0,
        "similarity_ratio": matcher.ratio(),
    }

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == "insert":
            stats["lines_added"] += j2 - j1
        elif tag == "delete":
            stats["lines_removed"] += i2 - i1
        elif tag == "replace":
            stats["lines_changed"] += max(i2 - i1, j2 - j1)

    return stats


def create_proposal_modal():
    """
    Create the proposal submission modal.

    Returns:
        Dict of proposal-related components
    """
    with gr.Column(visible=False, elem_classes=["proposal-modal"]) as modal:
        gr.Markdown("## ✏️ Propose Article Edit")
        gr.Markdown(
            "Your proposed changes will be reviewed by the article owner before being applied."
        )

        # Change statistics (updated dynamically)
        change_stats = gr.Markdown("", elem_id="change-stats")

        # Side-by-side editor
        with gr.Tabs() as edit_tabs:
            with gr.TabItem("Side by Side"), gr.Row():
                with gr.Column():
                    gr.Markdown("### Original Content")
                    original_content = gr.Textbox(
                        lines=15,
                        interactive=False,
                        show_label=False,
                        elem_id="original-content",
                    )
                with gr.Column():
                    gr.Markdown("### Your Proposed Changes")
                    proposed_content = gr.Textbox(
                        lines=15,
                        interactive=True,
                        show_label=False,
                        elem_id="proposed-content",
                        placeholder="Edit the content here...",
                    )

            with gr.TabItem("Diff View"):
                diff_view = gr.HTML(
                    "<p>Make changes in the 'Side by Side' tab to see the diff.</p>",
                    elem_id="diff-view",
                )

        # Change reason
        change_reason = gr.Textbox(
            label="Reason for change",
            placeholder="Explain why this change improves the article (e.g., outdated information, correction, clarification)...",
            lines=3,
            max_lines=5,
        )

        # Supporting sources
        supporting_sources = gr.Textbox(
            label="Supporting sources (optional, one URL per line)",
            placeholder="https://example.com/source1\nhttps://example.com/source2",
            lines=2,
            max_lines=4,
        )

        # Confirmation checkbox
        confirm_checkbox = gr.Checkbox(
            label="I confirm that this change is accurate and improves the article",
            value=False,
        )

        # Action buttons
        with gr.Row():
            btn_cancel = gr.Button("Cancel", variant="secondary")
            btn_preview_diff = gr.Button("Preview Changes", variant="secondary")
            btn_submit = gr.Button("Submit Proposal", variant="primary", interactive=False)

    return {
        "modal": modal,
        "change_stats": change_stats,
        "edit_tabs": edit_tabs,
        "original_content": original_content,
        "proposed_content": proposed_content,
        "diff_view": diff_view,
        "change_reason": change_reason,
        "supporting_sources": supporting_sources,
        "confirm_checkbox": confirm_checkbox,
        "btn_cancel": btn_cancel,
        "btn_preview_diff": btn_preview_diff,
        "btn_submit": btn_submit,
    }


def update_change_stats(original: str, proposed: str) -> str:
    """Generate change statistics markdown."""
    if not original or not proposed:
        return ""

    stats = calculate_change_stats(original, proposed)

    if stats["lines_added"] == 0 and stats["lines_removed"] == 0 and stats["lines_changed"] == 0:
        return "📊 **No changes detected**"

    similarity_pct = int(stats["similarity_ratio"] * 100)
    change_size = "minor" if similarity_pct > 80 else "moderate" if similarity_pct > 50 else "major"

    return f"""📊 **Change Summary:** {change_size.title()} edit ({100 - similarity_pct}% changed)
- ➕ {stats["lines_added"]} lines added
- ➖ {stats["lines_removed"]} lines removed
- 🔄 {stats["lines_changed"]} lines modified"""


def update_diff_view(original: str, proposed: str) -> str:
    """Update the diff view HTML."""
    if not original or not proposed:
        return "<p>No content to compare.</p>"

    if original == proposed:
        return "<p>No changes detected.</p>"

    return generate_diff_html(original, proposed)


def validate_proposal(
    original: str,
    proposed: str,
    reason: str,
    confirmed: bool,
) -> bool:
    """
    Validate proposal can be submitted.

    Returns:
        True if proposal is valid
    """
    if not original or not proposed:
        return False
    if original == proposed:
        return False
    if not reason or len(reason.strip()) < 10:
        return False
    if not confirmed:
        return False
    return True


def update_submit_button(
    original: str,
    proposed: str,
    reason: str,
    confirmed: bool,
) -> gr.update:
    """Update submit button interactivity based on validation."""
    is_valid = validate_proposal(original, proposed, reason, confirmed)
    return gr.update(interactive=is_valid)
