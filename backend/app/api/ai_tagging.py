"""
AI Tagging API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.database import get_db
from app.services.ai_tagger import ai_tagger
from app.models.bookmark import Bookmark
from app.api.deps import get_current_user
from app.models.user import User


router = APIRouter(prefix="/ai", tags=["ai-tagging"])


class SuggestTagsRequest(BaseModel):
    title: str = Field(..., description="书签标题")
    description: Optional[str] = Field(None, description="页面描述")
    url: Optional[str] = Field(None, description="书签URL")
    keywords: Optional[list[str]] = Field(
        default_factory=list, description="页面关键词"
    )
    max_tags: int = Field(5, ge=1, le=10, description="最大标签数量")


class SuggestTagsResponse(BaseModel):
    tags: list[str]
    confidence: dict[str, float]
    category: Optional[dict] = None  # 新增：分类信息


class BatchTagRequest(BaseModel):
    days: int = Field(30, ge=1, le=365, description="处理最近N天的书签")
    max_tags: int = Field(5, ge=1, le=10, description="每个书签的最大标签数")
    overwrite: bool = Field(False, description="是否覆盖现有标签")
    create_backup: bool = Field(True, description="处理前是否创建备份")


class BatchTagResponse(BaseModel):
    processed: int
    success: int
    failed: int
    skipped: int
    backup_id: Optional[int] = None
    errors: list[str] = []


class ApplyTagsRequest(BaseModel):
    bookmark_id: int = Field(..., description="书签ID")
    tags: list[str] = Field(..., description="要应用的标签")
    confidence: dict[str, float] = Field(default_factory=dict, description="置信度分数")


@router.get("/test-api-key")
async def test_api_key():
    """
    测试 Gemini API Key 是否有效（无需认证）
    """
    try:
        result = await ai_tagger.test_api_key()
        return {
            "status": "success" if result else "failed",
            "message": "API Key is valid" if result else "API Key is invalid or API call failed",
            "model": ai_tagger.api_url.split("/")[-1].split(":")[0],
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"API Key test failed: {str(e)}",
            "error": type(e).__name__,
        }


@router.post("/suggest-tags", response_model=SuggestTagsResponse)
async def suggest_tags(
    request: SuggestTagsRequest, current_user: User = Depends(get_current_user)
):
    """
    为单个书签建议标签和分类
    """
    try:
        # 1. 生成标签
        tags, confidence = await ai_tagger.generate_tags(
            title=request.title,
            description=request.description,
            url=request.url,
            keywords=request.keywords,
            max_tags=request.max_tags,
        )

        # 2. 尝试进行分类（可选）
        category_info = None
        try:
            from app.services.classification_service import get_classification_service
            from app.services.category_initializer import get_or_init_categories

            # 获取数据库会话
            from app.database import get_db
            async for db in get_db():
                # 获取或初始化分类
                categories = await get_or_init_categories(db, current_user.id)

                # 分类
                classification_service = get_classification_service()
                category_id, cat_confidence, cat_name = await classification_service.classify_bookmark(
                    title=request.title,
                    description=request.description,
                    url=request.url,
                    available_categories=categories
                )

                category_info = {
                    "id": category_id,
                    "name": cat_name,
                    "confidence": cat_confidence
                }
                break  # 只需要一个会话
        except Exception as e:
            print(f"[WARNING] Classification failed: {e}")
            # 分类失败不影响标签返回

        return SuggestTagsResponse(tags=tags, confidence=confidence, category=category_info)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tags: {str(e)}",
        )


@router.post("/batch-tag", response_model=BatchTagResponse)
async def batch_tag_bookmarks(
    request: BatchTagRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量打标签和分类 - 按时间范围处理书签

    处理最近N天的书签，为它们生成AI标签并进行AI分类
    """
    from app.services.backup_service import BackupService
    from app.services.classification_service import get_classification_service
    from app.services.category_initializer import get_or_init_categories
    from app.models.category import Category

    backup_id = None
    errors = []
    processed = 0
    success = 0
    failed = 0
    skipped = 0

    try:
        # 创建备份（如果需要）
        if request.create_backup:
            backup_name = (
                f"AI批量打标签和分类前备份 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            backup = await BackupService.create_backup(
                db=db,
                user_id=current_user.id,
                name=backup_name,
                description=f"批量处理最近{request.days}天的书签前创建的备份",
            )
            backup_id = backup.id

        # 获取或初始化默认分类
        categories = await get_or_init_categories(db, current_user.id)
        print(f"[DEBUG] Found {len(categories)} categories")

        # 初始化分类服务
        try:
            classification_service = get_classification_service()
            use_classification = True
            print(f"[DEBUG] Classification service initialized")
        except Exception as e:
            print(f"[WARNING] Classification service not available: {e}")
            use_classification = False

        # 计算时间范围
        start_date = datetime.utcnow() - timedelta(days=request.days)

        # 获取符合条件的书签
        query = select(Bookmark).where(
            and_(Bookmark.user_id == current_user.id, Bookmark.created_at >= start_date)
        )

        # 如果不覆盖，只处理没有标签的书签
        if not request.overwrite:
            query = query.where(
                (Bookmark.tags == None)
                | (Bookmark.tags == "[]")
                | (Bookmark.tags == "")
            )

        result = await db.execute(query)
        bookmarks = result.scalars().all()

        processed = len(bookmarks)
        print(f"[DEBUG] Found {processed} bookmarks to process")

        # 处理每个书签
        for idx, bookmark in enumerate(bookmarks, 1):
            print(f"[DEBUG] Processing bookmark {idx}/{processed}: ID={bookmark.id}, Title={bookmark.title[:30]}")
            try:
                # 1. 生成标签
                print(f"[DEBUG] Calling AI tagger for bookmark {bookmark.id}...")
                tags, confidence = await ai_tagger.generate_tags(
                    title=bookmark.title,
                    description=bookmark.description,
                    url=bookmark.url,
                    keywords=bookmark.keywords,
                    max_tags=request.max_tags,
                )

                # 更新书签
                bookmark.ai_tags = tags
                bookmark.ai_tags_confidence = confidence
                bookmark.last_ai_analysis_at = datetime.utcnow()

                print(f"[DEBUG] Bookmark {bookmark.id} updated with AI tags: {tags}")

                # 2. AI分类（如果启用）
                if use_classification:
                    try:
                        category_id, cat_confidence, cat_name = await classification_service.classify_bookmark(
                            title=bookmark.title,
                            description=bookmark.description,
                            url=bookmark.url,
                            available_categories=categories
                        )
                        bookmark.ai_category_id = category_id
                        print(f"[DEBUG] Bookmark {bookmark.id} classified as: {cat_name} (confidence: {cat_confidence:.2f})")
                    except Exception as e:
                        print(f"[WARNING] Classification failed for bookmark {bookmark.id}: {e}")

                # 如果有AI标签且用户未手动设置标签，则自动应用
                if tags and (not bookmark.tags or len(bookmark.tags) == 0):
                    bookmark.tags = tags
                    print(f"[DEBUG] Bookmark {bookmark.id} tags also updated: {tags}")

                success += 1

                # 每处理一个书签就立即提交，避免因中断导致数据丢失
                await db.commit()
                print(f"[DEBUG] Committed bookmark {bookmark.id} to database")

            except Exception as e:
                import traceback
                failed += 1
                error_msg = f"书签 {bookmark.title[:50]} (ID: {bookmark.id}) 失败: {type(e).__name__}: {str(e)}"
                errors.append(error_msg)
                print(f"[ERROR] {error_msg}")
                traceback.print_exc()

        print(f"[DEBUG] All bookmarks processed. Total: {processed}, Success: {success}, Failed: {failed}")

        return BatchTagResponse(
            processed=processed,
            success=success,
            failed=failed,
            skipped=skipped,
            backup_id=backup_id,
            errors=errors[:10],  # 只返回前10个错误
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量打标签和分类失败: {str(e)}",
        )


@router.post("/apply-tags/{bookmark_id}", status_code=status.HTTP_200_OK)
async def apply_tags(
    bookmark_id: int,
    request: ApplyTagsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    手动应用标签到特定书签
    """
    # 获取书签
    result = await db.execute(
        select(Bookmark).where(
            and_(Bookmark.id == bookmark_id, Bookmark.user_id == current_user.id)
        )
    )
    bookmark = result.scalar_one_or_none()

    if not bookmark:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bookmark not found"
        )

    # 应用标签
    bookmark.tags = request.tags
    bookmark.ai_tags = request.tags
    bookmark.ai_tags_confidence = request.confidence
    bookmark.last_ai_analysis_at = datetime.utcnow()

    await db.commit()

    return {"message": "Tags applied successfully"}


@router.get("/stats")
async def get_ai_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    获取AI处理的统计信息
    """
    # 总书签数
    total_result = await db.execute(
        select(func.count()).where(Bookmark.user_id == current_user.id)
    )
    total_bookmarks = total_result.scalar()

    # 已AI分析的书签数
    analyzed_result = await db.execute(
        select(func.count()).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.last_ai_analysis_at.isnot(None),
            )
        )
    )
    analyzed_bookmarks = analyzed_result.scalar()

    # 有AI标签的书签数
    with_ai_tags_result = await db.execute(
        select(func.count()).where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_tags.isnot(None),
                Bookmark.ai_tags != [],  # 空列表
                Bookmark.ai_tags != "",   # 空字符串（如果存储为字符串）
            )
        )
    )
    with_ai_tags = with_ai_tags_result.scalar()

    stats = {
        "total_bookmarks": total_bookmarks,
        "analyzed_bookmarks": analyzed_bookmarks,
        "bookmarks_with_ai_tags": with_ai_tags,
        "analysis_rate": f"{(analyzed_bookmarks / total_bookmarks * 100):.1f}%"
        if total_bookmarks > 0
        else "0%",
    }

    print(f"[DEBUG] AI Stats: {stats}")

    return stats


@router.get("/debug-tags")
async def debug_tags(
    limit: int = 5,
    db: AsyncSession = Depends(get_db),
):
    """
    调试端点：查看最近的 AI 标签（无需认证，用于调试）
    """
    # 获取最近处理的用户书签（限制到最近的一个用户）
    result = await db.execute(
        select(Bookmark)
        .where(Bookmark.last_ai_analysis_at.isnot(None))
        .order_by(Bookmark.last_ai_analysis_at.desc())
        .limit(limit)
    )
    bookmarks = result.scalars().all()

    debug_info = []
    for b in bookmarks:
        debug_info.append({
            "user_id": b.user_id,
            "id": b.id,
            "title": b.title[:50],
            "ai_tags": b.ai_tags,
            "ai_tags_confidence": b.ai_tags_confidence,
            "tags": b.tags,
            "last_ai_analysis_at": str(b.last_ai_analysis_at) if b.last_ai_analysis_at else None,
        })

    print(f"[DEBUG] AI Tags Debug: {debug_info}")

    return {
        "count": len(debug_info),
        "bookmarks": debug_info
    }
