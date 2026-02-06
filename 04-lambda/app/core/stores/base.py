"""Base store implementations for common data persistence patterns."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from pymongo import AsyncMongoClient
from pymongo.collection import AsyncCollection

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel")


class BaseMongoStore(ABC, Generic[TModel]):
    """
    Base class for MongoDB-backed stores.
    
    Provides common CRUD operations with type safety and error handling.
    Subclasses define the collection name and data serialization.
    """

    def __init__(self, client: AsyncMongoClient, database: str):
        """
        Initialize store.
        
        Args:
            client: MongoDB async client
            database: Database name
        """
        self.client = client
        self.db = client[database]
        self._collection: AsyncCollection | None = None

    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Return the MongoDB collection name."""
        pass

    @property
    def collection(self) -> AsyncCollection:
        """Get the MongoDB collection."""
        if self._collection is None:
            self._collection = self.db[self.collection_name]
        return self._collection

    @abstractmethod
    def serialize(self, model: TModel) -> dict[str, Any]:
        """
        Serialize model to MongoDB document.
        
        Args:
            model: Model instance
            
        Returns:
            MongoDB document
        """
        pass

    @abstractmethod
    def deserialize(self, document: dict[str, Any]) -> TModel:
        """
        Deserialize MongoDB document to model.
        
        Args:
            document: MongoDB document
            
        Returns:
            Model instance
        """
        pass

    async def get(self, id: str) -> TModel | None:
        """
        Get model by ID.
        
        Args:
            id: Model ID
            
        Returns:
            Model instance or None if not found
        """
        document = await self.collection.find_one({"_id": id})
        if document is None:
            return None
        return self.deserialize(document)

    async def list(self, **filters) -> list[TModel]:
        """
        List models with optional filters.
        
        Args:
            **filters: MongoDB query filters
            
        Returns:
            List of model instances
        """
        cursor = self.collection.find(filters)
        documents = await cursor.to_list(length=None)
        return [self.deserialize(doc) for doc in documents]

    async def create(self, model: TModel) -> str:
        """
        Create new model.
        
        Args:
            model: Model instance
            
        Returns:
            Created model ID
        """
        document = self.serialize(model)
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def update(self, id: str, model: TModel) -> None:
        """
        Update existing model.
        
        Args:
            id: Model ID
            model: Updated model instance
        """
        document = self.serialize(model)
        await self.collection.update_one({"_id": id}, {"$set": document})

    async def delete(self, id: str) -> None:
        """
        Delete model by ID.
        
        Args:
            id: Model ID
        """
        await self.collection.delete_one({"_id": id})

    async def exists(self, id: str) -> bool:
        """
        Check if model exists.
        
        Args:
            id: Model ID
            
        Returns:
            True if model exists
        """
        count = await self.collection.count_documents({"_id": id}, limit=1)
        return count > 0

    async def count(self, **filters) -> int:
        """
        Count models matching filters.
        
        Args:
            **filters: MongoDB query filters
            
        Returns:
            Count of matching models
        """
        return await self.collection.count_documents(filters)
