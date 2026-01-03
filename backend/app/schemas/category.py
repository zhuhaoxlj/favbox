"""
Category Schemas
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class CategoryBase(BaseModel):
    """基础分类Schema"""
    name: str = Field(..., min_length=1, max_length=100, description="分类名称")
    parent_id: Optional[int] = Field(None, description="父分类ID，None表示顶级分类")
    description: Optional[str] = Field(None, description="分类描述")
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$', description="颜色代码 #RRGGBB")
    icon: Optional[str] = Field(None, max_length=50, description="图标名或emoji")
    keywords: Optional[List[str]] = Field(default_factory=list, description="分类关键词（AI分类辅助）")
    position: Optional[int] = Field(0, description="排序位置")


class CategoryCreate(CategoryBase):
    """创建分类"""
    pass


class CategoryUpdate(BaseModel):
    """更新分类"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r'^#[0-9A-Fa-f]{6}$')
    icon: Optional[str] = Field(None, max_length=50)
    keywords: Optional[List[str]] = None
    position: Optional[int] = None


class CategoryResponse(CategoryBase):
    """分类响应（包含统计信息）"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    level: int
    bookmark_count: int
    created_at: datetime
    updated_at: datetime
    children: List["CategoryResponse"] = []

    # 计算属性
    @property
    def is_root(self) -> bool:
        return self.parent_id is None


class CategoryTree(CategoryResponse):
    """分类树（包含子分类）"""
    pass


class CategoryStats(BaseModel):
    """分类统计"""
    total_categories: int
    root_categories: int
    total_bookmarks_in_categories: int


# 更新前向引用
CategoryResponse.model_rebuild()
