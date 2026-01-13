"""Notification service for Knowledge Base proposals."""

import logging
from datetime import datetime
from typing import Any

import httpx
from bson import ObjectId
from capabilities.knowledge_graph.knowledge_base.config import config
from capabilities.knowledge_graph.knowledge_base.models import ArticleEditProposal
from pymongo import AsyncMongoClient

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications about proposal activity."""

    def __init__(
        self,
        mongo_client: AsyncMongoClient,
        n8n_webhook_url: str | None = None,
        discord_webhook_url: str | None = None,
    ):
        """
        Initialize the notification service.

        Args:
            mongo_client: MongoDB async client
            n8n_webhook_url: Optional n8n webhook for email notifications
            discord_webhook_url: Optional Discord webhook for notifications
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[config.mongodb_database]
        self.notifications_collection = self.db["notifications"]
        self.n8n_webhook_url = n8n_webhook_url
        self.discord_webhook_url = discord_webhook_url

    async def create_notification(
        self,
        user_email: str,
        notification_type: str,
        title: str,
        message: str,
        related_id: str | None = None,
        related_type: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """
        Create an in-app notification.

        Args:
            user_email: Email of user to notify
            notification_type: Type of notification (proposal_submitted, proposal_reviewed, etc.)
            title: Notification title
            message: Notification message
            related_id: ID of related object (proposal, article, etc.)
            related_type: Type of related object
            metadata: Additional metadata

        Returns:
            Notification ID
        """
        now = datetime.utcnow()
        notification_data = {
            "user_email": user_email,
            "type": notification_type,
            "title": title,
            "message": message,
            "related_id": related_id,
            "related_type": related_type,
            "metadata": metadata or {},
            "read": False,
            "created_at": now,
        }

        result = await self.notifications_collection.insert_one(notification_data)
        return str(result.inserted_id)

    async def get_user_notifications(
        self,
        user_email: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get notifications for a user."""
        filter_dict = {"user_email": user_email}
        if unread_only:
            filter_dict["read"] = False

        notifications = []
        cursor = self.notifications_collection.find(filter_dict).sort("created_at", -1).limit(limit)
        async for doc in cursor:
            doc["_id"] = str(doc["_id"])
            notifications.append(doc)

        return notifications

    async def mark_notification_read(
        self,
        notification_id: str,
        user_email: str,
    ) -> bool:
        """Mark a notification as read."""
        result = await self.notifications_collection.update_one(
            {"_id": ObjectId(notification_id), "user_email": user_email},
            {"$set": {"read": True, "read_at": datetime.utcnow()}},
        )
        return result.modified_count > 0

    async def mark_all_read(self, user_email: str) -> int:
        """Mark all notifications as read for a user."""
        result = await self.notifications_collection.update_many(
            {"user_email": user_email, "read": False},
            {"$set": {"read": True, "read_at": datetime.utcnow()}},
        )
        return result.modified_count

    async def get_unread_count(self, user_email: str) -> int:
        """Get count of unread notifications."""
        return await self.notifications_collection.count_documents(
            {"user_email": user_email, "read": False}
        )

    async def notify_proposal_submitted(
        self,
        proposal: ArticleEditProposal,
        owner_email: str,
        article_title: str,
    ) -> None:
        """Notify article owner when a new proposal is submitted."""
        # Create in-app notification
        await self.create_notification(
            user_email=owner_email,
            notification_type="proposal_submitted",
            title="New Edit Proposal",
            message=f"{proposal.proposer_email} has proposed edits to '{article_title}'",
            related_id=proposal.id,
            related_type="proposal",
            metadata={
                "proposer_email": proposal.proposer_email,
                "article_id": proposal.article_id,
                "article_title": article_title,
            },
        )

        # Send Discord notification if configured
        if self.discord_webhook_url:
            await self._send_discord_notification(
                title="New Edit Proposal",
                description=(
                    f"**{proposal.proposer_email}** has proposed edits to "
                    f"**{article_title}**\n\nReason: {proposal.change_reason[:200]}..."
                ),
                color=0x3498DB,  # Blue
            )

        # Send email via n8n if configured
        if self.n8n_webhook_url:
            await self._send_n8n_webhook(
                event="proposal_submitted",
                data={
                    "owner_email": owner_email,
                    "proposer_email": proposal.proposer_email,
                    "article_title": article_title,
                    "change_reason": proposal.change_reason,
                    "proposal_id": proposal.id,
                },
            )

        logger.info(f"Sent proposal notification to {owner_email}")

    async def notify_proposal_reviewed(
        self,
        proposal: ArticleEditProposal,
        action: str,
        reviewer_notes: str | None = None,
    ) -> None:
        """Notify proposer when their proposal is reviewed."""
        action_labels = {
            "approve": (
                "Proposal Approved",
                "Your proposal has been approved and applied!",
                0x2ECC71,
            ),
            "reject": ("Proposal Rejected", "Your proposal was not accepted.", 0xE74C3C),
            "request_changes": (
                "Changes Requested",
                "The article owner has requested changes.",
                0xF1C40F,
            ),
        }

        title, default_msg, color = action_labels.get(
            action,
            ("Proposal Updated", "Your proposal status has changed.", 0x95A5A6),
        )

        message = reviewer_notes or default_msg

        # Create in-app notification
        await self.create_notification(
            user_email=proposal.proposer_email,
            notification_type=f"proposal_{action}",
            title=title,
            message=message,
            related_id=proposal.id,
            related_type="proposal",
            metadata={
                "action": action,
                "reviewer_email": proposal.reviewer_email,
                "article_id": proposal.article_id,
            },
        )

        # Send Discord notification if configured
        if self.discord_webhook_url:
            await self._send_discord_notification(
                title=title,
                description=f"Proposal by **{proposal.proposer_email}**\n\n{message}",
                color=color,
            )

        # Send email via n8n if configured
        if self.n8n_webhook_url:
            await self._send_n8n_webhook(
                event=f"proposal_{action}",
                data={
                    "proposer_email": proposal.proposer_email,
                    "reviewer_email": proposal.reviewer_email,
                    "article_title": proposal.article_title,
                    "action": action,
                    "reviewer_notes": reviewer_notes,
                    "proposal_id": proposal.id,
                },
            )

        logger.info(f"Sent review notification to {proposal.proposer_email}: {action}")

    async def _send_discord_notification(
        self,
        title: str,
        description: str,
        color: int = 0x3498DB,
    ) -> None:
        """Send notification to Discord webhook."""
        if not self.discord_webhook_url:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.discord_webhook_url,
                    json={
                        "embeds": [
                            {
                                "title": title,
                                "description": description,
                                "color": color,
                                "footer": {"text": "Knowledge Base"},
                                "timestamp": datetime.utcnow().isoformat(),
                            }
                        ]
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to send Discord notification: {e}")

    async def _send_n8n_webhook(
        self,
        event: str,
        data: dict[str, Any],
    ) -> None:
        """Send notification via n8n webhook."""
        if not self.n8n_webhook_url:
            return

        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    self.n8n_webhook_url,
                    json={
                        "event": event,
                        "timestamp": datetime.utcnow().isoformat(),
                        **data,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to send n8n webhook: {e}")
