"""
Collections API Routes - Collaboration and Sharing
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func

from app.database import get_db
from app.models.user import User
from app.models.bookmark import Bookmark
from app.models.collection import Collection, CollectionBookmark, CollectionShare, Permission
from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
    CollectionResponse,
    CollectionShareCreate,
    CollectionShareResponse,
    CollectionWithBookmarks,
)
from app.schemas.bookmark import BookmarkResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/collections", tags=["Collections"])


@router.post("", response_model=CollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: CollectionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new collection"""
    collection = Collection(
        user_id=current_user.id,
        **collection_data.model_dump(),
    )
    db.add(collection)
    await db.commit()
    await db.refresh(collection)

    return CollectionResponse(
        **collection.__dict__,
        bookmark_count=0,
    )


@router.get("", response_model=list[CollectionResponse])
async def get_collections(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get all collections owned by current user"""
    result = await db.execute(
        select(Collection, func.count(CollectionBookmark.id).label("bookmark_count"))
        .outerjoin(CollectionBookmark)
        .where(Collection.user_id == current_user.id)
        .group_by(Collection.id)
    )

    return [
        CollectionResponse(
            id=row.Collection.id,
            user_id=row.Collection.user_id,
            name=row.Collection.name,
            description=row.Collection.description,
            is_public=row.Collection.is_public,
            created_at=row.Collection.created_at,
            updated_at=row.Collection.updated_at,
            bookmark_count=row.bookmark_count,
        )
        for row in result.all()
    ]


@router.get("/shared", response_model=list[CollectionResponse])
async def get_shared_collections(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get collections shared with current user"""
    result = await db.execute(
        select(Collection, func.count(CollectionBookmark.id).label("bookmark_count"))
        .join(CollectionShare, CollectionShare.collection_id == Collection.id)
        .outerjoin(CollectionBookmark)
        .where(CollectionShare.user_id == current_user.id)
        .group_by(Collection.id)
    )

    return [
        CollectionResponse(
            id=row.Collection.id,
            user_id=row.Collection.user_id,
            name=row.Collection.name,
            description=row.Collection.description,
            is_public=row.Collection.is_public,
            created_at=row.Collection.created_at,
            updated_at=row.Collection.updated_at,
            bookmark_count=row.bookmark_count,
        )
        for row in result.all()
    ]


@router.get("/{collection_id}", response_model=CollectionWithBookmarks)
async def get_collection(
    collection_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a collection with its bookmarks"""
    # Check access
    collection = await _get_collection_with_access(collection_id, current_user, db)

    # Get bookmarks
    result = await db.execute(
        select(Bookmark)
        .join(CollectionBookmark)
        .where(CollectionBookmark.collection_id == collection_id)
    )
    bookmarks = result.scalars().all()

    return CollectionWithBookmarks(
        id=collection.id,
        user_id=collection.user_id,
        name=collection.name,
        description=collection.description,
        is_public=collection.is_public,
        created_at=collection.created_at,
        updated_at=collection.updated_at,
        bookmark_count=len(bookmarks),
        bookmarks=[BookmarkResponse.model_validate(b).model_dump() for b in bookmarks],
    )


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: int,
    collection_data: CollectionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update a collection (owner only)"""
    result = await db.execute(
        select(Collection).where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id,
            )
        )
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    update_data = collection_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    await db.commit()
    await db.refresh(collection)

    # Get bookmark count
    result = await db.execute(
        select(func.count(CollectionBookmark.id))
        .where(CollectionBookmark.collection_id == collection_id)
    )
    bookmark_count = result.scalar() or 0

    return CollectionResponse(
        **collection.__dict__,
        bookmark_count=bookmark_count,
    )


@router.delete("/{collection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(
    collection_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a collection (owner only)"""
    result = await db.execute(
        select(Collection).where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id,
            )
        )
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    await db.delete(collection)
    await db.commit()


@router.post("/{collection_id}/bookmarks/{bookmark_id}", status_code=status.HTTP_201_CREATED)
async def add_bookmark_to_collection(
    collection_id: int,
    bookmark_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a bookmark to a collection"""
    # Check write access
    collection = await _get_collection_with_access(
        collection_id, current_user, db, require_write=True
    )

    # Check bookmark exists and belongs to user
    result = await db.execute(
        select(Bookmark).where(
            and_(
                Bookmark.id == bookmark_id,
                Bookmark.user_id == current_user.id,
            )
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    # Check if already in collection
    result = await db.execute(
        select(CollectionBookmark).where(
            and_(
                CollectionBookmark.collection_id == collection_id,
                CollectionBookmark.bookmark_id == bookmark_id,
            )
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Bookmark already in collection")

    # Add to collection
    cb = CollectionBookmark(collection_id=collection_id, bookmark_id=bookmark_id)
    db.add(cb)
    await db.commit()

    return {"message": "Bookmark added to collection"}


@router.delete("/{collection_id}/bookmarks/{bookmark_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_bookmark_from_collection(
    collection_id: int,
    bookmark_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a bookmark from a collection"""
    # Check write access
    await _get_collection_with_access(collection_id, current_user, db, require_write=True)

    result = await db.execute(
        select(CollectionBookmark).where(
            and_(
                CollectionBookmark.collection_id == collection_id,
                CollectionBookmark.bookmark_id == bookmark_id,
            )
        )
    )
    cb = result.scalar_one_or_none()

    if not cb:
        raise HTTPException(status_code=404, detail="Bookmark not in collection")

    await db.delete(cb)
    await db.commit()


@router.post("/{collection_id}/share", response_model=CollectionShareResponse)
async def share_collection(
    collection_id: int,
    share_data: CollectionShareCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Share a collection with another user (owner only)"""
    # Check ownership
    result = await db.execute(
        select(Collection).where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id,
            )
        )
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Check target user exists
    result = await db.execute(
        select(User).where(User.id == share_data.user_id)
    )
    target_user = result.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot share with yourself")

    # Check if already shared
    result = await db.execute(
        select(CollectionShare).where(
            and_(
                CollectionShare.collection_id == collection_id,
                CollectionShare.user_id == share_data.user_id,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update permission
        existing.permission = share_data.permission
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create share
    share = CollectionShare(
        collection_id=collection_id,
        user_id=share_data.user_id,
        permission=share_data.permission,
    )
    db.add(share)
    await db.commit()
    await db.refresh(share)

    return share


@router.delete("/{collection_id}/collaborators/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_collaborator(
    collection_id: int,
    user_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Remove a collaborator from a collection (owner only)"""
    # Check ownership
    result = await db.execute(
        select(Collection).where(
            and_(
                Collection.id == collection_id,
                Collection.user_id == current_user.id,
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Collection not found")

    # Remove share
    result = await db.execute(
        select(CollectionShare).where(
            and_(
                CollectionShare.collection_id == collection_id,
                CollectionShare.user_id == user_id,
            )
        )
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=404, detail="Collaborator not found")

    await db.delete(share)
    await db.commit()


async def _get_collection_with_access(
    collection_id: int,
    user: User,
    db: AsyncSession,
    require_write: bool = False,
) -> Collection:
    """Helper to check collection access"""
    result = await db.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Owner has full access
    if collection.user_id == user.id:
        return collection

    # Check if public
    if collection.is_public and not require_write:
        return collection

    # Check if shared
    result = await db.execute(
        select(CollectionShare).where(
            and_(
                CollectionShare.collection_id == collection_id,
                CollectionShare.user_id == user.id,
            )
        )
    )
    share = result.scalar_one_or_none()

    if not share:
        raise HTTPException(status_code=403, detail="Access denied")

    if require_write and share.permission != Permission.WRITE:
        raise HTTPException(status_code=403, detail="Write access required")

    return collection
