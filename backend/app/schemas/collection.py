"""
Collection Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel

from app.models.collection import Permission


class CollectionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_public: Optional[bool] = None


class CollectionResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    is_public: bool
    created_at: datetime
    updated_at: datetime
    bookmark_count: int = 0

    class Config:
        from_attributes = True


class CollectionShareCreate(BaseModel):
    user_id: int
    permission: Permission = Permission.READ


class CollectionShareResponse(BaseModel):
    id: int
    collection_id: int
    user_id: int
    permission: Permission
    created_at: datetime

    class Config:
        from_attributes = True


class CollectionWithBookmarks(CollectionResponse):
    bookmarks: list = []
