"""
FavBox Backend - FastAPI Application
"""

from contextlib import asynccontextmanager
import traceback

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.api import (
    auth_router,
    bookmarks_router,
    analytics_router,
    collections_router,
    websocket_router,
    backups_router,
    ai_tagging_router,
    search_router,
    categories_router,
    semantic_search_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize database
    await init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="FavBox Backend",
    description="Backend service for FavBox browser extension - bookmark sync, analytics, and collaboration",
    version="1.0.0",
    lifespan=lifespan,
)


# Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"\n{'=' * 60}")
    print(f"[ERROR] Unhandled exception in {request.url.path}")
    print(f"[ERROR] Method: {request.method}")
    print(f"[ERROR] Exception type: {type(exc).__name__}")
    print(f"[ERROR] Exception message: {str(exc)}")
    print(f"[ERROR] Traceback:")
    traceback.print_exc()
    print(f"{'=' * 60}\n")
    return JSONResponse(
        status_code=500,
        content={"detail": f"{type(exc).__name__}: {str(exc)}"},
    )


# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(bookmarks_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")
app.include_router(backups_router, prefix="/api")
app.include_router(ai_tagging_router, prefix="/api")
app.include_router(search_router, prefix="/api")
app.include_router(categories_router, prefix="/api")
app.include_router(semantic_search_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "FavBox Backend",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        limit_max_requests=100000,  # Increase max concurrent requests
        timeout_keep_alive=300,  # Increase keep-alive timeout
    )
