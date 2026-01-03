"""
Backup Model for bookmark snapshots
"""

from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class BookmarkBackup(Base):
    """Snapshot of bookmarks before AI processing"""

    __tablename__ = "bookmark_backups"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(String(500), nullable=True)

    # Snapshot data (JSON snapshot of all bookmarks at this time)
    snapshot_data: Mapped[dict] = mapped_column(JSON)

    # Statistics
    total_bookmarks: Mapped[int] = mapped_column(default=0)
    bookmarks_with_tags: Mapped[int] = mapped_column(default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )

    # Relationship
    user: Mapped["User"] = relationship("User", back_populates="backups")
