from pydantic import BaseModel


class MongoCredentials(BaseModel):
    """Credentials for MongoDB user."""

    username: str
    password: str


class ProvisionUserRequest(BaseModel):
    """Request to provision a MongoDB user."""

    email: str
    user_id: str
