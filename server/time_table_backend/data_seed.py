"""Idempotent MongoDB seed for timetable data.

The parsed JSON files have no natural primary key, so we derive a stable
`_id` from a hash of each document's content. On every run we upsert:
  - unchanged docs  -> replaced in place (effectively a no-op)
  - changed docs    -> updated
  - new docs        -> inserted
  - docs that vanished from the JSON -> deleted (keeps Mongo in sync)

Safe to run repeatedly (e.g. the `mongo-seed` service on every restart).
"""
import hashlib
import json
import os

from dotenv import load_dotenv
from pymongo import MongoClient, ReplaceOne

load_dotenv()

MONGO_DB = os.getenv("MONGO_DB")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")

client = MongoClient(f"mongodb://{MONGO_HOST}:{MONGO_PORT}")
db = client[MONGO_DB]


def _doc_id(doc: dict) -> str:
    """Deterministic id from the document's content (order-independent)."""
    canonical = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(canonical.encode("utf-8")).hexdigest()


def seed_collection(path: str) -> None:
    with open(path, "r") as f:
        data = json.load(f)

    collection_name = os.path.splitext(os.path.basename(path))[0]
    collection = db[collection_name]

    docs = data if isinstance(data, list) else [data]

    operations = []
    seen_ids = set()
    for doc in docs:
        doc = {k: v for k, v in doc.items() if k != "_id"}  # ignore stray _id
        doc_id = _doc_id(doc)
        seen_ids.add(doc_id)
        doc["_id"] = doc_id
        operations.append(ReplaceOne({"_id": doc_id}, doc, upsert=True))

    if operations:
        result = collection.bulk_write(operations, ordered=False)
        inserted = result.upserted_count
        updated = result.modified_count
        unchanged = len(operations) - inserted - updated
    else:
        inserted = updated = unchanged = 0

    # Prune docs that no longer exist in the source JSON
    deleted = collection.delete_many(
        {"_id": {"$nin": list(seen_ids)}}
    ).deleted_count if seen_ids else 0

    print(
        f"{collection_name}: inserted={inserted} updated={updated} "
        f"unchanged={unchanged} deleted={deleted} total={len(operations)}"
    )


if __name__ == "__main__":
    json_paths = [
        "/app/parsed_data/available_rooms_ranges.json",
        "/app/parsed_data/occupied_rooms.json",
        "/app/parsed_data/timetable_with_groups.json",
    ]
    for p in json_paths:
        if not os.path.exists(p):
            print(f"SKIP (missing): {p}")
            continue
        seed_collection(p)
    print("All data synced successfully!")
