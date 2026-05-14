"""Celery tasks for the timetable service.

scan_upcoming_lessons runs every minute (driven by Celery beat).
For every session in MongoDB starting in the 15-minute reminder window,
it enqueues a notification for each student in that session's group
(excluding students who dropped that subject), pushes the notification
to a Redis list `notif:list:{student_id}` (REST polling) and PUBLISHes
on channel `notif:user:{student_id}` (WebSocket live push).
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List

import redis
from pymongo import MongoClient
from sqlalchemy import create_engine, text

from celery_app import celery_app
from period_times import TZ, lesson_today_at, session_runs_on


log = logging.getLogger(__name__)


# ---- Connections (lazy module-level — workers reuse) ---------------------

_REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")
_MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
_MONGO_PORT = os.getenv("MONGO_PORT", "27017")
_MONGO_DB = os.getenv("MONGO_DB")
_PG_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'backend-postgres')}:{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME')}",
)

# A lesson is "upcoming" if it starts within this window and hasn't started
# yet. We notify on the FIRST scan where the lesson falls inside the window;
# the per-student dedup key (SET NX) guarantees exactly one reminder even
# though the lesson stays inside the window for ~15 scans. This is resilient
# to missed beat ticks / worker restarts (a fixed-instant band is not).
_REMINDER_WINDOW = timedelta(minutes=15)

_mongo = MongoClient(f"mongodb://{_MONGO_HOST}:{_MONGO_PORT}")
_mongo_db = _mongo[_MONGO_DB] if _MONGO_DB else None
_redis = redis.Redis.from_url(_REDIS_URL, decode_responses=True)
_pg = create_engine(_PG_URL, pool_pre_ping=True)


def _session_key(day_mask: str, period: str, subject: str) -> str:
    return f"{day_mask}|{period}|{subject}"


def _students_in_groups(groups: List[str]) -> list[dict]:
    """Look up student id + identifier for everyone in any of these groups."""
    if not groups:
        return []
    with _pg.connect() as conn:
        rows = conn.execute(
            text(
                'SELECT id, student_identifier, full_name '
                'FROM users WHERE "group" = ANY(:groups) AND role = :role'
            ),
            {"groups": groups, "role": "student"},
        ).fetchall()
    return [
        {"id": str(r[0]), "student_identifier": r[1], "full_name": r[2]}
        for r in rows
    ]


def _dropped_keys_by_student(student_ids: list[str]) -> dict[str, set]:
    """Returns {student_id: {session_key, ...}} for the given students."""
    if not student_ids or _mongo_db is None:
        return {}
    cursor = _mongo_db["dropped_subjects"].find(
        {"student_id": {"$in": student_ids}},
        {"_id": 0, "student_id": 1, "day_mask": 1, "period": 1, "subject": 1},
    )
    out: dict[str, set] = {}
    for doc in cursor:
        key = _session_key(doc["day_mask"], doc["period"], doc["subject"])
        out.setdefault(doc["student_id"], set()).add(key)
    return out


def _emit_notification(student_id: str, payload: dict) -> None:
    """Persist to Redis list + publish on pubsub channel."""
    serialized = json.dumps(payload, default=str)
    pipe = _redis.pipeline()
    list_key = f"notif:list:{student_id}"
    pipe.lpush(list_key, serialized)
    pipe.ltrim(list_key, 0, 49)  # keep last 50
    pipe.expire(list_key, 60 * 60 * 24)  # 24h
    pipe.publish(f"notif:user:{student_id}", serialized)
    pipe.execute()


@celery_app.task(name="tasks.scan_upcoming_lessons")
def scan_upcoming_lessons() -> dict:
    """Find sessions starting in ~15 minutes and notify enrolled students."""
    if _mongo_db is None:
        log.warning("MONGO_DB env var missing; skipping reminder scan")
        return {"scanned": 0, "notified": 0}

    now = datetime.now(tz=TZ)
    weekday = now.weekday()  # Mon=0..Sun=6
    if weekday > 4:
        return {"scanned": 0, "notified": 0, "reason": "weekend"}

    sessions = list(_mongo_db["timetable_with_groups"].find({}, {"_id": 0}))
    scanned = 0
    notified = 0

    for s in sessions:
        if not session_runs_on(s.get("day_mask", ""), weekday):
            continue
        start_dt = lesson_today_at(s.get("period", ""), now)
        if start_dt is None:
            continue
        delta = start_dt - now
        # upcoming = starts within the window and hasn't started yet
        if not (timedelta(0) < delta <= _REMINDER_WINDOW):
            continue
        minutes_until = max(1, int(delta.total_seconds() // 60))

        scanned += 1
        groups = s.get("groups", [])
        students = _students_in_groups(groups)
        if not students:
            continue

        dropped = _dropped_keys_by_student([st["id"] for st in students])
        skey = _session_key(s["day_mask"], s.get("period", ""), s.get("subject", ""))

        # idempotency: include the lesson date + period in the dedup key
        dedup_marker = (
            f"notif:sent:{start_dt.date().isoformat()}:{s.get('period')}:"
            f"{s.get('subject')}"
        )

        for st in students:
            if skey in dropped.get(st["id"], set()):
                continue
            student_marker = f"{dedup_marker}:{st['id']}"
            # SET NX EX prevents duplicate notification for same lesson
            if not _redis.set(student_marker, "1", nx=True, ex=60 * 30):
                continue
            payload = {
                "id": str(uuid.uuid4()),
                "type": "lesson_reminder",
                "subject": s.get("subject"),
                "period": s.get("period"),
                "start_time": start_dt.isoformat(),
                "rooms": s.get("rooms", []),
                "professors": s.get("professors", []),
                "minutes_until": minutes_until,
                "created_at": now.isoformat(),
            }
            _emit_notification(st["id"], payload)
            notified += 1

    log.info("scan_upcoming_lessons scanned=%s notified=%s", scanned, notified)
    return {"scanned": scanned, "notified": notified}
