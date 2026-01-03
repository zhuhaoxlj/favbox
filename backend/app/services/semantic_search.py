"""
Semantic Search Service using vector embeddings
"""

from typing import List, Optional
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.models.bookmark import Bookmark
from app.config import get_settings

settings = get_settings()


class SemanticSearchService:
    """Service for semantic search using vector embeddings"""

    def __init__(self):
        self.api_key = getattr(settings, "gemini_api_key", None)
        self.embedding_model = "text-embedding-004"

    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate vector embedding for text

        Args:
            text: Text to embed

        Returns:
            Vector embedding or None if failed
        """
        if not self.api_key:
            return None

        try:
            import httpx

            api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.embedding_model}:embedContent?key={self.api_key}"

            payload = {"content": {"parts": [{"text": text}]}}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, json=payload)
                response.raise_for_status()

                result = response.json()
                embedding = result.get("embedding", {}).get("values", [])

                return embedding if embedding else None

        except Exception as e:
            print(f"Failed to generate embedding: {e}")
            return None

    async def search_bookmarks(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        limit: int = 20,
        min_similarity: float = 0.5,
    ) -> List[tuple[Bookmark, float]]:
        """
        Perform semantic search on bookmarks

        Args:
            db: Database session
            user_id: User ID
            query: Search query
            limit: Maximum results
            min_similarity: Minimum similarity threshold (0-1)

        Returns:
            List of (bookmark, similarity_score) tuples
        """
        # Generate embedding for query
        query_embedding = await self.generate_embedding(query)

        if not query_embedding:
            # Fallback to text search
            return await self._fallback_text_search(db, user_id, query, limit)

        # Get all bookmarks for user that have embeddings
        result = await db.execute(
            select(Bookmark).where(
                and_(
                    Bookmark.user_id == user_id,
                    Bookmark.ai_embedding != None,
                    Bookmark.ai_embedding != [],
                )
            )
        )
        bookmarks = result.scalars().all()

        # Calculate similarity scores
        scored_bookmarks = []
        for bookmark in bookmarks:
            if bookmark.ai_embedding:
                similarity = self._cosine_similarity(
                    query_embedding, bookmark.ai_embedding
                )
                if similarity >= min_similarity:
                    scored_bookmarks.append((bookmark, similarity))

        # Sort by similarity and limit
        scored_bookmarks.sort(key=lambda x: x[1], reverse=True)
        return scored_bookmarks[:limit]

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        try:
            arr1 = np.array(vec1)
            arr2 = np.array(vec2)

            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            return float(dot_product / (norm1 * norm2))

        except Exception:
            return 0.0

    async def _fallback_text_search(
        self, db: AsyncSession, user_id: int, query: str, limit: int
    ) -> List[tuple[Bookmark, float]]:
        """Fallback to simple text search if embedding fails"""
        result = await db.execute(
            select(Bookmark)
            .where(
                and_(
                    Bookmark.user_id == user_id,
                    or_(
                        Bookmark.title.ilike(f"%{query}%"),
                        Bookmark.description.ilike(f"%{query}%"),
                        Bookmark.notes.ilike(f"%{query}%"),
                    ),
                )
            )
            .limit(limit)
        )
        bookmarks = result.scalars().all()

        # Return with dummy similarity scores
        return [(bm, 0.5) for bm in bookmarks]

    async def update_bookmark_embedding(self, db: AsyncSession, bookmark: Bookmark):
        """Update embedding for a bookmark"""
        # Combine title, description, and notes for embedding
        text_parts = [bookmark.title]

        if bookmark.description:
            text_parts.append(bookmark.description)
        if bookmark.notes:
            text_parts.append(bookmark.notes)
        if bookmark.tags:
            text_parts.extend(bookmark.tags)

        text = " ".join(text_parts)

        # Generate embedding
        embedding = await self.generate_embedding(text)

        if embedding:
            bookmark.ai_embedding = embedding
            await db.commit()


semantic_search = SemanticSearchService()
