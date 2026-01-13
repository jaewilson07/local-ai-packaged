"""Approval workflow UI components for Gradio Knowledge Base."""

import gradio as gr


def create_review_panel():
    """
    Create the proposal review panel for article owners.

    Returns:
        Dict of review-related components
    """
    with gr.Column(visible=False, elem_classes=["review-panel"]) as panel:
        gr.Markdown("## 📋 Proposals for Review")
        gr.Markdown(
            "These are proposed edits to your articles. Review and approve, "
            "reject, or request changes."
        )

        # Proposal list
        proposals_list = gr.Dataframe(
            headers=["ID", "Article", "Proposer", "Submitted", "Status"],
            datatype=["str", "str", "str", "str", "str"],
            col_count=(5, "fixed"),
            interactive=False,
            elem_id="proposals-list",
            wrap=True,
        )

        # Refresh button
        btn_refresh_proposals = gr.Button("🔄 Refresh", size="sm")

        # Selected proposal details (shown when a row is clicked)
        with gr.Column(visible=False) as proposal_details:
            gr.Markdown("### Proposal Details")

            proposal_meta = gr.Markdown("")

            with gr.Tabs():
                with gr.TabItem("Side by Side"), gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Original")
                        review_original = gr.Textbox(
                            lines=12,
                            interactive=False,
                            show_label=False,
                        )
                    with gr.Column():
                        gr.Markdown("#### Proposed Changes")
                        review_proposed = gr.Textbox(
                            lines=12,
                            interactive=False,
                            show_label=False,
                        )

                with gr.TabItem("Diff"):
                    review_diff = gr.HTML("", elem_id="review-diff")

            # Reason and sources
            with gr.Accordion("Change Details", open=True):
                change_reason_display = gr.Markdown("")
                supporting_sources_display = gr.Markdown("")

            # Review actions
            gr.Markdown("### Your Decision")

            reviewer_notes = gr.Textbox(
                label="Notes for the proposer (optional)",
                placeholder="Explain your decision or what changes you'd like to see...",
                lines=3,
            )

            with gr.Row():
                btn_approve = gr.Button(
                    "✅ Approve",
                    variant="primary",
                )
                btn_request_changes = gr.Button(
                    "🔄 Request Changes",
                    variant="secondary",
                )
                btn_reject = gr.Button(
                    "❌ Reject",
                    variant="stop",
                )

    return {
        "panel": panel,
        "proposals_list": proposals_list,
        "btn_refresh_proposals": btn_refresh_proposals,
        "proposal_details": proposal_details,
        "proposal_meta": proposal_meta,
        "review_original": review_original,
        "review_proposed": review_proposed,
        "review_diff": review_diff,
        "change_reason_display": change_reason_display,
        "supporting_sources_display": supporting_sources_display,
        "reviewer_notes": reviewer_notes,
        "btn_approve": btn_approve,
        "btn_request_changes": btn_request_changes,
        "btn_reject": btn_reject,
    }


def create_notifications_panel():
    """
    Create the notifications panel.

    Returns:
        Dict of notification-related components
    """
    with gr.Column(visible=False, elem_classes=["notifications-panel"]) as panel:
        with gr.Row():
            gr.Markdown("## 🔔 Notifications")
            unread_badge = gr.Markdown("", elem_id="unread-badge")
            btn_mark_all_read = gr.Button("Mark All Read", size="sm", variant="secondary")

        notifications_list = gr.Dataframe(
            headers=["", "Title", "Message", "Time"],
            datatype=["str", "str", "str", "str"],
            col_count=(4, "fixed"),
            interactive=False,
            elem_id="notifications-list",
            wrap=True,
        )

        btn_refresh_notifications = gr.Button("🔄 Refresh", size="sm")

    return {
        "panel": panel,
        "unread_badge": unread_badge,
        "btn_mark_all_read": btn_mark_all_read,
        "notifications_list": notifications_list,
        "btn_refresh_notifications": btn_refresh_notifications,
    }


def create_my_proposals_panel():
    """
    Create panel showing user's own proposals.

    Returns:
        Dict of proposal tracking components
    """
    with gr.Column(visible=False, elem_classes=["my-proposals-panel"]) as panel:
        gr.Markdown("## 📝 My Proposals")

        # Stats
        with gr.Row():
            stat_pending = gr.Markdown("**Pending:** 0")
            stat_approved = gr.Markdown("**Approved:** 0")
            stat_rejected = gr.Markdown("**Rejected:** 0")

        my_proposals_list = gr.Dataframe(
            headers=["ID", "Article", "Status", "Submitted", "Reviewed"],
            datatype=["str", "str", "str", "str", "str"],
            col_count=(5, "fixed"),
            interactive=False,
            elem_id="my-proposals-list",
            wrap=True,
        )

        btn_refresh_my_proposals = gr.Button("🔄 Refresh", size="sm")

        # Selected proposal details
        with gr.Column(visible=False) as my_proposal_details:
            my_proposal_meta = gr.Markdown("")
            my_proposal_status = gr.Markdown("")
            reviewer_feedback = gr.Markdown("")

            # Option to cancel pending proposal
            with gr.Row(visible=False) as cancel_row:
                btn_cancel_proposal = gr.Button(
                    "🗑️ Cancel Proposal",
                    variant="stop",
                    size="sm",
                )

    return {
        "panel": panel,
        "stat_pending": stat_pending,
        "stat_approved": stat_approved,
        "stat_rejected": stat_rejected,
        "my_proposals_list": my_proposals_list,
        "btn_refresh_my_proposals": btn_refresh_my_proposals,
        "my_proposal_details": my_proposal_details,
        "my_proposal_meta": my_proposal_meta,
        "my_proposal_status": my_proposal_status,
        "reviewer_feedback": reviewer_feedback,
        "cancel_row": cancel_row,
        "btn_cancel_proposal": btn_cancel_proposal,
    }


def format_proposal_for_list(proposal: dict) -> list:
    """Format a proposal for dataframe display."""
    return [
        proposal.get("id", proposal.get("_id", ""))[:8],
        proposal.get("article_title", "Unknown")[:30],
        proposal.get("proposer_email", "").split("@")[0][:15],
        proposal.get("created_at", "")[:10],
        proposal.get("status", "pending").title(),
    ]


def format_notification_for_list(notification: dict) -> list:
    """Format a notification for dataframe display."""
    read_marker = "" if notification.get("read") else "🔵"
    return [
        read_marker,
        notification.get("title", "")[:30],
        notification.get("message", "")[:50],
        notification.get("created_at", "")[:16],
    ]


def format_proposal_meta(proposal: dict) -> str:
    """Format proposal metadata for display."""
    return f"""
**Article:** {proposal.get("article_title", "Unknown")}
**Proposer:** {proposal.get("proposer_email", "Unknown")}
**Submitted:** {proposal.get("created_at", "Unknown")}
**Status:** {proposal.get("status", "pending").title()}
"""


def format_change_reason(proposal: dict) -> str:
    """Format change reason for display."""
    reason = proposal.get("change_reason", "No reason provided")
    return f"**Reason for change:**\n\n{reason}"


def format_supporting_sources(proposal: dict) -> str:
    """Format supporting sources for display."""
    sources = proposal.get("supporting_sources", [])
    if not sources:
        return "*No supporting sources provided*"

    sources_md = "**Supporting Sources:**\n\n"
    for i, url in enumerate(sources, 1):
        sources_md += f"{i}. [{url}]({url})\n"

    return sources_md
