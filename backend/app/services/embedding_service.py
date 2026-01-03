"""
Gemini Embedding Service

Generates 768-dimensional vector embeddings using Google Gemini API.
"""

import asyncio
from typing import List, Tuple, Optional
from google import genai
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Gemini嵌入服务 - 生成向量嵌入
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化嵌入服务

        Args:
            api_key: Gemini API密钥，默认从配置读取
        """
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "text-embedding-004"  # 768维
        self.dimension = 768

    async def generate_embedding(
        self,
        text: str,
        title: Optional[str] = None
    ) -> List[float]:
        """
        生成单个文本的向量嵌入

        Args:
            text: 文本内容
            title: 标题（可选，权重更高）

        Returns:
            768维向量

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.generate_embedding("Python教程")
            >>> len(embedding)
            768
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # 组合标题和内容（标题权重更高）
        combined_text = self._prepare_text(title, text)

        try:
            # 调用Gemini API
            result = await asyncio.to_thread(
                self.client.models.embed_content,
                model=self.model_name,
                content=combined_text
            )

            embedding = result.embedding.values
            logger.debug(f"Generated embedding for text: {text[:50]}... (dim={len(embedding)})")

            return embedding

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    async def batch_generate_embeddings(
        self,
        texts: List[Tuple[str, Optional[str]]],  # (title, description/text)
        batch_size: int = 100
    ) -> List[List[float]]:
        """
        批量生成嵌入

        Args:
            texts: 文本列表 [(title, text), ...]
            batch_size: 批次大小

        Returns:
            向量列表

        Example:
            >>> texts = [("Python教程", "..."), ("Vue.js", "...")]
            >>> embeddings = await service.batch_generate_embeddings(texts)
        """
        embeddings = []
        total = len(texts)

        logger.info(f"Starting batch embedding generation for {total} items (batch_size={batch_size})")

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} items)")

            # 并发处理批次
            batch_tasks = [
                self.generate_embedding(text, title)
                for title, text in batch
            ]

            try:
                batch_embeddings = await asyncio.gather(*batch_tasks, return_exceptions=True)

                # 处理结果
                for idx, result in enumerate(batch_embeddings):
                    if isinstance(result, Exception):
                        logger.error(f"Failed to embed item {i + idx}: {result}")
                        # 返回零向量作为占位符
                        embeddings.append([0.0] * self.dimension)
                    else:
                        embeddings.append(result)

                # 避免API速率限制
                if i + batch_size < total:
                    await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Batch {batch_num} failed: {e}")
                # 为整个批次添加零向量
                embeddings.extend([[0.0] * self.dimension] * len(batch))

        logger.info(f"Generated {len(embeddings)} embeddings total")
        return embeddings

    def _prepare_text(self, title: Optional[str], text: str) -> str:
        """
        准备用于嵌入的文本

        策略：标题重复两次以增加权重
        """
        if not title:
            return text[:5000]  # Gemini API限制

        # 标题权重更高
        combined = f"{title}. {title}. {text}"
        return combined[:5000]

    async def test_connection(self) -> bool:
        """
        测试API连接

        Returns:
            是否连接成功
        """
        try:
            test_embedding = await self.generate_embedding("test")
            return len(test_embedding) == self.dimension
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# 全局单例
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """
    获取嵌入服务单例

    Returns:
        EmbeddingService实例
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
