"""
Backup Service for bookmark snapshots
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import Optional, List
from datetime import datetime

from app.models.backup import BookmarkBackup
from app.models.bookmark import Bookmark


class BackupService:
    """Service for managing bookmark backups and restoration"""

    @staticmethod
    async def create_backup(
        db: AsyncSession, user_id: int, name: str, description: Optional[str] = None
    ) -> BookmarkBackup:
        """
        Create a snapshot of all user's bookmarks

        Args:
            db: Database session
            user_id: User ID
            name: Backup name
            description: Optional description

        Returns:
            Created backup record
        """
        # Get all bookmarks for this user
        result = await db.execute(select(Bookmark).where(Bookmark.user_id == user_id))
        bookmarks = result.scalars().all()

        # Serialize bookmarks to JSON
        snapshot_data = []
        bookmarks_with_tags = 0

        for bm in bookmarks:
            bookmark_dict = {
                "id": bm.id,
                "browser_id": bm.browser_id,
                "url": bm.url,
                "title": bm.title,
                "description": bm.description,
                "domain": bm.domain,
                "favicon": bm.favicon,
                "image": bm.image,
                "tags": bm.tags or [],
                "keywords": bm.keywords or [],
                "notes": bm.notes,
                "folder_name": bm.folder_name,
                "folder_id": bm.folder_id,
                "pinned": bm.pinned,
                "http_status": bm.http_status,
                "date_added": bm.date_added,
                "created_at": bm.created_at.isoformat() if bm.created_at else None,
                "updated_at": bm.updated_at.isoformat() if bm.updated_at else None,
                "synced_at": bm.synced_at.isoformat() if bm.synced_at else None,
                # AI fields
                "ai_tags": bm.ai_tags or [],
                "ai_tags_confidence": bm.ai_tags_confidence or {},
                "ai_category_id": bm.ai_category_id,
                "ai_embedding": bm.ai_embedding,
                "last_ai_analysis_at": bm.last_ai_analysis_at.isoformat()
                if bm.last_ai_analysis_at
                else None,
            }
            snapshot_data.append(bookmark_dict)

            if bm.tags and len(bm.tags) > 0:
                bookmarks_with_tags += 1

        # Create backup record
        backup = BookmarkBackup(
            user_id=user_id,
            name=name,
            description=description,
            snapshot_data={
                "bookmarks": snapshot_data,
                "backup_time": datetime.utcnow().isoformat(),
            },
            total_bookmarks=len(bookmarks),
            bookmarks_with_tags=bookmarks_with_tags,
        )

        db.add(backup)
        await db.commit()
        await db.refresh(backup)

        return backup

    @staticmethod
    async def get_user_backups(
        db: AsyncSession, user_id: int, limit: int = 50
    ) -> List[BookmarkBackup]:
        """Get all backups for a user"""
        result = await db.execute(
            select(BookmarkBackup)
            .where(BookmarkBackup.user_id == user_id)
            .order_by(BookmarkBackup.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_backup(
        db: AsyncSession, backup_id: int, user_id: int
    ) -> Optional[BookmarkBackup]:
        """Get a specific backup"""
        result = await db.execute(
            select(BookmarkBackup).where(
                and_(BookmarkBackup.id == backup_id, BookmarkBackup.user_id == user_id)
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_backup(db: AsyncSession, backup_id: int, user_id: int) -> bool:
        """Delete a backup"""
        result = await db.execute(
            delete(BookmarkBackup).where(
                and_(BookmarkBackup.id == backup_id, BookmarkBackup.user_id == user_id)
            )
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def restore_backup(
        db: AsyncSession, backup_id: int, user_id: int, merge_mode: bool = False
    ) -> dict:
        """
        Restore bookmarks from a backup

        Args:
            db: Database session
            backup_id: Backup ID
            user_id: User ID
            merge_mode: If True, merge with existing bookmarks;
                        If False, delete all existing bookmarks first

        Returns:
            Dictionary with restoration statistics
        """
        # Get backup
        backup = await BackupService.get_backup(db, backup_id, user_id)
        if not backup:
            raise ValueError("Backup not found")

        snapshot_data = backup.snapshot_data.get("bookmarks", [])

        if not merge_mode:
            # Delete all existing bookmarks
            await db.execute(delete(Bookmark).where(Bookmark.user_id == user_id))

        # Restore bookmarks
        restored_count = 0
        skipped_count = 0

        for bookmark_data in snapshot_data:
            browser_id = bookmark_data["browser_id"]

            if merge_mode:
                # Check if bookmark already exists
                existing = await db.execute(
                    select(Bookmark).where(
                        and_(
                            Bookmark.user_id == user_id,
                            Bookmark.browser_id == browser_id,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    skipped_count += 1
                    continue

            # Create or restore bookmark
            bookmark = Bookmark(
                user_id=user_id,
                browser_id=browser_id,
                url=bookmark_data["url"],
                title=bookmark_data["title"],
                description=bookmark_data.get("description"),
                domain=bookmark_data.get("domain"),
                favicon=bookmark_data.get("favicon"),
                image=bookmark_data.get("image"),
                tags=bookmark_data.get("tags", []),
                keywords=bookmark_data.get("keywords", []),
                notes=bookmark_data.get("notes"),
                folder_name=bookmark_data.get("folder_name"),
                folder_id=bookmark_data.get("folder_id"),
                pinned=bookmark_data.get("pinned", 0),
                http_status=bookmark_data.get("http_status"),
                date_added=bookmark_data.get("date_added"),
                # Restore AI fields
                ai_tags=bookmark_data.get("ai_tags", []),
                ai_tags_confidence=bookmark_data.get("ai_tags_confidence", {}),
                ai_category_id=bookmark_data.get("ai_category_id"),
                ai_embedding=bookmark_data.get("ai_embedding"),
                last_ai_analysis_at=bookmark_data.get("last_ai_analysis_at"),
            )
            db.add(bookmark)
            restored_count += 1

        await db.commit()

        return {
            "restored_count": restored_count,
            "skipped_count": skipped_count,
            "total_in_backup": len(snapshot_data),
            "merge_mode": merge_mode,
        }
