import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import redis
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from pymongo import MongoClient

load_dotenv()

client = MongoClient(f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT', '27017')}")
db = client[os.getenv('MONGO_DB')]

_redis = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://redis:6379/1"),
    decode_responses=True,
)

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

DAY_MAP = {
    "1": "Monday",
    "2": "Tuesday",
    "3": "Wednesday",
    "4": "Thursday",
    "5": "Friday",
}

app = FastAPI(title="Timetable API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from telemetry import init_telemetry  # noqa: E402
init_telemetry(app)


@app.get("/healthz", tags=["Health"])
def healthz():
    return {"status": "ok"}


router = APIRouter(prefix="/timetable", tags=["Timetable"], dependencies=[Depends(get_current_user)])


@router.get("/group/{group_name}")
def get_sessions_by_group(group_name: str):
    sessions = list(
        db["timetable_with_groups"].find(
            {"groups": group_name},
            {"_id": 0}
        )
    )
    if not sessions:
        raise HTTPException(status_code=404, detail=f"No sessions found for group '{group_name}'")
    for s in sessions:
        s["days"] = [DAY_MAP[str(i + 1)] for i, bit in enumerate(s.pop("day_mask", "")) if bit == "1"]
    return {
        "group": group_name,
        "total_sessions": len(sessions),
        "sessions": sessions
    }


@router.get("/available_rooms")
def get_available_rooms(day: str, room_name: str = None, start_period: int = None, end_period: int = None):
    DAY_REVERSE = {v: k for k, v in DAY_MAP.items()}
    day_index = DAY_REVERSE.get(day)
    if not day_index:
        raise HTTPException(status_code=400, detail=f"Invalid day '{day}'. Valid options: {', '.join(DAY_MAP.values())}")

    if start_period and end_period and start_period > end_period:
        raise HTTPException(status_code=400, detail=f"start_period ({start_period}) must be less than end_period ({end_period})")

    all_docs = list(db["available_rooms_ranges"].find({}, {"_id": 0}))
    results = []

    for doc in all_docs:
        mask = doc.get("day_mask", "")
        if len(mask) >= int(day_index) and mask[int(day_index) - 1] == "1":
            for room in doc.get("rooms", []):
                if room_name and room_name.lower() not in room["room_name"].lower():
                    continue
                if start_period and end_period:
                    if not is_range_available(room["available_periods"], start_period, end_period):
                        continue
                results.append({
                    "room_name": room["room_name"],
                    "available_periods": room["available_periods"]
                })

    if not results:
        msg = f"No available rooms on {day}"
        if room_name:
            msg += f" for room '{room_name}'"
        if start_period and end_period:
            msg += f" during periods {start_period}-{end_period}"
        return {
            "day": day,
            "start_period": start_period,
            "end_period": end_period,
            "total_rooms": 0,
            "rooms": [],
            "message": msg
        }

    return {
        "day": day,
        "start_period": start_period,
        "end_period": end_period,
        "total_rooms": len(results),
        "rooms": results
    }


def is_range_available(available_periods: str, start: int, end: int) -> bool:
    available = set()
    for part in available_periods.split(","):
        part = part.strip()
        if "-" in part:
            s, e = map(int, part.split("-"))
            available.update(range(s, e + 1))
        else:
            available.add(int(part))
    return all(p in available for p in range(start, end + 1))


@router.get("/occupied_rooms")
def get_occupied_rooms(day: str, room_name: str = None, period: int = None):
    DAY_REVERSE = {v: k for k, v in DAY_MAP.items()}
    day_index = DAY_REVERSE.get(day)
    if not day_index:
        raise HTTPException(status_code=400, detail=f"Invalid day '{day}'. Valid options: {', '.join(DAY_MAP.values())}")

    all_docs = list(db["occupied_rooms"].find({}, {"_id": 0}))
    results = []

    for doc in all_docs:
        mask = doc.get("day_mask", "")
        if len(mask) >= int(day_index) and mask[int(day_index) - 1] == "1":
            if room_name and room_name.lower() not in doc.get("room_name", "").lower():
                continue
            if period and str(period) != str(doc.get("period")):
                continue
            results.append({
                "room_name": doc.get("room_name"),
                "period": doc.get("period"),
                "subject": doc.get("subject"),
                "professors": doc.get("professors", []),
                "groups": doc.get("groups", []),
            })

    if not results:
        msg = f"No occupied rooms on {day}"
        if room_name:
            msg += f" for room '{room_name}'"
        if period:
            msg += f" at period {period}"
        return {
            "day": day,
            "period": period,
            "total_rooms": 0,
            "rooms": [],
            "message": msg
        }

    return {
        "day": day,
        "period": period,
        "total_rooms": len(results),
        "rooms": results
    }


app.include_router(router)


# ---------------------------------------------------------------------------
# My timetable (group sessions minus dropped subjects) + drop/undrop
# ---------------------------------------------------------------------------

class DropRequest(BaseModel):
    day_mask: str = Field(min_length=5, max_length=5,
                          pattern=r"^[01]{5}$",
                          description="5-bit mask for Mon..Fri, e.g. '10100'")
    period: str = Field(min_length=1, max_length=2)
    subject: str = Field(min_length=1, max_length=200)


my_router = APIRouter(prefix="/timetable/my", tags=["My Timetable"])


def _composite_key(day_mask: str, period: str, subject: str) -> str:
    return f"{day_mask}|{period}|{subject}"


@my_router.get("/sessions")
def get_my_sessions(current_user: dict = Depends(get_current_user)):
    """Sessions for the caller's group, minus their dropped subjects."""
    group = current_user.get("group")
    student_id = current_user.get("sub")
    if not group:
        raise HTTPException(status_code=400, detail="Token missing group claim")

    sessions = list(
        db["timetable_with_groups"].find({"groups": group}, {"_id": 0})
    )
    dropped = {
        _composite_key(d["day_mask"], d["period"], d["subject"])
        for d in db["dropped_subjects"].find(
            {"student_id": student_id},
            {"_id": 0, "day_mask": 1, "period": 1, "subject": 1},
        )
    }

    visible = []
    for s in sessions:
        key = _composite_key(
            s.get("day_mask", ""), s.get("period", ""), s.get("subject", "")
        )
        if key in dropped:
            continue
        s["days"] = [
            DAY_MAP[str(i + 1)]
            for i, bit in enumerate(s.pop("day_mask", ""))
            if bit == "1"
        ]
        visible.append(s)

    return {
        "group": group,
        "total_sessions": len(visible),
        "dropped_count": len(dropped),
        "sessions": visible,
    }


@my_router.post("/drops", status_code=201)
def drop_subject(
    payload: DropRequest,
    current_user: dict = Depends(get_current_user),
):
    student_id = current_user.get("sub")
    group = current_user.get("group")

    # Validate session exists and includes the caller's group
    exists = db["timetable_with_groups"].find_one({
        "day_mask": payload.day_mask,
        "period": payload.period,
        "subject": payload.subject,
        "groups": group,
    })
    if not exists:
        raise HTTPException(
            status_code=404,
            detail="Session not found for your group",
        )

    doc = {
        "_id": f"{student_id}|{_composite_key(payload.day_mask, payload.period, payload.subject)}",
        "student_id": student_id,
        "student_identifier": current_user.get("student_id"),
        "full_name": current_user.get("full_name"),
        "group": group,
        "role": current_user.get("role"),
        "day_mask": payload.day_mask,
        "period": payload.period,
        "subject": payload.subject,
        "dropped_at": datetime.now(tz=timezone.utc),
    }
    try:
        db["dropped_subjects"].insert_one(doc)
    except Exception:
        # Duplicate _id => already dropped; treat as idempotent
        existing = db["dropped_subjects"].find_one({"_id": doc["_id"]}, {"_id": 0})
        if existing:
            return {"message": "Already dropped", "drop": existing}
        raise
    doc.pop("_id", None)
    return {"message": "Subject dropped", "drop": doc}


@my_router.get("/drops")
def list_my_drops(current_user: dict = Depends(get_current_user)):
    student_id = current_user.get("sub")
    rows = list(
        db["dropped_subjects"].find(
            {"student_id": student_id},
            {"_id": 0},
        )
    )
    return {"total": len(rows), "drops": rows}


@my_router.delete("/drops", status_code=204)
def undrop_subject(
    payload: DropRequest,
    current_user: dict = Depends(get_current_user),
):
    student_id = current_user.get("sub")
    res = db["dropped_subjects"].delete_one({
        "_id": f"{student_id}|{_composite_key(payload.day_mask, payload.period, payload.subject)}"
    })
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Drop not found")


app.include_router(my_router)


# ---------------------------------------------------------------------------
# Notifications (Redis-backed; populated by Celery reminders)
# ---------------------------------------------------------------------------

notif_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@notif_router.get("")
def list_notifications(current_user: dict = Depends(get_current_user)):
    student_id = current_user.get("sub")
    raw = _redis.lrange(f"notif:list:{student_id}", 0, -1)
    items = []
    for entry in raw:
        try:
            items.append(json.loads(entry))
        except json.JSONDecodeError:
            continue
    return {"total": len(items), "notifications": items}


@notif_router.post("/ack/{notification_id}", status_code=204)
def ack_notification(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove one notification by id from the user's queue."""
    student_id = current_user.get("sub")
    key = f"notif:list:{student_id}"
    raw = _redis.lrange(key, 0, -1)
    for entry in raw:
        try:
            doc = json.loads(entry)
        except json.JSONDecodeError:
            continue
        if doc.get("id") == notification_id:
            _redis.lrem(key, 1, entry)
            return
    raise HTTPException(status_code=404, detail="Notification not found")


@notif_router.delete("", status_code=204)
def clear_notifications(current_user: dict = Depends(get_current_user)):
    student_id = current_user.get("sub")
    _redis.delete(f"notif:list:{student_id}")


app.include_router(notif_router)