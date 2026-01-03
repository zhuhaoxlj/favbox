"""
Batch Embedding Script

批量处理书签的向量化，支持中断继续和进度报告。
"""

import asyncio
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import time

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import get_db
from app.models.bookmark import Bookmark
from app.services.embedding_service import get_embedding_service
from app.services.classification_service import get_classification_service
from app.models.category import Category


class BatchEmbedder:
    """
    批量向量化处理器
    """

    def __init__(
        self,
        batch_size: int = 100,
        overwrite: bool = False,
        also_classify: bool = True
    ):
        """
        初始化批量处理器

        Args:
            batch_size: 批次大小
            overwrite: 是否覆盖已有向量
            also_classify: 是否同时进行AI分类
        """
        self.batch_size = batch_size
        self.overwrite = overwrite
        self.also_classify = also_classify
        self.embedding_service = None
        self.classification_service = None

        # 统计信息
        self.stats = {
            "total": 0,
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "start_time": None,
            "end_time": None
        }

    async def process_all_bookmarks(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Dict:
        """
        处理用户所有书签的向量化

        Args:
            db: 数据库会话
            user_id: 用户ID

        Returns:
            处理统计信息
        """
        self.stats["start_time"] = datetime.now()

        print(f"🚀 Starting batch embedding for user {user_id}")
        print(f"   Batch size: {self.batch_size}")
        print(f"   Overwrite: {self.overwrite}")
        print(f"   Also classify: {self.also_classify}")

        # 1. 初始化服务
        try:
            self.embedding_service = get_embedding_service()
            if self.also_classify:
                self.classification_service = get_classification_service()
            print("✅ Services initialized")
        except Exception as e:
            print(f"❌ Failed to initialize services: {e}")
            return self.stats

        # 2. 获取需要处理的书签
        query = select(Bookmark).where(Bookmark.user_id == user_id)

        if not self.overwrite:
            # 只处理没有向量的书签
            query = query.where(Bookmark.ai_embedding.is_(None))

        result = await db.execute(query)
        bookmarks = result.scalars().all()

        self.stats["total"] = len(bookmarks)

        if self.stats["total"] == 0:
            print("✅ No bookmarks to process")
            return self.stats

        print(f"📊 Found {self.stats['total']} bookmarks to process")
        print()

        # 3. 如果需要分类，获取可用分类
        categories = []
        if self.also_classify:
            cat_result = await db.execute(
                select(Category).where(Category.user_id == user_id)
            )
            categories = cat_result.scalars().all()
            print(f"📁 Found {len(categories)} categories")

        # 4. 分批处理
        for i in range(0, len(bookmarks), self.batch_size):
            batch = bookmarks[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(bookmarks) + self.batch_size - 1) // self.batch_size

            print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} bookmarks)")

            await self._process_batch(db, batch, categories)

            # 每批次后提交
            await db.commit()

            # 进度报告
            progress = (self.stats["processed"] / self.stats["total"]) * 100
            print(f"   Progress: {progress:.1f}%")
            print(f"   Success: {self.stats['success']}, Failed: {self.stats['failed']}, Skipped: {self.stats['skipped']}")
            print()

        # 5. 创建向量索引（如果所有书签都已向量化）
        await self._create_vector_indexes(db)

        self.stats["end_time"] = datetime.now()
        duration = (self.stats["end_time"] - self.stats["start_time"]).total_seconds()

        print("=" * 60)
        print("✅ Batch embedding completed!")
        print(f"   Total: {self.stats['total']}")
        print(f"   Processed: {self.stats['processed']}")
        print(f"   Success: {self.stats['success']}")
        print(f"   Failed: {self.stats['failed']}")
        print(f"   Skipped: {self.stats['skipped']}")
        print(f"   Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
        print(f"   Average: {duration/self.stats['processed']:.2f}s per bookmark")
        print("=" * 60)

        return self.stats

    async def _process_batch(
        self,
        db: AsyncSession,
        bookmarks: List[Bookmark],
        categories: List[Category]
    ):
        """
        处理单个批次
        """
        # 准备数据
        texts = [(bm.title, bm.description or "") for bm in bookmarks]

        try:
            # 1. 批量生成向量
            print(f"   🔄 Generating embeddings...")
            embeddings = await self.embedding_service.batch_generate_embeddings(texts)

            # 2. 同时进行分类（如果启用）
            classifications = []
            if self.also_classify and categories:
                print(f"   🤖 Classifying bookmarks...")
                for idx, bookmark in enumerate(bookmarks):
                    try:
                        cat_id, confidence, cat_name = await self.classification_service.classify_bookmark(
                            title=bookmark.title,
                            description=bookmark.description,
                            url=bookmark.url,
                            available_categories=categories
                        )
                        classifications.append({
                            "bookmark_id": bookmark.id,
                            "category_id": cat_id,
                            "confidence": confidence
                        })
                    except Exception as e:
                        print(f"      ⚠️  Classification failed for {bookmark.id}: {e}")
                        classifications.append(None)

            # 3. 更新书签
            print(f"   💾 Updating bookmarks...")
            for idx, bookmark in enumerate(bookmarks):
                try:
                    # 更新向量
                    bookmark.ai_embedding = embeddings[idx]
                    bookmark.last_ai_analysis_at = datetime.now()

                    # 更新分类
                    if self.also_classify and idx < len(classifications):
                        classification = classifications[idx]
                        if classification:
                            bookmark.ai_category_id = classification["category_id"]

                    self.stats["success"] += 1

                except Exception as e:
                    print(f"      ❌ Failed to update bookmark {bookmark.id}: {e}")
                    self.stats["failed"] += 1

                self.stats["processed"] += 1

        except Exception as e:
            print(f"   ❌ Batch processing failed: {e}")
            # 整个批次标记为失败
            self.stats["failed"] += len(bookmarks)
            self.stats["processed"] += len(bookmarks)

    async def _create_vector_indexes(self, db: AsyncSession):
        """创建向量索引"""
        try:
            # 检查是否已有索引
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT indexname FROM pg_indexes
                WHERE tablename = 'bookmarks'
                  AND indexname LIKE '%embedding%'
            """))
            existing_indexes = result.fetchall()

            if existing_indexes:
                print(f"   ✅ Vector indexes already exist: {[r[0] for r in existing_indexes]}")
                return

            print("   📊 Creating vector indexes...")

            # HNSW索引 - 余弦相似度
            await db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bookmarks_embedding_hnsw
                ON bookmarks USING hnsw (ai_embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """))

            print("   ✅ Vector indexes created")

        except Exception as e:
            print(f"   ⚠️  Failed to create indexes: {e}")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="Batch embed bookmarks")
    parser.add_argument("--user-id", type=int, required=True, help="User ID")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing embeddings")
    parser.add_argument("--no-classify", action="store_true", help="Skip classification")

    args = parser.parse_args()

    # 获取数据库会话
    async for db in get_db():
        embedder = BatchEmbedder(
            batch_size=args.batch_size,
            overwrite=args.overwrite,
            also_classify=not args.no_classify
        )

        await embedder.process_all_bookmarks(db, args.user_id)
        break


if __name__ == "__main__":
    asyncio.run(main())
