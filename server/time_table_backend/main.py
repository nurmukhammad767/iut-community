from fastapi import FastAPI, APIRouter, HTTPException
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(f"mongodb://{os.getenv('MONGO_HOST')}:{os.getenv('MONGO_PORT')}")
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

app.include_router(router)