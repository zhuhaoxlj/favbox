from app.api.deps import get_current_user
from app.api.auth import router as auth_router
from app.api.bookmarks import router as bookmarks_router
from app.api.analytics import router as analytics_router
from app.api.collections import router as collections_router
from app.api.websocket import router as websocket_router

__all__ = [
    "get_current_user",
    "auth_router",
    "bookmarks_router",
    "analytics_router",
    "collections_router",
    "websocket_router",
]
