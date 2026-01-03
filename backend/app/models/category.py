"""
Category Model - Hierarchical classification for bookmarks
"""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

# 仅在使用PostgreSQL时导入Vector
try:
    from pgvector.sqlalchemy import Vector
    HAS_PGVECTOR = True
except ImportError:
    # SQLite使用JSON存储向量
    Vector = None
    HAS_PGVECTOR = False

from app.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class Category(Base):
    """
    分类表 - 支持层级结构
    """
    __tablename__ = "categories"
    __table_args__ = (
        Index("ix_categories_user_parent", "user_id", "parent_id"),
        Index("ix_categories_user_level", "user_id", "level"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    # 分类层级
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # 分类名
    parent_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), nullable=True, index=True
    )  # 父分类ID, NULL表示主要分类
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 层级深度: 1=主分类, 2=子分类

    # 分类元数据
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # 颜色代码 #RRGGBB
    icon: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 图标名 (emoji或图标类名)

    # AI分类辅助
    keywords: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)  # 分类关键词
    # PostgreSQL使用Vector类型，SQLite使用JSON类型
    if HAS_PGVECTOR:
        embedding: Mapped[Optional[Vector]] = mapped_column(Vector(768), nullable=True)  # 分类中心向量
    else:
        embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)

    # 统计
    bookmark_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序位置

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="categories")
    children: Mapped[List["Category"]] = relationship(
        "Category",
        back_populates="parent",
        foreign_keys=[parent_id],
        cascade="all, delete-orphan",
        order_by="Category.position"
    )
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="children",
        remote_side=[id],
        foreign_keys=[parent_id]
    )
    bookmarks: Mapped[List["Bookmark"]] = relationship(
        "Bookmark",
        back_populates="category",
        foreign_keys="Bookmark.ai_category_id"
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', level={self.level}, user_id={self.user_id})>"

    @property
    def is_root(self) -> bool:
        """是否为顶级分类"""
        return self.parent_id is None

    @property
    def path(self) -> str:
        """获取分类完整路径"""
        if self.parent:
            return f"{self.parent.path} > {self.name}"
        return self.name
