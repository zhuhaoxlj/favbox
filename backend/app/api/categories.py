"""
Categories API

分类管理端点：创建、读取、更新、删除分类。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import List
import logging

from app.database import get_db
from app.models.category import Category
from app.models.bookmark import Bookmark
from app.models.user import User
from app.api.deps import get_current_user
from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryTree,
    CategoryStats
)
from app.services.category_initializer import (
    get_or_init_categories,
    init_default_categories
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=List[CategoryTree])
async def get_categories(
    include_empty: bool = True,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取用户的所有分类（树形结构）

    Args:
        include_empty: 是否包含空分类（没有书签的分类）
    """
    # 获取所有顶级分类
    result = await db.execute(
        select(Category)
        .where(
            and_(
                Category.user_id == current_user.id,
                Category.parent_id.is_(None)
            )
        )
        .order_by(Category.position)
    )
    root_categories = result.scalars().all()

    # 如果没有分类，自动初始化默认分类
    if not root_categories:
        root_categories = await init_default_categories(db, current_user.id)

    # 构建树形结构
    categories_tree = []
    for root in root_categories:
        category_dict = _category_to_dict(root)
        category_dict["children"] = await _get_children_recursive(db, root.id, include_empty)
        categories_tree.append(CategoryTree(**category_dict))

    return categories_tree


@router.get("/stats", response_model=CategoryStats)
async def get_category_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取分类统计信息
    """
    # 总分类数
    total_result = await db.execute(
        select(func.count()).where(Category.user_id == current_user.id)
    )
    total_categories = total_result.scalar()

    # 顶级分类数
    root_result = await db.execute(
        select(func.count()).where(
            and_(
                Category.user_id == current_user.id,
                Category.parent_id.is_(None)
            )
        )
    )
    root_categories = root_result.scalar()

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

    return CategoryStats(
        total_categories=total_categories,
        root_categories=root_categories,
        total_bookmarks_in_categories=classified_bookmarks
    )


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    创建新分类

    Args:
        category: 分类数据

    Returns:
        创建的分类
    """
    # 验证父分类
    if category.parent_id:
        parent_result = await db.execute(
            select(Category).where(
                and_(
                    Category.id == category.parent_id,
                    Category.user_id == current_user.id
                )
            )
        )
        parent = parent_result.scalar_one_or_none()

        if not parent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Parent category not found"
            )

        level = parent.level + 1
    else:
        level = 1

    # 创建分类
    new_category = Category(
        user_id=current_user.id,
        name=category.name,
        parent_id=category.parent_id,
        description=category.description,
        color=category.color,
        icon=category.icon,
        keywords=category.keywords,
        position=category.position,
        level=level,
        bookmark_count=0
    )

    db.add(new_category)
    await db.commit()
    await db.refresh(new_category)

    logger.info(f"User {current_user.id} created category: {new_category.name}")

    return CategoryResponse(**_category_to_dict(new_category))


@router.put("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: int,
    category_update: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    更新分类

    Args:
        category_id: 分类ID
        category_update: 更新数据

    Returns:
        更新后的分类
    """
    # 获取分类
    result = await db.execute(
        select(Category).where(
            and_(
                Category.id == category_id,
                Category.user_id == current_user.id
            )
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # 更新字段
    update_data = category_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    await db.commit()
    await db.refresh(category)

    logger.info(f"User {current_user.id} updated category {category_id}")

    return CategoryResponse(**_category_to_dict(category))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    move_bookmarks_to: int = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    删除分类

    Args:
        category_id: 分类ID
        move_bookmarks_to: 将书签移动到此分类ID（可选）
    """
    # 获取分类
    result = await db.execute(
        select(Category).where(
            and_(
                Category.id == category_id,
                Category.user_id == current_user.id
            )
        )
    )
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # 检查是否有子分类
    if category.children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category with subcategories. Delete subcategories first."
        )

    # 处理该分类下的书签
    if move_bookmarks_to:
        # 移动书签到其他分类
        await db.execute(
            select(Bookmark)
            .where(Bookmark.ai_category_id == category_id)
        )
        # 更新书签分类
        from sqlalchemy import update
        await db.execute(
            update(Bookmark)
            .where(Bookmark.ai_category_id == category_id)
            .values(ai_category_id=move_bookmarks_to)
        )
    else:
        # 移除分类关联
        from sqlalchemy import update
        await db.execute(
            update(Bookmark)
            .where(Bookmark.ai_category_id == category_id)
            .values(ai_category_id=None)
        )

    # 删除分类
    await db.delete(category)
    await db.commit()

    logger.info(f"User {current_user.id} deleted category {category_id}")


@router.post("/initialize", response_model=List[CategoryTree])
async def initialize_default_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    初始化默认分类模板

    如果用户已有分类，则返回现有分类。
    """
    categories = await get_or_init_categories(db, current_user.id)

    # 构建树形结构
    categories_tree = []
    for category in categories:
        if category.parent_id is None:  # 只返回顶级分类
            category_dict = _category_to_dict(category)
            category_dict["children"] = await _get_children_recursive(db, category.id, True)
            categories_tree.append(CategoryTree(**category_dict))

    return categories_tree


@router.post("/reset", response_model=List[CategoryTree])
async def reset_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    重置用户的分类（删除所有现有分类，重新初始化默认分类）

    警告：这将删除所有自定义分类！
    """
    from app.services.category_initializer import reset_user_categories

    categories = await reset_user_categories(db, current_user.id)

    # 构建树形结构
    categories_tree = []
    for category in categories:
        category_dict = _category_to_dict(category)
        category_dict["children"] = []
        categories_tree.append(CategoryTree(**category_dict))

    return categories_tree


@router.get("/{category_id}/bookmarks")
async def get_category_bookmarks(
    category_id: int,
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    获取指定分类下的书签列表

    Args:
        category_id: 分类ID
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        书签列表和分页信息
    """
    # 验证分类存在且属于当前用户
    category_result = await db.execute(
        select(Category).where(
            and_(
                Category.id == category_id,
                Category.user_id == current_user.id
            )
        )
    )
    category = category_result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # 获取该分类下的书签
    from app.schemas.bookmark import BookmarkResponse

    # 计算总数
    count_result = await db.execute(
        select(func.count())
        .select_from(Bookmark)
        .where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_category_id == category_id
            )
        )
    )
    total = count_result.scalar()

    # 获取书签列表
    offset = (page - 1) * page_size
    bookmarks_result = await db.execute(
        select(Bookmark)
        .where(
            and_(
                Bookmark.user_id == current_user.id,
                Bookmark.ai_category_id == category_id
            )
        )
        .order_by(Bookmark.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    bookmarks = bookmarks_result.scalars().all()

    # 转换为响应格式 - BookmarkResponse 支持从 SQLAlchemy 模型直接创建
    bookmarks_data = [
        BookmarkResponse.model_validate(bookmark)
        for bookmark in bookmarks
    ]

    return {
        "bookmarks": bookmarks_data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


# 辅助函数
def _category_to_dict(category: Category) -> dict:
    """将Category对象转换为字典"""
    return {
        "id": category.id,
        "user_id": category.user_id,
        "name": category.name,
        "parent_id": category.parent_id,
        "description": category.description,
        "color": category.color,
        "icon": category.icon,
        "keywords": category.keywords or [],
        "position": category.position,
        "level": category.level,
        "bookmark_count": category.bookmark_count,
        "created_at": category.created_at,
        "updated_at": category.updated_at
    }


async def _get_children_recursive(
    db: AsyncSession,
    parent_id: int,
    include_empty: bool
) -> List[dict]:
    """递归获取子分类"""
    result = await db.execute(
        select(Category)
        .where(Category.parent_id == parent_id)
        .order_by(Category.position)
    )
    children = result.scalars().all()

    children_list = []
    for child in children:
        # 检查是否包含空分类
        if not include_empty and child.bookmark_count == 0:
            continue

        child_dict = _category_to_dict(child)
        child_dict["children"] = await _get_children_recursive(db, child.id, include_empty)
        children_list.append(child_dict)

    return children_list
