from fastapi import FastAPI, APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pymongo import MongoClient
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT', '27017')}")
db = client[os.getenv('MONGO_DB')]

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