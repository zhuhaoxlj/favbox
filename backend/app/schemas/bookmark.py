"""
Bookmark Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class BookmarkBase(BaseModel):
    browser_id: str
    url: str
    title: str
    description: Optional[str] = None
    domain: Optional[str] = None
    favicon: Optional[str] = None
    image: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    keywords: Optional[list[str]] = Field(default_factory=list)
    notes: Optional[str] = None
    folder_name: Optional[str] = None
    folder_id: Optional[str] = None
    pinned: int = 0
    http_status: Optional[int] = None
    date_added: Optional[int] = None


class BookmarkCreate(BookmarkBase):
    pass


class BookmarkUpdate(BaseModel):
    url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    domain: Optional[str] = None
    favicon: Optional[str] = None
    image: Optional[str] = None
    tags: Optional[list[str]] = None
    keywords: Optional[list[str]] = None
    notes: Optional[str] = None
    folder_name: Optional[str] = None
    folder_id: Optional[str] = None
    pinned: Optional[int] = None
    http_status: Optional[int] = None


class BookmarkResponse(BookmarkBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    synced_at: datetime

    class Config:
        from_attributes = True


class BookmarkSync(BaseModel):
    """For sync operations"""
    browser_id: str
    url: str
    title: str
    description: Optional[str] = None
    domain: Optional[str] = None
    favicon: Optional[str] = None
    image: Optional[str] = None
    tags: Optional[list[str]] = Field(default_factory=list)
    keywords: Optional[list[str]] = Field(default_factory=list)
    notes: Optional[str] = None
    folder_name: Optional[str] = None
    folder_id: Optional[str] = None
    pinned: int = 0
    http_status: Optional[int] = None
    date_added: Optional[int] = None
    updated_at: Optional[datetime] = None  # Client's last update time
    deleted: bool = False  # For incremental sync - mark as deleted


class SyncRequest(BaseModel):
    """Full sync request from client"""
    bookmarks: list[BookmarkSync]
    client_timestamp: datetime


class IncrementalSyncRequest(BaseModel):
    """Incremental sync - only changes since last sync"""
    changes: list[BookmarkSync]
    last_sync_at: datetime


class SyncResponse(BaseModel):
    """Sync response to client"""
    bookmarks: list[BookmarkResponse]
    server_timestamp: datetime
    conflicts: list[dict] = Field(default_factory=list)
