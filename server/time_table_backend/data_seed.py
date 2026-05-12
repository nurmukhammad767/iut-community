import os
from dotenv import load_dotenv
from pymongo import MongoClient
import json

load_dotenv()

MONGO_DB = os.getenv("MONGO_DB")
MONGO_HOST = os.getenv("MONGO_HOST")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")

client = MongoClient(f'mongodb://{MONGO_HOST}:{MONGO_PORT}')
db = client[MONGO_DB]

def insert(file_paths):
    for path in file_paths:
        with open(path, 'r') as f:
            data = json.load(f)
        collection_name = os.path.splitext(os.path.basename(path))[0]
        if isinstance(data, list):
            db[collection_name].insert_many(data)
        else:
            db[collection_name].insert_one(data)
        print(f"Inserted: {collection_name}")

if __name__ == '__main__':
    json_path = [
        '/app/parsed_data/available_rooms_ranges.json',
        '/app/parsed_data/occupied_rooms.json',
        '/app/parsed_data/timetable_with_groups.json'
        # '/home/nurmukhammad/projects/iut-community/server/timetable_web_scraping/parsed_data/available_rooms_ranges.json',
        # '/home/nurmukhammad/projects/iut-community/server/timetable_web_scraping/parsed_data/occupied_rooms.json',
        # '/home/nurmukhammad/projects/iut-community/server/timetable_web_scraping/parsed_data/timetable_with_groups.json'
    ]
    insert(json_path)
    print("All data inserted successfully!")