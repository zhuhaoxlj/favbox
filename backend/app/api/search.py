"""
Semantic Search API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.semantic_search import semantic_search
from app.models.bookmark import Bookmark
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.bookmark import BookmarkResponse


router = APIRouter(prefix="/search", tags=["search"])


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="搜索查询")
    limit: int = Field(20, ge=1, le=100, description="返回结果数量")
    min_similarity: float = Field(0.5, ge=0.0, le=1.0, description="最小相似度阈值")


class SemanticSearchResult(BaseModel):
    bookmark: BookmarkResponse
    similarity: float


class GenerateEmbeddingsRequest(BaseModel):
    days: int = Field(30, ge=1, le=365, description="处理最近N天的书签")
    overwrite: bool = Field(False, description="是否覆盖现有嵌入")


@router.post("/semantic", response_model=List[SemanticSearchResult])
async def semantic_search_endpoint(
    request: SemanticSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    语义化搜索 - 基于向量嵌入的智能搜索

    通过理解查询的语义含义来找到相关书签，而不仅仅是匹配关键词
    """
    try:
        results = await semantic_search.search_bookmarks(
            db=db,
            user_id=current_user.id,
            query=request.query,
            limit=request.limit,
            min_similarity=request.min_similarity,
        )

        # Convert to response format
        search_results = []
        for bookmark, similarity in results:
            bookmark_response = BookmarkResponse(
                id=bookmark.id,
                user_id=bookmark.user_id,
                browser_id=bookmark.browser_id,
                url=bookmark.url,
                title=bookmark.title,
                description=bookmark.description,
                domain=bookmark.domain,
                favicon=bookmark.favicon,
                image=bookmark.image,
                tags=bookmark.tags or [],
                keywords=bookmark.keywords or [],
                notes=bookmark.notes,
                folder_name=bookmark.folder_name,
                folder_id=bookmark.folder_id,
                pinned=bookmark.pinned,
                http_status=bookmark.http_status,
                date_added=bookmark.date_added,
                created_at=bookmark.created_at,
                updated_at=bookmark.updated_at,
                synced_at=bookmark.synced_at,
            )
            search_results.append(
                SemanticSearchResult(bookmark=bookmark_response, similarity=similarity)
            )

        return search_results

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"语义搜索失败: {str(e)}",
        )


@router.post("/generate-embeddings", status_code=status.HTTP_200_OK)
async def generate_embeddings(
    request: GenerateEmbeddingsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    为书签生成向量嵌入

    批量为书签生成向量嵌入，用于语义化搜索
    """
    from datetime import datetime, timedelta
    from sqlalchemy import select, and_, func

    try:
        # 计算时间范围
        start_date = datetime.utcnow() - timedelta(days=request.days)

        # 获取符合条件的书签
        query = select(Bookmark).where(
            and_(Bookmark.user_id == current_user.id, Bookmark.created_at >= start_date)
        )

        # 如果不覆盖，只处理没有嵌入的书签
        if not request.overwrite:
            query = query.where(
                (Bookmark.ai_embedding == None) | (Bookmark.ai_embedding == [])
            )

        result = await db.execute(query)
        bookmarks = result.scalars().all()

        processed = 0
        success = 0
        failed = 0

        # 为每个书签生成嵌入
        for bookmark in bookmarks:
            processed += 1
            try:
                await semantic_search.update_bookmark_embedding(db, bookmark)
                success += 1
            except Exception as e:
                failed += 1
                print(f"Failed to generate embedding for bookmark {bookmark.id}: {e}")

        return {
            "processed": processed,
            "success": success,
            "failed": failed,
            "message": f"成功为 {success}/{processed} 个书签生成向量嵌入",
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"生成向量嵌入失败: {str(e)}",
        )


@router.get("/embedding-stats")
async def get_embedding_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    获取向量嵌入的统计信息
    """
    from sqlalchemy import select, and_, func

    # 总书签数
    total_result = await db.execute(
        select(func.count()).where(Bookmark.user_id == current_user.id)
    )
    total_bookmarks = total_result.scalar()

    # 有向量嵌入的书签数（兼容SQLite和PostgreSQL）
    # SQLite: 使用JSON不为null且不为空数组
    # PostgreSQL: 也可以使用相同的逻辑
    with_embedding_result = await db.execute(
        select(func.count()).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_embedding != None,
                Bookmark.ai_embedding != [],
            )
        )
    )
    with_embedding = with_embedding_result.scalar()

    return {
        "total_bookmarks": total_bookmarks,
        "bookmarks_with_embeddings": with_embedding,
        "embedding_coverage": f"{(with_embedding / total_bookmarks * 100):.1f}%"
        if total_bookmarks > 0
        else "0%",
    }
