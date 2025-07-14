"""
WebSocket Connection Manager for Real-Time Notifications
Handles user connections, rooms, and message broadcasting
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.security import verify_token
from app.db.session import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        # Active connections: {user_id: {connection_id: websocket}}
        self.active_connections: Dict[str, Dict[str, WebSocket]] = {}

        # Room memberships: {room_name: {user_id: set_of_connection_ids}}
        self.rooms: Dict[str, Dict[str, Set[str]]] = {}

        # Connection metadata: {connection_id: {user_id, connected_at, last_heartbeat}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}

        # Message queue for offline users: {user_id: [messages]}
        self.offline_messages: Dict[str, List[Dict[str, Any]]] = {}

        # Heartbeat tracking
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds

    async def connect(
        self, websocket: WebSocket, user_id: str, connection_id: str, token: str
    ) -> bool:
        """
        Authenticate and connect a WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: User ID from URL
            connection_id: Unique connection identifier
            token: JWT token for authentication

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Verify JWT token
            payload = verify_token(token, "access")
            if not payload or payload.get("sub") != user_id:
                logger.warning(f"Invalid token for user {user_id}")
                await websocket.close(code=4001, reason="Invalid authentication")
                return False

            # Accept WebSocket connection
            await websocket.accept()

            # Initialize user connections if not exists
            if user_id not in self.active_connections:
                self.active_connections[user_id] = {}

            # Store connection
            self.active_connections[user_id][connection_id] = websocket

            # Store connection metadata
            self.connection_metadata[connection_id] = {
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "last_heartbeat": datetime.utcnow(),
                "websocket": websocket,
            }

            # Join user to their personal room
            await self.join_room(f"user:{user_id}", user_id, connection_id)

            # Join user to role-based rooms if needed
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    await self.join_room(
                        f"role:{user.role.value}", user_id, connection_id
                    )
                    if user.company:
                        await self.join_room(
                            f"company:{user.company}", user_id, connection_id
                        )
            finally:
                db.close()

            # Send pending offline messages
            await self.send_offline_messages(user_id, connection_id)

            # Update user presence
            await self.update_user_presence(user_id, "online")

            logger.info(f"User {user_id} connected with connection {connection_id}")

            # Send connection success message
            await self.send_personal_message(
                user_id,
                {
                    "type": "connection:success",
                    "data": {
                        "connected_at": datetime.utcnow().isoformat(),
                        "connection_id": connection_id,
                    },
                },
            )

            return True

        except Exception as e:
            logger.error(f"Error connecting user {user_id}: {str(e)}")
            try:
                await websocket.close(code=4000, reason="Connection error")
            except:
                pass
            return False

    async def disconnect(self, user_id: str, connection_id: str):
        """
        Disconnect a WebSocket connection.

        Args:
            user_id: User ID
            connection_id: Connection identifier
        """
        try:
            # Remove from active connections
            if user_id in self.active_connections:
                self.active_connections[user_id].pop(connection_id, None)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]

            # Remove from all rooms
            for room_name in list(self.rooms.keys()):
                if user_id in self.rooms[room_name]:
                    self.rooms[room_name][user_id].discard(connection_id)
                    if not self.rooms[room_name][user_id]:
                        del self.rooms[room_name][user_id]
                    if not self.rooms[room_name]:
                        del self.rooms[room_name]

            # Remove connection metadata
            self.connection_metadata.pop(connection_id, None)

            # Update user presence if no more connections
            if user_id not in self.active_connections:
                await self.update_user_presence(user_id, "offline")

            logger.info(f"User {user_id} disconnected (connection {connection_id})")

        except Exception as e:
            logger.error(f"Error disconnecting user {user_id}: {str(e)}")

    async def join_room(self, room_name: str, user_id: str, connection_id: str):
        """Add a connection to a room."""
        if room_name not in self.rooms:
            self.rooms[room_name] = {}

        if user_id not in self.rooms[room_name]:
            self.rooms[room_name][user_id] = set()

        self.rooms[room_name][user_id].add(connection_id)
        logger.debug(f"User {user_id} joined room {room_name}")

    async def leave_room(self, room_name: str, user_id: str, connection_id: str):
        """Remove a connection from a room."""
        if room_name in self.rooms and user_id in self.rooms[room_name]:
            self.rooms[room_name][user_id].discard(connection_id)
            if not self.rooms[room_name][user_id]:
                del self.rooms[room_name][user_id]
            if not self.rooms[room_name]:
                del self.rooms[room_name]

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """
        Send message to all connections of a specific user.

        Args:
            user_id: Target user ID
            message: Message to send
        """
        if user_id not in self.active_connections:
            # Store message for offline delivery
            if user_id not in self.offline_messages:
                self.offline_messages[user_id] = []
            self.offline_messages[user_id].append(
                {**message, "queued_at": datetime.utcnow().isoformat()}
            )
            logger.debug(f"Message queued for offline user {user_id}")
            return

        # Send to all user connections
        disconnected_connections = []
        for connection_id, websocket in self.active_connections[user_id].items():
            try:
                await websocket.send_text(json.dumps(message))
            except WebSocketDisconnect:
                disconnected_connections.append(connection_id)
            except Exception as e:
                logger.error(f"Error sending message to {user_id}: {str(e)}")
                disconnected_connections.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            await self.disconnect(user_id, connection_id)

    async def send_room_message(
        self, room_name: str, message: Dict[str, Any], exclude_user: str = None
    ):
        """
        Send message to all users in a room.

        Args:
            room_name: Target room name
            message: Message to send
            exclude_user: User ID to exclude from broadcast
        """
        if room_name not in self.rooms:
            return

        for user_id in self.rooms[room_name]:
            if exclude_user and user_id == exclude_user:
                continue
            await self.send_personal_message(user_id, message)

    async def send_offline_messages(self, user_id: str, connection_id: str):
        """Send queued messages to newly connected user."""
        if user_id in self.offline_messages:
            messages = self.offline_messages[user_id]
            if messages:
                try:
                    websocket = self.active_connections[user_id][connection_id]
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "offline_messages",
                                "data": {"messages": messages, "count": len(messages)},
                            }
                        )
                    )
                    # Clear offline messages after successful delivery
                    del self.offline_messages[user_id]
                    logger.info(
                        f"Delivered {len(messages)} offline messages to user {user_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error sending offline messages to {user_id}: {str(e)}"
                    )

    async def update_user_presence(self, user_id: str, status: str):
        """
        Update user presence status.

        Args:
            user_id: User ID
            status: 'online', 'away', or 'offline'
        """
        # Store presence in database
        db = SessionLocal()
        try:
            # TODO: Update user presence in database
            # This will be implemented when we create the presence model
            pass
        finally:
            db.close()

        # Broadcast presence update to interested parties
        await self.send_room_message(
            "global",
            {
                "type": "user:presence",
                "data": {
                    "user_id": user_id,
                    "status": status,
                    "updated_at": datetime.utcnow().isoformat(),
                },
            },
            exclude_user=user_id,
        )

    async def handle_heartbeat(self, user_id: str, connection_id: str):
        """Handle heartbeat from client."""
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id][
                "last_heartbeat"
            ] = datetime.utcnow()

            # Send heartbeat response
            await self.send_personal_message(
                user_id,
                {
                    "type": "heartbeat:pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()},
                },
            )

    async def cleanup_stale_connections(self):
        """Remove stale connections that haven't sent heartbeat."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.heartbeat_timeout)
        stale_connections = []

        for connection_id, metadata in self.connection_metadata.items():
            if metadata["last_heartbeat"] < cutoff_time:
                stale_connections.append((metadata["user_id"], connection_id))

        for user_id, connection_id in stale_connections:
            logger.warning(
                f"Removing stale connection {connection_id} for user {user_id}"
            )
            await self.disconnect(user_id, connection_id)

    def get_connected_users(self) -> List[str]:
        """Get list of currently connected users."""
        return list(self.active_connections.keys())

    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of active connections for a user."""
        return len(self.active_connections.get(user_id, {}))

    def get_room_members(self, room_name: str) -> List[str]:
        """Get list of users in a room."""
        return list(self.rooms.get(room_name, {}).keys())

    async def broadcast_system_message(self, message: Dict[str, Any]):
        """Broadcast system message to all connected users."""
        for user_id in self.active_connections:
            await self.send_personal_message(
                user_id, {"type": "system:announcement", "data": message}
            )


# Global connection manager instance
connection_manager = ConnectionManager()


async def start_heartbeat_cleanup():
    """Background task to clean up stale connections."""
    while True:
        try:
            await connection_manager.cleanup_stale_connections()
            await asyncio.sleep(connection_manager.heartbeat_interval)
        except Exception as e:
            logger.error(f"Error in heartbeat cleanup: {str(e)}")
            await asyncio.sleep(5)
