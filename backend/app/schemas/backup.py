"""
Backup Schemas
"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class BookmarkBackupBase(BaseModel):
    name: str
    description: Optional[str] = None


class BookmarkBackupCreate(BookmarkBackupBase):
    pass


class BookmarkBackupResponse(BookmarkBackupBase):
    id: int
    user_id: int
    total_bookmarks: int
    bookmarks_with_tags: int
    created_at: datetime

    class Config:
        from_attributes = True


class CreateBackupRequest(BaseModel):
    name: str = Field(..., description="备份名称，例如：AI处理前备份")
    description: Optional[str] = Field(None, description="备份描述")


class RestoreBackupRequest(BaseModel):
    backup_id: int = Field(..., description="要还原的备份ID")
    merge_mode: bool = Field(
        False, description="是否合并模式，true=保留当前书签，false=完全覆盖"
    )
