"""WebSocket chat for club members.

Path: WS /ws/chat/{club_id}?token=<jwt>

On connect:
  1. Decode JWT (token query param) -> student_id
  2. Verify student is a member of {club_id} (Postgres)
  3. Stream the most-recent 100 messages from Redis backlog
On message:
  1. Persist to Mongo collection `chat_messages`
  2. LPUSH to Redis list `chat:room:{club_id}` and trim to 100
  3. Broadcast to all sockets currently subscribed to the room
"""
import json
import os
from datetime import datetime
from typing import Dict, Set
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt as jose_jwt
from pymongo import MongoClient
import redis as redis_lib

from db_config import SessionLocal
from models import ClubMember, User


router = APIRouter(tags=["Chat (WebSocket)"])


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "iut")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

CHAT_BACKLOG_SIZE = 100


_mongo = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")[MONGO_DB]
_redis = redis_lib.from_url(REDIS_URL, decode_responses=True)


class ConnectionManager:
    """In-process pub/sub: club_id -> set of WebSocket connections.

    Note: this only works correctly with a single backend replica per room.
    Behind a load balancer with sticky sessions on club_id, each room lives on
    one replica. For a true cross-replica fanout, swap this for Redis pub/sub.
    """

    def __init__(self) -> None:
        self._rooms: Dict[str, Set[WebSocket]] = {}

    async def join(self, club_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self._rooms.setdefault(club_id, set()).add(ws)

    def leave(self, club_id: str, ws: WebSocket) -> None:
        room = self._rooms.get(club_id)
        if room:
            room.discard(ws)
            if not room:
                self._rooms.pop(club_id, None)

    async def broadcast(self, club_id: str, payload: dict) -> None:
        room = list(self._rooms.get(club_id, ()))
        for ws in room:
            try:
                await ws.send_json(payload)
            except Exception:
                self.leave(club_id, ws)


_manager = ConnectionManager()


def _decode_token(token: str) -> dict | None:
    try:
        return jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def _is_member(student_id: UUID, club_id: UUID) -> bool:
    db = SessionLocal()
    try:
        return (
            db.query(ClubMember)
            .filter(
                ClubMember.club_id == club_id,
                ClubMember.student_id == student_id,
            )
            .first()
            is not None
        )
    finally:
        db.close()


def _load_user(student_id: UUID) -> User | None:
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == student_id).first()
    finally:
        db.close()


def _backlog_key(club_id: str) -> str:
    return f"chat:room:{club_id}"


def _load_backlog(club_id: str) -> list[dict]:
    raw = _redis.lrange(_backlog_key(club_id), 0, CHAT_BACKLOG_SIZE - 1)
    # LPUSH means index 0 is newest; reverse so clients render oldest-first
    return [json.loads(item) for item in reversed(raw)]


def _persist(club_id: str, payload: dict) -> None:
    _mongo.chat_messages.insert_one({
        "club_id": club_id,
        "author_id": payload["author_id"],
        "author_name": payload["author_name"],
        "body": payload["body"],
        "created_at": payload["created_at"],
    })
    _redis.lpush(_backlog_key(club_id), json.dumps(payload))
    _redis.ltrim(_backlog_key(club_id), 0, CHAT_BACKLOG_SIZE - 1)


@router.websocket("/ws/chat/{club_id}")
async def chat_socket(
    websocket: WebSocket,
    club_id: str,
    token: str = Query(...),
):
    payload = _decode_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        student_id = UUID(payload["sub"])
        club_uuid = UUID(club_id)
    except (KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if not _is_member(student_id, club_uuid):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    user = _load_user(student_id)
    if not user:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await _manager.join(club_id, websocket)

    try:
        # Push backlog to the new connection
        backlog = _load_backlog(club_id)
        await websocket.send_json({"type": "backlog", "messages": backlog})

        while True:
            data = await websocket.receive_json()
            body = (data or {}).get("body", "").strip()
            if not body:
                continue
            if len(body) > 2000:
                body = body[:2000]

            event = {
                "type": "message",
                "club_id": club_id,
                "author_id": str(student_id),
                "author_name": user.full_name,
                "body": body,
                "created_at": datetime.utcnow().isoformat() + "Z",
            }
            _persist(club_id, event)
            await _manager.broadcast(club_id, event)
    except WebSocketDisconnect:
        pass
    finally:
        _manager.leave(club_id, websocket)
