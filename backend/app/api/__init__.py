from app.api.deps import get_current_user
from app.api.auth import router as auth_router
from app.api.bookmarks import router as bookmarks_router
from app.api.analytics import router as analytics_router
from app.api.collections import router as collections_router
from app.api.websocket import router as websocket_router
from app.api.backups import router as backups_router
from app.api.ai_tagging import router as ai_tagging_router
from app.api.search import router as search_router
from app.api.categories import router as categories_router
from app.api.semantic_search import router as semantic_search_router

__all__ = [
    "get_current_user",
    "auth_router",
    "bookmarks_router",
    "analytics_router",
    "collections_router",
    "websocket_router",
    "backups_router",
    "ai_tagging_router",
    "search_router",
    "categories_router",
    "semantic_search_router",
]
