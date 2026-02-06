"""Proposal management service for article edits."""

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from app.capabilities.knowledge_graph.knowledge_base.config import config
from app.capabilities.knowledge_graph.knowledge_base.models import (
    ArticleEditProposal,
    ProposalCreateRequest,
    ProposalReviewRequest,
    ProposalStatus,
)
from app.capabilities.knowledge_graph.knowledge_base.services.article_service import ArticleService
from app.capabilities.knowledge_graph.knowledge_base.services.notification_service import (
    NotificationService,
)
from pymongo import AsyncMongoClient

logger = logging.getLogger(__name__)


class ProposalService:
    """Service for managing article edit proposals."""

    def __init__(
        self,
        mongo_client: AsyncMongoClient,
        article_service: ArticleService,
        notification_service: "NotificationService | None" = None,
    ):
        """
        Initialize the proposal service.

        Args:
            mongo_client: MongoDB async client
            article_service: Article service for applying approved changes
            notification_service: Optional notification service
        """
        self.mongo_client = mongo_client
        self.db = mongo_client[config.mongodb_database]
        self.collection = self.db[config.proposals_collection]
        self.article_service = article_service
        self.notification_service = notification_service

    async def create_proposal(
        self,
        request: ProposalCreateRequest,
        proposer_email: str,
    ) -> ArticleEditProposal:
        """
        Create a new edit proposal.

        Args:
            request: Proposal creation request
            proposer_email: Email of the person proposing the edit

        Returns:
            Created proposal
        """
        # Get article info for reference
        article = await self.article_service.get_article(request.article_id)
        if not article:
            raise ValueError(f"Article {request.article_id} not found")

        # Check if proposer is trying to edit their own article
        if article.author_email == proposer_email:
            # Owner can directly edit, but we'll allow proposals for tracking
            logger.info(f"Owner {proposer_email} creating proposal for own article")

        # Check for duplicate pending proposals
        existing = await self.collection.find_one(
            {
                "article_id": request.article_id,
                "proposer_email": proposer_email,
                "status": ProposalStatus.PENDING.value,
            }
        )
        if existing:
            raise ValueError("You already have a pending proposal for this article")

        now = datetime.utcnow()
        proposal_data = {
            "article_id": request.article_id,
            "article_slug": article.slug,
            "article_title": article.title,
            "proposer_email": proposer_email,
            "original_content": request.original_content,
            "proposed_content": request.proposed_content,
            "change_reason": request.change_reason,
            "supporting_sources": request.supporting_sources,
            "status": ProposalStatus.PENDING.value,
            "created_at": now,
            "reviewed_at": None,
            "reviewer_email": None,
            "reviewer_notes": None,
        }

        result = await self.collection.insert_one(proposal_data)
        proposal_data["_id"] = str(result.inserted_id)

        logger.info(f"Created proposal for article {article.slug} by {proposer_email}")

        # Send notification to article owner
        proposal = ArticleEditProposal(**proposal_data)
        if self.notification_service and article.author_email != proposer_email:
            try:
                await self.notification_service.notify_proposal_submitted(
                    proposal=proposal,
                    owner_email=article.author_email,
                    article_title=article.title,
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")

        return proposal

    async def get_proposal(self, proposal_id: str) -> ArticleEditProposal | None:
        """Get a proposal by ID."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(proposal_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return ArticleEditProposal(**doc)
        except Exception as e:
            logger.error(f"Error fetching proposal {proposal_id}: {e}")
        return None

    async def list_user_proposals(
        self,
        user_email: str,
        status: ProposalStatus | None = None,
    ) -> list[ArticleEditProposal]:
        """
        List proposals submitted by a user.

        Args:
            user_email: Email of the proposer
            status: Optional status filter

        Returns:
            List of proposals
        """
        filter_dict: dict[str, Any] = {"proposer_email": user_email}
        if status:
            filter_dict["status"] = status.value

        proposals = []
        async for doc in self.collection.find(filter_dict).sort("created_at", -1):
            doc["_id"] = str(doc["_id"])
            proposals.append(ArticleEditProposal(**doc))

        return proposals

    async def list_proposals_for_review(
        self,
        owner_email: str,
    ) -> list[ArticleEditProposal]:
        """
        List pending proposals for articles owned by a user.

        Args:
            owner_email: Email of the article owner

        Returns:
            List of proposals pending review
        """
        # Get articles owned by user
        articles_cursor = self.article_service.collection.find(
            {"author_email": owner_email},
            {"_id": 1},
        )
        article_ids = [str(doc["_id"]) async for doc in articles_cursor]

        if not article_ids:
            return []

        # Get pending proposals for those articles
        filter_dict = {
            "article_id": {"$in": article_ids},
            "status": {
                "$in": [
                    ProposalStatus.PENDING.value,
                    ProposalStatus.UNDER_REVIEW.value,
                ]
            },
            # Exclude proposals by the owner themselves
            "proposer_email": {"$ne": owner_email},
        }

        proposals = []
        async for doc in self.collection.find(filter_dict).sort("created_at", -1):
            doc["_id"] = str(doc["_id"])
            proposals.append(ArticleEditProposal(**doc))

        return proposals

    async def review_proposal(
        self,
        proposal_id: str,
        request: ProposalReviewRequest,
        reviewer_email: str,
    ) -> ArticleEditProposal:
        """
        Review a proposal (approve, reject, or request changes).

        Args:
            proposal_id: ID of the proposal
            request: Review request with action and notes
            reviewer_email: Email of the reviewer

        Returns:
            Updated proposal

        Raises:
            ValueError: If proposal not found or reviewer not authorized
        """
        proposal = await self.get_proposal(proposal_id)
        if not proposal:
            raise ValueError(f"Proposal {proposal_id} not found")

        # Check if reviewer is the article owner
        article = await self.article_service.get_article(proposal.article_id)
        if not article:
            raise ValueError(f"Article {proposal.article_id} not found")

        if article.author_email != reviewer_email:
            raise ValueError("Only the article owner can review proposals")

        # Determine new status based on action
        if request.action == "approve":
            new_status = ProposalStatus.APPROVED
        elif request.action == "reject":
            new_status = ProposalStatus.REJECTED
        elif request.action == "request_changes":
            new_status = ProposalStatus.NEEDS_REVISION
        else:
            raise ValueError(f"Invalid action: {request.action}")

        now = datetime.utcnow()

        # Update proposal
        await self.collection.update_one(
            {"_id": ObjectId(proposal_id)},
            {
                "$set": {
                    "status": new_status.value,
                    "reviewed_at": now,
                    "reviewer_email": reviewer_email,
                    "reviewer_notes": request.reviewer_notes,
                }
            },
        )

        # If approved, apply the changes to the article
        if new_status == ProposalStatus.APPROVED:
            from capabilities.knowledge_graph.knowledge_base.models import ArticleUpdateRequest

            update_request = ArticleUpdateRequest(
                content=proposal.proposed_content,
                change_reason=f"Approved proposal: {proposal.change_reason}",
            )
            await self.article_service.update_article(
                proposal.article_id,
                update_request,
                editor_email=proposal.proposer_email,
            )
            logger.info(f"Applied approved proposal {proposal_id} to article {proposal.article_id}")

        logger.info(f"Proposal {proposal_id} reviewed by {reviewer_email}: {request.action}")

        # Send notification to proposer
        updated_proposal = await self.get_proposal(proposal_id)
        if self.notification_service:
            try:
                await self.notification_service.notify_proposal_reviewed(
                    proposal=updated_proposal,
                    action=request.action,
                    reviewer_notes=request.reviewer_notes,
                )
            except Exception as e:
                logger.warning(f"Failed to send notification: {e}")

        return updated_proposal

    async def mark_under_review(self, proposal_id: str) -> ArticleEditProposal | None:
        """Mark a proposal as under review when owner views it."""
        await self.collection.update_one(
            {
                "_id": ObjectId(proposal_id),
                "status": ProposalStatus.PENDING.value,
            },
            {"$set": {"status": ProposalStatus.UNDER_REVIEW.value}},
        )
        return await self.get_proposal(proposal_id)

    async def cancel_proposal(
        self,
        proposal_id: str,
        user_email: str,
    ) -> bool:
        """
        Cancel a pending proposal (only by the proposer).

        Args:
            proposal_id: ID of the proposal
            user_email: Email of the user trying to cancel

        Returns:
            True if cancelled successfully
        """
        result = await self.collection.delete_one(
            {
                "_id": ObjectId(proposal_id),
                "proposer_email": user_email,
                "status": ProposalStatus.PENDING.value,
            }
        )
        return result.deleted_count > 0

    async def get_proposal_stats(self, user_email: str) -> dict[str, int]:
        """Get proposal statistics for a user."""
        pipeline = [
            {"$match": {"proposer_email": user_email}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]

        stats = {status.value: 0 for status in ProposalStatus}
        async for doc in self.collection.aggregate(pipeline):
            stats[doc["_id"]] = doc["count"]

        return stats
