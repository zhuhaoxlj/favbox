"""
AI Tagger Service for generating tags and categories
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
import httpx
import json

from app.config import get_settings

settings = get_settings()


class AITaggerService:
    """Service for generating AI-based tags and categories"""

    def __init__(self):
        self.api_key = getattr(settings, "gemini_api_key", None)
        # 使用 gemini-3-pro-preview 模型（根据官方示例）
        self.api_url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-pro-preview:generateContent"

        # 代理配置（从环境变量读取）
        self.proxy = getattr(settings, "http_proxy", None) or getattr(settings, "https_proxy", None)

    async def test_api_key(self) -> bool:
        """测试 API Key 是否有效"""
        if not self.api_key:
            return False

        try:
            # 配置代理（如果设置）
            proxies = None
            if self.proxy:
                proxies = {"http://": self.proxy, "https://": self.proxy}

            async with httpx.AsyncClient(timeout=30.0, proxies=proxies) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}",
                    json={
                        "contents": [
                            {
                                "parts": [{"text": "Hello, please respond with 'OK'"}]
                            }
                        ]
                    },
                )
                return response.status_code == 200
        except Exception as e:
            print(f"API Key test failed: {e}")
            return False

    async def generate_tags(
        self,
        title: str,
        description: Optional[str] = None,
        url: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        max_tags: int = 5,
    ) -> tuple[List[str], Dict[str, float]]:
        """
        Generate tags for a bookmark using AI

        Args:
            title: Bookmark title
            description: Page description
            url: Bookmark URL
            keywords: Page keywords
            max_tags: Maximum number of tags to generate

        Returns:
            Tuple of (tags list, confidence scores dict)
        """
        if not self.api_key:
            # Fallback: simple keyword-based tagging
            return self._generate_simple_tags(
                title, description, url, keywords, max_tags
            )

        prompt = self._build_tag_prompt(title, description, url, keywords, max_tags)

        try:
            # 配置代理（如果设置）
            proxies = None
            if self.proxy:
                proxies = {"http://": self.proxy, "https://": self.proxy}
                print(f"[DEBUG] Using proxy: {self.proxy}")

            async with httpx.AsyncClient(
                timeout=60.0,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                proxies=proxies
            ) as client:
                response = await client.post(
                    f"{self.api_url}?key={self.api_key}", json=prompt
                )

                print(f"[DEBUG] API Status Code: {response.status_code}")

                # 打印 400 错误的响应内容
                if response.status_code == 400:
                    error_detail = response.text
                    print(f"[ERROR] AI API returned 400 Bad Request:")
                    print(f"[ERROR] Response: {error_detail}")
                    print(f"[ERROR] Request: {json.dumps(prompt, ensure_ascii=False, indent=2)}")
                    return self._generate_simple_tags(
                        title, description, url, keywords, max_tags
                    )

                response.raise_for_status()

                result = response.json()
                print(f"[DEBUG] Full API Response: {json.dumps(result, ensure_ascii=False, indent=2)}")
                tags, confidences = self._parse_tag_response(result)

                if tags:
                    print(f"AI generated {len(tags)} tags successfully: {tags}")
                    return tags[:max_tags], confidences
                else:
                    print("AI returned empty tags, using fallback")
                    return self._generate_simple_tags(
                        title, description, url, keywords, max_tags
                    )

        except Exception as e:
            print(f"AI tag generation failed: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to simple tagging
            return self._generate_simple_tags(
                title, description, url, keywords, max_tags
            )

    def _build_tag_prompt(
        self,
        title: str,
        description: Optional[str],
        url: Optional[str],
        keywords: Optional[List[str]],
        max_tags: int,
    ) -> dict:
        """Build the prompt for AI tag generation"""
        context_parts = [f"Title: {title}"]

        if description:
            context_parts.append(f"Description: {description}")
        if url:
            context_parts.append(f"URL: {url}")
        if keywords:
            context_parts.append(f"Keywords: {', '.join(keywords)}")

        context = "\n".join(context_parts)

        prompt_text = f"""Analyze this bookmark and generate relevant tags:

{context}

Generate up to {max_tags} relevant tags. Each tag should be:
- Short (1-3 words)
- Descriptive and useful for categorization
- In the same language as the content
- Not too generic (avoid 'web', 'online', 'website' unless very specific)

Respond in JSON format:
{{
  "tags": ["tag1", "tag2", "tag3"],
  "confidence": {{"tag1": 0.9, "tag2": 0.8, "tag3": 0.7}}
}}"""

        return {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 8192,  # 增加到 8192，为思考令牌留出空间
            },
        }

    def _parse_tag_response(self, response: dict) -> tuple[List[str], Dict[str, float]]:
        """Parse AI response to extract tags and confidence scores"""
        try:
            content = response.get("candidates", [{}])[0].get("content", {})
            text = content.get("parts", [{}])[0].get("text", "")

            print(f"[DEBUG] AI raw response: {text}")

            # 尝试从 markdown 代码块中提取 JSON
            import re
            json_pattern = r'```json\s*\n(.*?)\n```'
            json_match = re.search(json_pattern, text, re.DOTALL)

            json_text = None
            if json_match:
                json_text = json_match.group(1).strip()
                print(f"[DEBUG] Extracted JSON from markdown code block")

            # 如果没有找到代码块，尝试直接解析
            if not json_text:
                json_text = text.strip()

            # 尝试解析 JSON
            result = json.loads(json_text)
            tags = result.get("tags", [])
            confidence = result.get("confidence", {})

            print(f"[DEBUG] Parsed tags: {tags}")
            print(f"[DEBUG] Parsed confidence: {confidence}")

            return tags, confidence
        except json.JSONDecodeError as e:
            print(f"[DEBUG] Failed to parse JSON, trying to extract tags from text: {e}")
            # 如果 JSON 解析失败，尝试从文本中提取标签
            content = response.get("candidates", [{}])[0].get("content", {})
            text = content.get("parts", [{}])[0].get("text", "")
            return self._extract_tags_from_text(text), {}
        except (KeyError, json.JSONDecodeError) as e:
            print(f"Failed to parse AI response: {e}")
            return [], {}

    def _extract_tags_from_text(self, text: str) -> List[str]:
        """从文本中提取标签，当 JSON 解析失败时使用"""
        tags = []

        # 尝试提取类似 ["tag1", "tag2", "tag3"] 的模式
        import re
        pattern = r'\["([^"]+)"(?:,\s*"([^"]+)")*\]'
        matches = re.findall(pattern, text)
        if matches:
            # 展平结果
            for match in matches:
                tags.extend([m for m in match if m])

        # 如果没有找到，尝试提取以 # 开头的标签
        if not tags:
            hashtag_pattern = r'#(\w+)'
            hashtags = re.findall(hashtag_pattern, text)
            tags = hashtags

        # 如果还是没有找到，提取关键名词
        if not tags and len(text) > 0:
            words = text.split()
            for word in words[:5]:  # 取前5个词
                if len(word) > 2 and word.isalpha():
                    tags.append(word)

        print(f"[DEBUG] Extracted tags from text: {tags}")
        return tags[:5]  # 最多返回5个标签

    def _generate_simple_tags(
        self,
        title: str,
        description: Optional[str],
        url: Optional[str],
        keywords: Optional[List[str]],
        max_tags: int,
    ) -> tuple[List[str], Dict[str, float]]:
        """Fallback: simple keyword-based tag generation"""
        tags = []
        confidence = {}

        # Extract domain from URL
        if url:
            try:
                from urllib.parse import urlparse

                domain = urlparse(url).netloc.replace("www.", "").split(".")[0]
                if domain and len(domain) > 2:
                    tags.append(domain)
                    confidence[domain] = 0.7
                    print(f"  [Fallback] Added domain tag: {domain}")
            except Exception as e:
                print(f"  [Fallback] Error extracting domain: {e}")

        # Use keywords
        if keywords:
            for kw in keywords[: max_tags - len(tags)]:
                if len(kw) <= 20 and len(tags) < max_tags:
                    tags.append(kw.lower())
                    confidence[kw.lower()] = 0.6
                    print(f"  [Fallback] Added keyword tag: {kw}")

        # Extract from title (simple word extraction)
        words = title.lower().split()
        for word in words:
            if (
                len(word) > 3
                and word.isalpha()
                and word not in tags
                and len(tags) < max_tags
            ):
                tags.append(word)
                confidence[word] = 0.5
                print(f"  [Fallback] Added title word tag: {word}")

        print(f"  [Fallback] Generated {len(tags)} tags: {tags}")
        return tags, confidence

    async def suggest_category(
        self,
        title: str,
        description: Optional[str] = None,
        url: Optional[str] = None,
        existing_categories: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Suggest a category for a bookmark

        Args:
            title: Bookmark title
            description: Page description
            url: Bookmark URL
            existing_categories: List of existing categories to match against

        Returns:
            Suggested category name or None
        """
        # This could be expanded to use AI for category suggestion
        # For now, we'll do a simple URL-based categorization
        if url:
            from urllib.parse import urlparse

            domain = urlparse(url).netloc.lower()

            # Simple domain-based categorization
            category_map = {
                "github": "Development",
                "stackoverflow": "Development",
                "dev.to": "Development",
                "medium": "Articles",
                "youtube": "Videos",
                "vimeo": "Videos",
                "wikipedia": "Reference",
                "reddit": "Social",
                "twitter": "Social",
                "linkedin": "Professional",
            }

            for key, category in category_map.items():
                if key in domain:
                    return category

        return None


ai_tagger = AITaggerService()
