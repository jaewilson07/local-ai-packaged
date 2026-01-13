"""UI components for Gradio Knowledge Base."""

from components.article_viewer import create_article_viewer
from components.chat_interface import create_chat_interface
from components.proposal_ui import create_proposal_modal

__all__ = ["create_article_viewer", "create_chat_interface", "create_proposal_modal"]
