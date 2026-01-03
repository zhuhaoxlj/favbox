"""
Semantic Search API

语义搜索端点：自然语言搜索、相似书签查找。
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.services.search_service import SearchService, SearchFilters

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/search", tags=["semantic-search"])


class SemanticSearchRequest(BaseModel):
    """语义搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="最小相似度")
    limit: int = Field(20, ge=1, le=100, description="返回结果数量")
    filters: Optional[dict] = Field(None, description="过滤条件")


class SemanticSearchResponse(BaseModel):
    """语义搜索响应"""
    query: str
    results: List[dict]
    total: int
    query_time_ms: float


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    语义搜索 - 基于向量相似度的智能搜索

    Args:
        request: 搜索请求

    Returns:
        搜索结果列表
    """
    import time

    start_time = time.time()

    # 构建过滤条件
    filters = None
    if request.filters:
        filters = SearchFilters(
            domains=request.filters.get("domains"),
            tags=request.filters.get("tags"),
            category_ids=request.filters.get("category_ids"),
            date_start=request.filters.get("date_start"),
            date_end=request.filters.get("date_end")
        )

    # 执行搜索
    try:
        search_service = SearchService(db)
        results, _ = await search_service.semantic_search(
            query=request.query,
            user_id=current_user.id,
            filters=filters,
            limit=request.limit,
            min_similarity=request.min_similarity
        )

        query_time = (time.time() - start_time) * 1000

        return SemanticSearchResponse(
            query=request.query,
            results=[r.to_dict() for r in results],
            total=len(results),
            query_time_ms=round(query_time, 2)
        )

    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/similar/{bookmark_id}", response_model=List[dict])
async def find_similar_bookmarks(
    bookmark_id: int,
    limit: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.6, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    查找相似书签

    Args:
        bookmark_id: 参考书签ID
        limit: 返回结果数量
        min_similarity: 最小相似度

    Returns:
        相似书签列表
    """
    try:
        search_service = SearchService(db)
        results = await search_service.find_similar_bookmarks(
            bookmark_id=bookmark_id,
            user_id=current_user.id,
            limit=limit,
            min_similarity=min_similarity
        )

        return [r.to_dict() for r in results]

    except Exception as e:
        logger.error(f"Find similar failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to find similar bookmarks: {str(e)}"
        )


@router.post("/embeddings/batch", response_model=dict)
async def batch_generate_embeddings(
    days: int = Query(30, ge=1, le=365, description="处理最近N天的书签"),
    overwrite: bool = Query(False, description="是否覆盖已有向量"),
    also_classify: bool = Query(True, description="是否同时进行AI分类"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    批量生成向量嵌入（后台任务）

    注意：这是一个长时间运行的操作，建议使用WebSocket或任务队列。

    Args:
        days: 处理最近N天的书签
        overwrite: 是否覆盖
        also_classify: 是否同时分类

    Returns:
        任务信息
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select

    # 获取需要处理的书签数量
    query = select(Bookmark).where(
        and_(
            Bookmark.user_id == current_user.id,
            Bookmark.created_at >= datetime.utcnow() - timedelta(days=days)
        )
    )

    if not overwrite:
        query = query.where(Bookmark.ai_embedding.is_(None))

    result = await db.execute(query)
    bookmarks = result.scalars().all()

    if not bookmarks:
        return {
            "message": "No bookmarks to process",
            "total": 0,
            "status": "completed"
        }

    # 这里应该启动后台任务
    # 目前返回提示信息
    return {
        "message": "Batch embedding requires background task queue",
        "total": len(bookmarks),
        "status": "pending",
        "instruction": f"Run: python -m app.scripts.batch_embed --user-id {current_user.id} --batch-size 100"
    }


@router.get("/embeddings/stats", response_model=dict)
async def get_embedding_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取向量化统计信息
    """
    from sqlalchemy import select, func

    # 总书签数
    total_result = await db.execute(
        select(func.count()).where(Bookmark.user_id == current_user.id)
    )
    total_bookmarks = total_result.scalar()

    # 已向量化的书签数
    embedded_result = await db.execute(
        select(func.count()).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_embedding.isnot(None)
            )
        )
    )
    embedded_bookmarks = embedded_result.scalar()

    # 已分类的书签数
    classified_result = await db.execute(
        select(func.count()).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_category_id.isnot(None)
            )
        )
    )
    classified_bookmarks = classified_result.scalar()

    return {
        "total_bookmarks": total_bookmarks,
        "embedded_bookmarks": embedded_bookmarks,
        "classified_bookmarks": classified_bookmarks,
        "embedding_rate": f"{(embedded_bookmarks / total_bookmarks * 100):.1f}%" if total_bookmarks > 0 else "0%",
        "classification_rate": f"{(classified_bookmarks / total_bookmarks * 100):.1f}%" if total_bookmarks > 0 else "0%"
    }
