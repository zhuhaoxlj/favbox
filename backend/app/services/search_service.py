"""
Semantic Search Service

基于pgvector的语义搜索服务，支持向量搜索和多条件过滤。
"""

from typing import List, Optional, Dict, Tuple
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
import logging

from app.models.bookmark import Bookmark
from app.models.category import Category
from app.services.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class SearchFilters:
    """搜索过滤器"""

    def __init__(
        self,
        domains: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        category_ids: Optional[List[int]] = None,
        date_start: Optional[str] = None,
        date_end: Optional[str] = None,
        min_confidence: Optional[float] = None
    ):
        self.domains = domains or []
        self.tags = tags or []
        self.category_ids = category_ids or []
        self.date_start = date_start
        self.date_end = date_end
        self.min_confidence = min_confidence


class SearchResult:
    """搜索结果"""

    def __init__(
        self,
        bookmark: Bookmark,
        similarity: float,
        category: Optional[Category] = None
    ):
        self.bookmark = bookmark
        self.similarity = similarity
        self.category = category

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "id": self.bookmark.id,
            "title": self.bookmark.title,
            "url": self.bookmark.url,
            "description": self.bookmark.description,
            "domain": self.bookmark.domain,
            "favicon": self.bookmark.favicon,
            "tags": self.bookmark.tags,
            "ai_tags": self.bookmark.ai_tags,
            "category": {
                "id": self.category.id,
                "name": self.category.name,
                "icon": self.category.icon,
                "color": self.category.color
            } if self.category else None,
            "similarity": round(self.similarity, 4),
            "created_at": self.bookmark.created_at.isoformat() if self.bookmark.created_at else None
        }


class SearchService:
    """
    语义搜索服务
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def semantic_search(
        self,
        query: str,
        user_id: int,
        filters: Optional[SearchFilters] = None,
        limit: int = 20,
        min_similarity: float = 0.5
    ) -> Tuple[List[SearchResult], str]:
        """
        纯向量语义搜索

        Args:
            query: 搜索查询文本
            user_id: 用户ID
            filters: 过滤条件
            limit: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            (搜索结果列表, 使用的查询向量)

        Example:
            >>> service = SearchService(db)
            >>> results, query_vec = await service.semantic_search("Vue教程", user_id=1)
        """
        # 1. 生成查询向量
        try:
            embedding_service = get_embedding_service()
            query_embedding = await embedding_service.generate_embedding(query)
            query_vector_str = "[" + ",".join(map(str, query_embedding)) + "]"
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            return [], ""

        # 2. 构建基础查询
        base_query = select(Bookmark).where(
            and_(
                Bookmark.user_id == user_id,
                Bookmark.ai_embedding.isnot(None)
            )
        )

        # 3. 应用过滤条件
        if filters:
            base_query = self._apply_filters(base_query, filters)

        # 4. 执行向量相似度搜索（使用余弦距离）
        # 注意：<=> 是余弦距离操作符 (1 - cosine_similarity)
        # 我们需要将其转换为相似度: similarity = 1 - distance
        search_query = text(f"""
            SELECT
                id,
                title,
                url,
                description,
                domain,
                favicon,
                tags,
                ai_tags,
                ai_category_id,
                created_at,
                1 - (ai_embedding <=> :query_vector::vector) as similarity
            FROM bookmarks
            WHERE user_id = :user_id
              AND ai_embedding IS NOT NULL
              AND 1 - (ai_embedding <=> :query_vector::vector) >= :min_similarity
            ORDER BY ai_embedding <=> :query_vector::vector
            LIMIT :limit
        """)

        # 执行查询
        result = await self.db.execute(
            search_query,
            {
                "query_vector": query_vector_str,
                "user_id": user_id,
                "min_similarity": min_similarity,
                "limit": limit
            }
        )

        rows = result.fetchall()

        # 5. 获取分类信息
        bookmark_ids = [row[0] for row in rows]
        categories_map = await self._get_categories_for_bookmarks(bookmark_ids)

        # 6. 构建结果
        results = []
        for row in rows:
            bookmark = Bookmark(
                id=row[0],
                title=row[1],
                url=row[2],
                description=row[3],
                domain=row[4],
                favicon=row[5],
                tags=row[6],
                ai_tags=row[7],
                ai_category_id=row[8],
                created_at=row[9]
            )
            similarity = row[10]
            category = categories_map.get(bookmark.id)

            results.append(SearchResult(bookmark, similarity, category))

        logger.info(f"Semantic search for '{query}' returned {len(results)} results")

        return results, query_vector_str

    async def find_similar_bookmarks(
        self,
        bookmark_id: int,
        user_id: int,
        limit: int = 10,
        min_similarity: float = 0.6
    ) -> List[SearchResult]:
        """
        查找相似书签（基于向量）

        Args:
            bookmark_id: 参考书签ID
            user_id: 用户ID
            limit: 返回结果数量
            min_similarity: 最小相似度

        Returns:
            相似书签列表
        """
        # 获取参考书签的向量
        result = await self.db.execute(
            select(Bookmark).where(
                and_(
                    Bookmark.id == bookmark_id,
                    Bookmark.user_id == user_id,
                    Bookmark.ai_embedding.isnot(None)
                )
            )
        )
        reference_bookmark = result.scalar_one_or_none()

        if not reference_bookmark:
            logger.warning(f"Bookmark {bookmark_id} not found or has no embedding")
            return []

        # 使用参考书签的向量进行搜索
        reference_embedding = reference_bookmark.ai_embedding
        if isinstance(reference_embedding, list):
            vector_str = "[" + ",".join(map(str, reference_embedding)) + "]"
        else:
            logger.error(f"Invalid embedding format for bookmark {bookmark_id}")
            return []

        # 执行相似度搜索
        search_query = text("""
            SELECT
                id,
                title,
                url,
                description,
                domain,
                favicon,
                tags,
                ai_tags,
                ai_category_id,
                created_at,
                1 - (ai_embedding <=> :vector::vector) as similarity
            FROM bookmarks
            WHERE user_id = :user_id
              AND id != :bookmark_id
              AND ai_embedding IS NOT NULL
              AND 1 - (ai_embedding <=> :vector::vector) >= :min_similarity
            ORDER BY ai_embedding <=> :vector::vector
            LIMIT :limit
        """)

        result = await self.db.execute(
            search_query,
            {
                "vector": vector_str,
                "user_id": user_id,
                "bookmark_id": bookmark_id,
                "min_similarity": min_similarity,
                "limit": limit
            }
        )

        rows = result.fetchall()

        # 获取分类信息
        bookmark_ids = [row[0] for row in rows]
        categories_map = await self._get_categories_for_bookmarks(bookmark_ids)

        # 构建结果
        results = []
        for row in rows:
            bookmark = Bookmark(
                id=row[0],
                title=row[1],
                url=row[2],
                description=row[3],
                domain=row[4],
                favicon=row[5],
                tags=row[6],
                ai_tags=row[7],
                ai_category_id=row[8],
                created_at=row[9]
            )
            similarity = row[10]
            category = categories_map.get(bookmark.id)

            results.append(SearchResult(bookmark, similarity, category))

        logger.info(f"Found {len(results)} similar bookmarks to bookmark {bookmark_id}")

        return results

    def _apply_filters(self, query, filters: SearchFilters):
        """应用过滤条件到查询"""
        conditions = []

        if filters.domains:
            conditions.append(Bookmark.domain.in_(filters.domains))

        if filters.tags:
            # JSON数组包含任一标签
            tag_conditions = [
                Bookmark.tags.contains([tag]) for tag in filters.tags
            ]
            conditions.append(or_(*tag_conditions))

        if filters.category_ids:
            conditions.append(Bookmark.ai_category_id.in_(filters.category_ids))

        if filters.date_start or filters.date_end:
            from datetime import datetime
            if filters.date_start:
                start = datetime.fromisoformat(filters.date_start)
                conditions.append(Bookmark.created_at >= start)
            if filters.date_end:
                end = datetime.fromisoformat(filters.date_end)
                conditions.append(Bookmark.created_at <= end)

        if conditions:
            query = query.where(and_(*conditions))

        return query

    async def _get_categories_for_bookmarks(
        self,
        bookmark_ids: List[int]
    ) -> Dict[int, Category]:
        """批量获取书签的分类"""
        if not bookmark_ids:
            return {}

        result = await self.db.execute(
            select(Category).where(
                Category.id.in_(
                    select(Bookmark.ai_category_id).where(
                        and_(
                            Bookmark.id.in_(bookmark_ids),
                            Bookmark.ai_category_id.isnot(None)
                        )
                    )
                )
            )
        )

        categories = result.scalars().all()

        # 构建书签ID -> 分类映射
        # 需要通过bookmark来获取对应关系
        mapping = {}
        for category in categories:
            # 查找使用此分类的书签
            bookmark_result = await self.db.execute(
                select(Bookmark.id).where(Bookmark.ai_category_id == category.id)
            )
            for row in bookmark_result:
                mapping[row[0]] = category

        return mapping
