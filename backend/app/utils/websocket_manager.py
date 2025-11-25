"""
WebSocket Connection Manager
Manages real-time connections for bookmark sync across devices
"""
from typing import Dict, List
from fastapi import WebSocket
import json


class ConnectionManager:
    def __init__(self):
        # user_id -> list of WebSocket connections (multiple devices)
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

    async def broadcast_to_user(
        self, user_id: int, message: dict, exclude: WebSocket = None
    ):
        """
        Broadcast message to all devices of a user except the sender
        """
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                if connection != exclude:
                    try:
                        await connection.send_json(message)
                    except Exception:
                        # Connection might be closed
                        pass

    def get_user_connection_count(self, user_id: int) -> int:
        return len(self.active_connections.get(user_id, []))


# Global instance
manager = ConnectionManager()
