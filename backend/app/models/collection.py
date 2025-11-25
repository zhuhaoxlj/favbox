"""
Collection Models for Collaboration
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Permission(str, Enum):
    READ = "read"
    WRITE = "write"


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="collections")
    bookmarks: Mapped[list["CollectionBookmark"]] = relationship(
        "CollectionBookmark", back_populates="collection", cascade="all, delete-orphan"
    )
    shares: Mapped[list["CollectionShare"]] = relationship(
        "CollectionShare", back_populates="collection", cascade="all, delete-orphan"
    )


class CollectionBookmark(Base):
    __tablename__ = "collection_bookmarks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), index=True)
    bookmark_id: Mapped[int] = mapped_column(ForeignKey("bookmarks.id"), index=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="bookmarks")
    bookmark: Mapped["Bookmark"] = relationship("Bookmark", back_populates="collections")


class CollectionShare(Base):
    __tablename__ = "collection_shares"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    permission: Mapped[Permission] = mapped_column(
        SQLEnum(Permission), default=Permission.READ
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Relationships
    collection: Mapped["Collection"] = relationship("Collection", back_populates="shares")
    user: Mapped["User"] = relationship("User", back_populates="shared_collections")
