from typing import Dict, Set
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)
        logger.info(f"User {user_id} connected. Total connections: {len(self.active_connections.get(user_id, set()))}")
    
    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info(f"User {user_id} disconnected. Total connections: {len(self.active_connections.get(user_id, set()))}")
    
    async def send_personal_message(self, message: dict, user_id: int):
        if user_id in self.active_connections and self.active_connections[user_id]:
            for connection in list(self.active_connections[user_id]):
                try:
                    await connection.send_json(message)
                    logger.debug(f"Message sent to user {user_id}: {message}")
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    self.disconnect(connection, user_id)
        else:
            logger.debug(f"No active connections for user {user_id}")
    
    async def broadcast_to_users(self, message: dict, user_ids: list[int]):
        for user_id in user_ids:
            await self.send_personal_message(message, user_id)

manager = ConnectionManager()