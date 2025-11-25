"""
Bookmark Model
"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Bookmark(Base):
    __tablename__ = "bookmarks"
    __table_args__ = (
        Index("ix_bookmarks_user_browser", "user_id", "browser_id"),
        Index("ix_bookmarks_user_url", "user_id", "url"),
        Index("ix_bookmarks_user_domain", "user_id", "domain"),
        Index("ix_bookmarks_synced_at", "synced_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    # Browser bookmark identifier
    browser_id: Mapped[str] = mapped_column(String(255), index=True)

    # Core fields
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Media
    favicon: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    image: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata (stored as JSON arrays)
    tags: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # User content
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Organization
    folder_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    folder_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    pinned: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    http_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    date_added: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # Original browser timestamp

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="bookmarks")
    collections: Mapped[list["CollectionBookmark"]] = relationship(
        "CollectionBookmark", back_populates="bookmark", cascade="all, delete-orphan"
    )
