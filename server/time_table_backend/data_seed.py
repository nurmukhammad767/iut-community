from fastapi import FastAPI, APIRouter, HTTPException
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT', '27017')}")
db = client[os.getenv('MONGO_DB')]

app = FastAPI(title="Timetable API")
router = APIRouter(prefix="/timetable", tags=["Timetable"])

DAY_MAP = {
    "1": "Monday",
    "2": "Tuesday",
    "3": "Wednesday",
    "4": "Thursday",
    "5": "Friday",
}

PERIOD_MAP = {
    "1":  "8:30 - 10:00",
    "2":  "10:00 - 10:30",
    "3":  "10:30 - 11:00",
    "4":  "11:00 - 11:30",
    "5":  "11:30 - 12:00",
    "6":  "12:00 - 12:30",
    "7":  "12:30 - 13:00",
    "8":  "13:00 - 13:30",
    "9":  "13:30 - 14:00",
    "10": "14:00 - 14:30",
    "11": "14:30 - 15:00",
    "12": "15:00 - 15:30",
    "13": "15:30 - 16:00",
    "14": "16:00 - 16:30",
    "15": "16:30 - 17:00",
    "16": "17:00 - 17:30",
    "17": "17:30 - 18:00",
    "18": "18:00 - 18:30",
    "19": "18:30 - 19:00",
    "20": "19:00 - 19:30",
}

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
        s["period_time"] = PERIOD_MAP.get(str(s.get("period")), "Unknown")

    return {
        "group": group_name,
        "total_sessions": len(sessions),
        "sessions": sessions
    }

app.include_router(router)