"""
Bookmark Sync API Routes
"""
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.database import get_db
from app.models.user import User
from app.models.bookmark import Bookmark
from app.schemas.bookmark import (
    BookmarkCreate,
    BookmarkUpdate,
    BookmarkResponse,
    SyncRequest,
    IncrementalSyncRequest,
    SyncResponse,
)
from app.api.deps import get_current_user
from app.utils.websocket_manager import manager

router = APIRouter(prefix="/bookmarks", tags=["Bookmarks"])


@router.get("", response_model=list[BookmarkResponse])
async def get_bookmarks(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 1000,
):
    """Get all bookmarks for current user"""
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .order_by(Bookmark.created_at.desc())
    )
    return result.scalars().all()


@router.get("/changes", response_model=list[BookmarkResponse])
async def get_changes(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    since: datetime = Query(..., description="Get changes since this timestamp"),
):
    """Get bookmarks changed since a specific time (for incremental sync)"""
    result = await db.execute(
        select(Bookmark)
        .where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.synced_at > since,
            )
        )
        .order_by(Bookmark.synced_at.desc())
    )
    return result.scalars().all()


@router.post("/sync", response_model=SyncResponse)
async def full_sync(
    sync_data: SyncRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Full sync: Client sends all bookmarks, server merges and returns final state
    Uses Last-Write-Wins strategy based on updated_at timestamp
    """
    server_timestamp = datetime.now(timezone.utc)
    conflicts = []

    # Get existing bookmarks indexed by browser_id
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == current_user.id)
    )
    existing_bookmarks = {b.browser_id: b for b in result.scalars().all()}

    # Process client bookmarks
    for client_bookmark in sync_data.bookmarks:
        if client_bookmark.browser_id in existing_bookmarks:
            # Update existing bookmark
            db_bookmark = existing_bookmarks[client_bookmark.browser_id]

            # Check for conflict (both modified since last sync)
            client_updated = client_bookmark.updated_at or sync_data.client_timestamp

            # Ensure both datetimes are timezone-aware for comparison
            if client_updated.tzinfo is None:
                client_updated = client_updated.replace(tzinfo=timezone.utc)

            db_updated = db_bookmark.updated_at
            if db_updated.tzinfo is None:
                db_updated = db_updated.replace(tzinfo=timezone.utc)

            if db_updated > client_updated:
                # Server version is newer, keep server version but log conflict
                conflicts.append({
                    "browser_id": client_bookmark.browser_id,
                    "reason": "server_newer",
                    "server_updated_at": db_bookmark.updated_at.isoformat(),
                    "client_updated_at": client_updated.isoformat(),
                })
            else:
                # Client version is newer or same, update server
                for field in [
                    "url", "title", "description", "domain", "favicon", "image",
                    "tags", "keywords", "notes", "folder_name", "folder_id",
                    "pinned", "http_status", "date_added"
                ]:
                    value = getattr(client_bookmark, field, None)
                    if value is not None:
                        setattr(db_bookmark, field, value)
                db_bookmark.synced_at = server_timestamp
        else:
            # Create new bookmark
            db_bookmark = Bookmark(
                user_id=current_user.id,
                browser_id=client_bookmark.browser_id,
                url=client_bookmark.url,
                title=client_bookmark.title,
                description=client_bookmark.description,
                domain=client_bookmark.domain,
                favicon=client_bookmark.favicon,
                image=client_bookmark.image,
                tags=client_bookmark.tags or [],
                keywords=client_bookmark.keywords or [],
                notes=client_bookmark.notes,
                folder_name=client_bookmark.folder_name,
                folder_id=client_bookmark.folder_id,
                pinned=client_bookmark.pinned,
                http_status=client_bookmark.http_status,
                date_added=client_bookmark.date_added,
                synced_at=server_timestamp,
            )
            db.add(db_bookmark)

    # Bookmarks only on server (deleted on client) - keep them for now
    # In a full sync, we don't delete server bookmarks

    await db.commit()

    # Get final state
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == current_user.id)
    )
    all_bookmarks = result.scalars().all()

    return SyncResponse(
        bookmarks=all_bookmarks,
        server_timestamp=server_timestamp,
        conflicts=conflicts,
    )


@router.post("/sync/incremental", response_model=SyncResponse)
async def incremental_sync(
    sync_data: IncrementalSyncRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Incremental sync: Client sends only changes since last sync
    Supports create, update, and delete operations
    """
    server_timestamp = datetime.now(timezone.utc)
    conflicts = []

    for change in sync_data.changes:
        result = await db.execute(
            select(Bookmark).where(
                and_(
                    Bookmark.user_id == current_user.id,
                    Bookmark.browser_id == change.browser_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if change.deleted:
            # Delete bookmark
            if existing:
                await db.delete(existing)
                # Broadcast delete to other devices
                await manager.broadcast_to_user(
                    current_user.id,
                    {
                        "type": "bookmark_deleted",
                        "browser_id": change.browser_id,
                        "timestamp": server_timestamp.isoformat(),
                    }
                )
        elif existing:
            # Update existing
            client_updated = change.updated_at or server_timestamp
            if existing.updated_at <= client_updated:
                for field in [
                    "url", "title", "description", "domain", "favicon", "image",
                    "tags", "keywords", "notes", "folder_name", "folder_id",
                    "pinned", "http_status", "date_added"
                ]:
                    value = getattr(change, field, None)
                    if value is not None:
                        setattr(existing, field, value)
                existing.synced_at = server_timestamp

                # Broadcast update to other devices
                await manager.broadcast_to_user(
                    current_user.id,
                    {
                        "type": "bookmark_updated",
                        "bookmark": BookmarkResponse.model_validate(existing).model_dump(mode="json"),
                        "timestamp": server_timestamp.isoformat(),
                    }
                )
            else:
                conflicts.append({
                    "browser_id": change.browser_id,
                    "reason": "server_newer",
                })
        else:
            # Create new
            new_bookmark = Bookmark(
                user_id=current_user.id,
                browser_id=change.browser_id,
                url=change.url,
                title=change.title,
                description=change.description,
                domain=change.domain,
                favicon=change.favicon,
                image=change.image,
                tags=change.tags or [],
                keywords=change.keywords or [],
                notes=change.notes,
                folder_name=change.folder_name,
                folder_id=change.folder_id,
                pinned=change.pinned,
                http_status=change.http_status,
                date_added=change.date_added,
                synced_at=server_timestamp,
            )
            db.add(new_bookmark)
            await db.flush()

            # Broadcast create to other devices
            await manager.broadcast_to_user(
                current_user.id,
                {
                    "type": "bookmark_created",
                    "bookmark": BookmarkResponse.model_validate(new_bookmark).model_dump(mode="json"),
                    "timestamp": server_timestamp.isoformat(),
                }
            )

    await db.commit()

    # Return changes from server since client's last sync
    result = await db.execute(
        select(Bookmark).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.synced_at > sync_data.last_sync_at,
            )
        )
    )
    server_changes = result.scalars().all()

    return SyncResponse(
        bookmarks=server_changes,
        server_timestamp=server_timestamp,
        conflicts=conflicts,
    )


@router.post("", response_model=BookmarkResponse, status_code=status.HTTP_201_CREATED)
async def create_bookmark(
    bookmark_data: BookmarkCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a single bookmark"""
    bookmark = Bookmark(
        user_id=current_user.id,
        **bookmark_data.model_dump(),
    )
    db.add(bookmark)
    await db.commit()
    await db.refresh(bookmark)

    # Broadcast to other devices
    await manager.broadcast_to_user(
        current_user.id,
        {
            "type": "bookmark_created",
            "bookmark": BookmarkResponse.model_validate(bookmark).model_dump(mode="json"),
        }
    )

    return bookmark


@router.put("/{browser_id}", response_model=BookmarkResponse)
async def update_bookmark(
    browser_id: str,
    bookmark_data: BookmarkUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a bookmark by browser_id"""
    result = await db.execute(
        select(Bookmark).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.browser_id == browser_id,
            )
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    update_data = bookmark_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(bookmark, field, value)

    bookmark.synced_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(bookmark)

    # Broadcast to other devices
    await manager.broadcast_to_user(
        current_user.id,
        {
            "type": "bookmark_updated",
            "bookmark": BookmarkResponse.model_validate(bookmark).model_dump(mode="json"),
        }
    )

    return bookmark


@router.delete("/{browser_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bookmark(
    browser_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a bookmark by browser_id"""
    result = await db.execute(
        select(Bookmark).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.browser_id == browser_id,
            )
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    await db.delete(bookmark)
    await db.commit()

    # Broadcast to other devices
    await manager.broadcast_to_user(
        current_user.id,
        {
            "type": "bookmark_deleted",
            "browser_id": browser_id,
        }
    )
