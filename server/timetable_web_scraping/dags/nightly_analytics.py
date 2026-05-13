"""Nightly analytics DAG (R10).

Workflow:
  1. aggregate_room_usage   — reads Mongo `occupied_rooms` and writes
                              Postgres `room_usage_daily` (one row per
                              (day, room_name) snapshot).
  2. expire_assignments     — flips `assignments.status` to 'expired'
                              for every row where due_date < now().
  3. clear_stale_bookings   — flips `room_bookings.status` to 'expired'
                              for every active booking older than 7 days.

These tasks run sequentially; the dependency arrow is what we render as a
BPMN diagram for the report (R2 deliverable).
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from pymongo import MongoClient
from sqlalchemy import create_engine, text


PG_URL = (
    f"postgresql://{os.getenv('DB_USER','postgres')}:{os.getenv('DB_PASSWORD','postgres')}"
    f"@{os.getenv('DB_HOST','backend-postgres')}:{os.getenv('DB_PORT','5432')}"
    f"/{os.getenv('DB_NAME','iut')}"
)
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_DB = os.getenv("MONGO_DB", "iut")


DAY_MAP = {"1": "Monday", "2": "Tuesday", "3": "Wednesday",
           "4": "Thursday", "5": "Friday"}


def aggregate_room_usage() -> None:
    mongo = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")[MONGO_DB]
    engine = create_engine(PG_URL)

    # group occupied_rooms by (day, room_name)
    pipeline = [
        {"$project": {"_id": 0, "room_name": 1, "day_mask": 1, "period": 1}},
    ]
    occupied_counts: dict[tuple[str, str], int] = {}
    for doc in mongo.occupied_rooms.aggregate(pipeline):
        mask = doc.get("day_mask", "")
        room = doc.get("room_name")
        if not room:
            continue
        for idx, bit in enumerate(mask):
            if bit == "1":
                day = DAY_MAP.get(str(idx + 1))
                if day:
                    key = (day, room)
                    occupied_counts[key] = occupied_counts.get(key, 0) + 1

    PERIODS_PER_DAY = 10
    now = datetime.utcnow()
    with engine.begin() as conn:
        for (day, room), occ in occupied_counts.items():
            free = max(0, PERIODS_PER_DAY - occ)
            conn.execute(
                text("""
                    INSERT INTO room_usage_daily
                        (id, day, room_name, occupied_periods, free_periods, computed_at)
                    VALUES (gen_random_uuid(), :day, :room, :occ, :free, :ts)
                    ON CONFLICT (day, room_name, computed_at) DO NOTHING
                """),
                {"day": day, "room": room, "occ": occ, "free": free, "ts": now},
            )
    print(f"aggregate_room_usage: wrote {len(occupied_counts)} rows")


def expire_assignments() -> None:
    engine = create_engine(PG_URL)
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE assignments
                SET status = 'expired'
                WHERE status = 'active' AND due_date < now()
            """)
        )
        print(f"expire_assignments: flipped {result.rowcount} assignments")


def clear_stale_bookings() -> None:
    engine = create_engine(PG_URL)
    cutoff = datetime.utcnow() - timedelta(days=7)
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                UPDATE room_bookings
                SET status = 'expired'
                WHERE status = 'active' AND booked_at < :cutoff
            """),
            {"cutoff": cutoff},
        )
        print(f"clear_stale_bookings: flipped {result.rowcount} bookings")


default_args = {
    "owner": "iut-community",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="nightly_analytics",
    default_args=default_args,
    start_date=datetime(2026, 5, 1),
    schedule="@daily",
    catchup=False,
    tags=["analytics", "iut-community"],
) as dag:
    t_aggregate = PythonOperator(
        task_id="aggregate_room_usage",
        python_callable=aggregate_room_usage,
    )
    t_expire = PythonOperator(
        task_id="expire_assignments",
        python_callable=expire_assignments,
    )
    t_clear = PythonOperator(
        task_id="clear_stale_bookings",
        python_callable=clear_stale_bookings,
    )

    t_aggregate >> t_expire >> t_clear
