"""
MongoDB connection and utilities
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient

from app.core.config import settings


class MongoManager:
    """MongoDB connection manager."""

    def __init__(self):
        self.client: AsyncIOMotorClient = None
        self.database = None

    async def connect_to_mongo(self):
        """Create database connection."""
        self.client = AsyncIOMotorClient(settings.MONGODB_URL)
        self.database = self.client[settings.MONGODB_DB_NAME]

    async def close_mongo_connection(self):
        """Close database connection."""
        if self.client:
            self.client.close()


# Global mongo manager instance
mongo_manager = MongoManager()


async def get_database():
    """Get database instance."""
    return mongo_manager.database


# Synchronous client for migrations and admin tasks
def get_sync_mongo_client():
    """Get synchronous MongoDB client."""
    return MongoClient(settings.MONGODB_URL)
