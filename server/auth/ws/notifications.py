"""WebSocket live push of per-user notifications.

Path: WS /ws/notifications?token=<jwt>

On connect: subscribe to Redis pub/sub channel `notif:user:{student_id}`.
Celery beat (in the timetable service) publishes lesson reminders there
~15 minutes before each lesson; this socket forwards them to the client.

The Redis list `notif:list:{student_id}` is the durable queue read via the
REST GET /notifications endpoint when the user wasn't connected at fire time.
"""
import asyncio
import json
import os
from uuid import UUID

import redis.asyncio as redis_async
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status
from jose import JWTError, jwt as jose_jwt


router = APIRouter(tags=["Notifications (WebSocket)"])


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")


def _decode_token(token: str) -> dict | None:
    try:
        return jose_jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


@router.websocket("/ws/notifications")
async def notifications_socket(
    websocket: WebSocket,
    token: str = Query(...),
):
    payload = _decode_token(token)
    if not payload:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        student_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    client = redis_async.from_url(REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    channel = f"notif:user:{student_id}"
    await pubsub.subscribe(channel)

    async def relay() -> None:
        async for msg in pubsub.listen():
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            try:
                payload = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                payload = {"raw": data}
            await websocket.send_json(payload)

    relay_task = asyncio.create_task(relay())

    try:
        # Flush any queued notifications from the durable list on connect
        backlog = await client.lrange(f"notif:list:{student_id}", 0, -1)
        if backlog:
            decoded = []
            for entry in backlog:
                try:
                    decoded.append(json.loads(entry))
                except json.JSONDecodeError:
                    continue
            await websocket.send_json({
                "type": "backlog",
                "notifications": decoded,
            })

        while True:
            # Hold the socket open; ignore incoming frames (ack via REST)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        relay_task.cancel()
        try:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await client.close()
        except Exception:
            pass
