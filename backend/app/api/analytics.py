"""
Analytics API Routes
"""
from typing import Annotated
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.user import User
from app.models.bookmark import Bookmark
from app.schemas.analytics import (
    AnalyticsOverview,
    DomainStat,
    TagStat,
    TimelineStat,
    DuplicateGroup,
)
from app.api.deps import get_current_user

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get analytics overview for current user"""
    # Total bookmarks
    result = await db.execute(
        select(func.count(Bookmark.id)).where(Bookmark.user_id == current_user.id)
    )
    total_bookmarks = result.scalar() or 0

    # Get all bookmarks for analysis
    result = await db.execute(
        select(Bookmark).where(Bookmark.user_id == current_user.id)
    )
    bookmarks = result.scalars().all()

    # Count unique domains
    domains = set()
    tags = set()
    folders = set()
    pinned_count = 0
    dead_links_count = 0

    for bookmark in bookmarks:
        if bookmark.domain:
            domains.add(bookmark.domain)
        if bookmark.tags:
            tags.update(bookmark.tags)
        if bookmark.folder_name:
            folders.add(bookmark.folder_name)
        if bookmark.pinned:
            pinned_count += 1
        if bookmark.http_status and bookmark.http_status >= 400:
            dead_links_count += 1

    return AnalyticsOverview(
        total_bookmarks=total_bookmarks,
        total_domains=len(domains),
        total_tags=len(tags),
        total_folders=len(folders),
        pinned_count=pinned_count,
        dead_links_count=dead_links_count,
    )


@router.get("/domains", response_model=list[DomainStat])
async def get_domain_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
):
    """Get domain distribution statistics"""
    result = await db.execute(
        select(Bookmark.domain, func.count(Bookmark.id).label("count"))
        .where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.domain.isnot(None),
            )
        )
        .group_by(Bookmark.domain)
        .order_by(func.count(Bookmark.id).desc())
        .limit(limit)
    )

    return [
        DomainStat(domain=row.domain, count=row.count)
        for row in result.all()
    ]


@router.get("/tags", response_model=list[TagStat])
async def get_tag_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
):
    """Get tag cloud statistics"""
    result = await db.execute(
        select(Bookmark.tags).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.tags.isnot(None),
            )
        )
    )

    # Count all tags
    tag_counter = Counter()
    for row in result.all():
        if row.tags:
            tag_counter.update(row.tags)

    # Return top tags
    return [
        TagStat(tag=tag, count=count)
        for tag, count in tag_counter.most_common(limit)
    ]


@router.get("/timeline", response_model=list[TimelineStat])
async def get_timeline_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    period: str = "day",  # day, week, month
):
    """Get bookmark creation timeline"""
    # SQLite and PostgreSQL have different date functions
    # Using a simple approach that works with both

    result = await db.execute(
        select(Bookmark.created_at)
        .where(Bookmark.user_id == current_user.id)
        .order_by(Bookmark.created_at)
    )

    date_counter = Counter()
    for row in result.all():
        if row.created_at:
            if period == "day":
                key = row.created_at.strftime("%Y-%m-%d")
            elif period == "week":
                key = row.created_at.strftime("%Y-W%W")
            else:  # month
                key = row.created_at.strftime("%Y-%m")
            date_counter[key] += 1

    return [
        TimelineStat(date=date, count=count)
        for date, count in sorted(date_counter.items())
    ]


@router.get("/duplicates", response_model=list[DuplicateGroup])
async def get_duplicates(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Find duplicate bookmarks by URL"""
    # Find URLs that appear more than once
    result = await db.execute(
        select(Bookmark.url, func.count(Bookmark.id).label("count"))
        .where(Bookmark.user_id == current_user.id)
        .group_by(Bookmark.url)
        .having(func.count(Bookmark.id) > 1)
    )

    duplicate_urls = [row.url for row in result.all()]

    if not duplicate_urls:
        return []

    # Get all bookmarks for duplicate URLs
    result = await db.execute(
        select(Bookmark)
        .where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.url.in_(duplicate_urls),
            )
        )
        .order_by(Bookmark.url, Bookmark.created_at)
    )

    bookmarks = result.scalars().all()

    # Group by URL
    url_groups = {}
    for bookmark in bookmarks:
        if bookmark.url not in url_groups:
            url_groups[bookmark.url] = []
        url_groups[bookmark.url].append({
            "id": bookmark.id,
            "browser_id": bookmark.browser_id,
            "title": bookmark.title,
            "folder_name": bookmark.folder_name,
            "created_at": bookmark.created_at.isoformat(),
        })

    return [
        DuplicateGroup(
            url=url,
            bookmarks=bookmarks,
            count=len(bookmarks),
        )
        for url, bookmarks in url_groups.items()
    ]
