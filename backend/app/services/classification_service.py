"""
AI Classification Service

使用Gemini对书签进行智能分类。
"""

import asyncio
import json
from typing import List, Tuple, Optional, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google import genai
import logging

from app.models.category import Category
from app.models.bookmark import Bookmark
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class ClassificationService:
    """
    AI分类引擎 - 使用Gemini进行智能分类
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化分类服务

        Args:
            api_key: Gemini API密钥
        """
        self.api_key = api_key or settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")

        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-1.5-flash"  # 使用快速模型

    async def classify_bookmark(
        self,
        title: str,
        description: Optional[str],
        url: str,
        available_categories: List[Category],
        user_keywords: Optional[List[str]] = None
    ) -> Tuple[int, float, str]:
        """
        使用Gemini对单个书签分类

        Args:
            title: 书签标题
            description: 页面描述
            url: 书签URL
            available_categories: 可用的分类列表
            user_keywords: 用户提供的额外关键词

        Returns:
            (category_id, confidence_score, category_name)

        Example:
            >>> service = ClassificationService()
            >>> cat_id, confidence, name = await service.classify_bookmark(
            ...     "Vue.js教程",
            ...     "学习Vue3框架",
            ...     "https://vuejs.org",
            ...     categories
            ... )
        """
        if not available_categories:
            raise ValueError("No categories available for classification")

        # 构建分类选项
        category_options = self._build_category_prompt(available_categories, user_keywords)

        # 构建完整提示
        prompt = self._build_classification_prompt(
            title=title,
            description=description,
            url=url,
            category_options=category_options
        )

        try:
            # 调用Gemini API
            result = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=genai.GenerateContentConfig(
                    temperature=0.1,  # 低温度以获得更确定的结果
                    max_output_tokens=100,
                    response_mime_type="application/json"
                )
            )

            # 解析JSON响应
            response_text = result.candidates[0].content.parts[0].text
            response_data = json.loads(response_text)

            category_name = response_data.get("category", "")
            confidence = response_data.get("confidence", 0.0)

            # 查找匹配的分类ID
            category_id = None
            for cat in available_categories:
                if cat.name == category_name:
                    category_id = cat.id
                    break

            if category_id is None:
                # 未找到匹配分类，使用第一个分类作为默认
                logger.warning(f"Category '{category_name}' not found, using default")
                category_id = available_categories[0].id
                confidence = 0.3  # 低置信度

            logger.info(f"Classified '{title}' -> {category_name} (confidence: {confidence:.2f})")

            return category_id, confidence, category_name

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            # 返回默认分类
            return available_categories[0].id, 0.0, available_categories[0].name

        except Exception as e:
            logger.error(f"Classification failed: {e}")
            # 返回默认分类
            return available_categories[0].id, 0.0, available_categories[0].name

    async def batch_classify(
        self,
        bookmarks: List[Bookmark],
        available_categories: List[Category],
        batch_size: int = 10,
        max_concurrency: int = 5
    ) -> Dict[str, any]:
        """
        批量分类书签

        Args:
            bookmarks: 书签列表
            available_categories: 可用分类列表
            batch_size: 批次大小
            max_concurrency: 最大并发数

        Returns:
            统计信息字典
        """
        total = len(bookmarks)
        processed = 0
        success = 0
        failed = 0
        results = []

        logger.info(f"Starting batch classification for {total} bookmarks")

        # 分批处理
        for i in range(0, total, batch_size):
            batch = bookmarks[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            logger.info(f"Processing classification batch {batch_num}/{total_batches} ({len(batch)} items)")

            # 限制并发
            semaphore = asyncio.Semaphore(max_concurrency)

            async def classify_with_semaphore(bookmark: Bookmark):
                async with semaphore:
                    try:
                        cat_id, confidence, cat_name = await self.classify_bookmark(
                            title=bookmark.title,
                            description=bookmark.description,
                            url=bookmark.url,
                            available_categories=available_categories
                        )

                        return {
                            "bookmark_id": bookmark.id,
                            "category_id": cat_id,
                            "category_name": cat_name,
                            "confidence": confidence,
                            "success": True
                        }

                    except Exception as e:
                        logger.error(f"Failed to classify bookmark {bookmark.id}: {e}")
                        return {
                            "bookmark_id": bookmark.id,
                            "error": str(e),
                            "success": False
                        }

            # 并发处理批次
            batch_results = await asyncio.gather(*[
                classify_with_semaphore(bm) for bm in batch
            ])

            results.extend(batch_results)

            # 更新统计
            for result in batch_results:
                processed += 1
                if result.get("success"):
                    success += 1
                else:
                    failed += 1

            # 避免API速率限制
            if i + batch_size < total:
                await asyncio.sleep(2)

        logger.info(f"Batch classification completed: {success} success, {failed} failed")

        return {
            "total": total,
            "processed": processed,
            "success": success,
            "failed": failed,
            "results": results
        }

    def _build_category_prompt(
        self,
        categories: List[Category],
        user_keywords: Optional[List[str]] = None
    ) -> str:
        """
        构建分类选项提示

        Returns:
            分类描述字符串
        """
        category_descriptions = []
        for cat in categories:
            keywords_str = ", ".join(cat.keywords[:5]) if cat.keywords else ""
            desc = f"- {cat.name}"
            if keywords_str:
                desc += f" (关键词: {keywords_str})"
            category_descriptions.append(desc)

        prompt = "可用分类:\n" + "\n".join(category_descriptions)

        if user_keywords:
            prompt += f"\n\n用户指定关键词: {', '.join(user_keywords)}"

        return prompt

    def _build_classification_prompt(
        self,
        title: str,
        description: Optional[str],
        url: str,
        category_options: str
    ) -> str:
        """
        构建完整的分类提示

        Returns:
            完整提示字符串
        """
        prompt = f"""你是一个网页分类专家。请根据网页的标题、描述和URL，将其归类到最合适的分类中。

{category_options}

网页信息:
- 标题: {title}
- 描述: {description or '无描述'}
- URL: {url}

请返回JSON格式：
{{
    "category": "分类名称",
    "confidence": 0.0-1.0之间的置信度分数
}}

要求：
1. 只返回一个分类名称（必须从上面的可用分类中选择）
2. 置信度分数应该反映分类的确定性
3. 如果网页内容不明确，选择最相关的分类并给出较低置信度
4. 确保返回的是纯JSON，不要有其他文本

分类结果："""

        return prompt


# 全局单例
_classification_service: Optional[ClassificationService] = None


def get_classification_service() -> ClassificationService:
    """
    获取分类服务单例

    Returns:
        ClassificationService实例
    """
    global _classification_service
    if _classification_service is None:
        _classification_service = ClassificationService()
    return _classification_service
