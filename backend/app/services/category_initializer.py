"""
Default Category Templates

初始化默认分类模板：技术、设计、Switch游戏资源、图书下载资源、Blog
"""

from typing import List, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.category import Category
from app.models.user import User
from app.services.embedding_service import get_embedding_service


# 默认分类配置
DEFAULT_CATEGORIES: List[Dict] = [
    {
        "name": "技术",
        "description": "技术相关文章和教程",
        "color": "#3B82F6",
        "icon": "💻",
        "keywords": ["编程", "开发", "代码", "教程", "技术", "API", "框架", "算法", "数据库", "Python", "JavaScript", "Vue", "React", "前端", "后端"],
        "position": 1
    },
    {
        "name": "设计",
        "description": "UI/UX设计资源和灵感",
        "color": "#EC4899",
        "icon": "🎨",
        "keywords": ["UI", "UX", "设计", "Figma", "Sketch", "原型", "界面", "交互", "视觉", "图标", "素材", "模板"],
        "position": 2
    },
    {
        "name": "Switch游戏资源",
        "description": "Nintendo Switch游戏相关资源",
        "color": "#EF4444",
        "icon": "🎮",
        "keywords": ["Switch", "Nintendo", "游戏", "NSO", "eShop", "下载", "攻略", "评测", "独立游戏"],
        "position": 3
    },
    {
        "name": "图书下载资源",
        "description": "电子书下载和在线阅读资源",
        "color": "#10B981",
        "icon": "📚",
        "keywords": ["电子书", "PDF", "下载", "图书", "阅读", "Kindle", "epub", "mobi", "小说", "技术书", "教程"],
        "position": 4
    },
    {
        "name": "Blog",
        "description": "个人博客和文章收藏",
        "color": "#F59E0B",
        "icon": "✍️",
        "keywords": ["博客", "Blog", "文章", "随笔", "日记", "思考", "经验", "分享"],
        "position": 5
    }
]


async def init_default_categories(
    db: AsyncSession,
    user_id: int
) -> List[Category]:
    """
    为用户初始化默认分类

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        创建的分类列表
    """
    # 检查是否已有分类
    result = await db.execute(
        select(Category).where(Category.user_id == user_id)
    )
    existing = result.scalars().all()

    if existing:
        print(f"✅ User {user_id} already has {len(existing)} categories")
        return existing

    print(f"🔧 Initializing default categories for user {user_id}...")

    # 获取嵌入服务
    try:
        embedding_service = get_embedding_service()
    except Exception as e:
        print(f"⚠️  Embedding service not available: {e}")
        print("   Categories will be created without embeddings")
        embedding_service = None

    created_categories = []

    for cat_config in DEFAULT_CATEGORIES:
        # 创建分类
        category = Category(
            user_id=user_id,
            name=cat_config["name"],
            description=cat_config["description"],
            color=cat_config["color"],
            icon=cat_config["icon"],
            keywords=cat_config["keywords"],
            position=cat_config["position"],
            level=1,  # 顶级分类
            bookmark_count=0
        )

        # 生成分类向量嵌入（用于AI分类）
        if embedding_service:
            try:
                # 使用分类名称+关键词生成嵌入
                text = f"{cat_config['name']}. {', '.join(cat_config['keywords'])}"
                embedding = await embedding_service.generate_embedding(text)
                category.embedding = embedding
                print(f"   ✅ Generated embedding for category: {cat_config['name']}")
            except Exception as e:
                print(f"   ⚠️  Failed to generate embedding for {cat_config['name']}: {e}")

        db.add(category)
        created_categories.append(category)

    # 提交到数据库
    await db.commit()

    # 刷新以获取ID
    for category in created_categories:
        await db.refresh(category)

    print(f"✅ Created {len(created_categories)} default categories for user {user_id}")

    return created_categories


async def get_or_init_categories(
    db: AsyncSession,
    user_id: int
) -> List[Category]:
    """
    获取用户分类，如果不存在则初始化默认分类

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        分类列表
    """
    result = await db.execute(
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.position)
    )
    categories = result.scalars().all()

    if not categories:
        # 初始化默认分类
        categories = await init_default_categories(db, user_id)

    return categories


async def reset_user_categories(
    db: AsyncSession,
    user_id: int
) -> List[Category]:
    """
    重置用户的分类（删除所有现有分类，重新初始化）

    注意：这将删除所有自定义分类！

    Args:
        db: 数据库会话
        user_id: 用户ID

    Returns:
        新创建的分类列表
    """
    # 删除现有分类
    result = await db.execute(
        select(Category).where(Category.user_id == user_id)
    )
    existing = result.scalars().all()

    for category in existing:
        await db.delete(category)

    await db.commit()

    print(f"🗑️  Deleted {len(existing)} existing categories for user {user_id}")

    # 重新初始化
    return await init_default_categories(db, user_id)


if __name__ == "__main__":
    """
    测试脚本
    """
    import asyncio
    from app.database import get_db

    async def test():
        async for db in get_db():
            # 假设用户ID为1（实际应从认证获取）
            categories = await get_or_init_categories(db, 1)

            print("\n📊 User Categories:")
            for cat in categories:
                print(f"   - {cat.icon} {cat.name} ({cat.color})")

            break

    asyncio.run(test())
