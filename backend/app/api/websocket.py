"""
WebSocket API for Real-time Sync
"""
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.models.user import User
from app.utils.security import verify_token
from app.utils.websocket_manager import manager

router = APIRouter(tags=["WebSocket"])


async def get_user_from_token(token: str) -> User | None:
    """Verify token and get user for WebSocket connection"""
    payload = verify_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == int(user_id)))
        return result.scalar_one_or_none()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time bookmark sync.

    Connection: ws://server/api/ws?token=<jwt_token>

    Message types (server -> client):
    - bookmark_created: New bookmark created on another device
    - bookmark_updated: Bookmark updated on another device
    - bookmark_deleted: Bookmark deleted on another device
    - ping: Keep-alive ping

    Message types (client -> server):
    - pong: Response to ping
    - sync_request: Request full sync (server will respond via REST API)
    """
    # Authenticate
    user = await get_user_from_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid token")
        return

    # Connect
    await manager.connect(websocket, user.id)

    try:
        # Send connection confirmation
        await manager.send_personal_message(
            {
                "type": "connected",
                "user_id": user.id,
                "connections": manager.get_user_connection_count(user.id),
            },
            websocket,
        )

        # Listen for messages
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "pong":
                # Keep-alive response
                pass
            elif data.get("type") == "ping":
                # Client ping
                await manager.send_personal_message({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket, user.id)
    except Exception:
        manager.disconnect(websocket, user.id)
