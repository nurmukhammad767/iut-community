# import requests
# import json
# import os
# from itertools import groupby
# from operator import itemgetter

# def get_period_ranges(periods):
#     """Converts a list like [1, 2, 3, 5] into '1-3, 5'"""
#     ranges = []
#     periods = sorted([int(p) for p in periods])
#     for k, g in groupby(enumerate(periods), lambda x: x[0] - x[1]):
#         group = list(map(itemgetter(1), g))
#         if len(group) > 1:
#             ranges.append(f"{group[0]}-{group[-1]}")
#         else:
#             ranges.append(str(group[0]))
#     return ", ".join(ranges)

# def extract_free_rooms():
#     url = "https://iut.edupage.org/timetable/server/regulartt.js?__func=regularttGetData"
#     payload = {"__args": [None, "139"], "__gsh": "00000000"}
#     headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

#     try:
#         response = requests.post(url, json=payload, headers=headers)
#         response.raise_for_status()
#         data = response.json()
#         tables = data['r']['dbiAccessorRes']['tables']

#         def get_table_rows(tid):
#             return next((t for t in tables if t['id'] == tid), {'data_rows': []})['data_rows']

#         # 1. Load data
#         classrooms = get_table_rows('classrooms')
#         cards = get_table_rows('cards')
#         lessons = get_table_rows('lessons')
#         periods_table = get_table_rows('periods')

#         # 2. Map Lesson Durations
#         # durationperiods tells us how many consecutive slots a lesson takes
#         lesson_duration_map = {l['id']: int(l.get('durationperiods', 1)) for l in lessons}

#         # 3. Basic mappings
#         all_rooms_map = {r['id']: r['name'] for r in classrooms if r.get('name')}
#         all_room_ids = set(all_rooms_map.keys())
#         all_period_ids = sorted([int(p['id']) for p in periods_table if p.get('id')])

#         # 4. Build Occupancy Grid (Accounting for Duration)
#         occupancy_grid = {} # {day: {room_id: set(occupied_periods)}}
        
#         for card in cards:
#             day = card.get('days', '').strip()
#             if not day:
#                 continue
                
#             start_period = int(card.get('period'))
#             lesson_id = card.get('lessonid')
#             duration = lesson_duration_map.get(lesson_id, 1)
#             room_ids = card.get('classroomids', [])
            
#             if day not in occupancy_grid:
#                 occupancy_grid[day] = {}
            
#             for r_id in room_ids:
#                 if r_id not in occupancy_grid[day]:
#                     occupancy_grid[day][r_id] = set()
                
#                 # Mark all periods from start to (start + duration - 1) as occupied
#                 for i in range(duration):
#                     occupancy_grid[day][r_id].add(str(start_period + i))

#         # 5. Determine Free Ranges
#         free_rooms_by_day = []
#         unique_days = sorted(list(set(
#             card['days'].strip() for card in cards 
#             if card.get('days') and card['days'].strip() != ""
#         )))

#         for day in unique_days:
#             day_entry = {"day_mask": day, "rooms": []}
            
#             for r_id in sorted(all_room_ids):
#                 room_name = all_rooms_map[r_id]
#                 occupied_periods = occupancy_grid.get(day, {}).get(r_id, set())
                
#                 # Check each period against the occupancy grid
#                 free_periods = [p for p in all_period_ids if str(p) not in occupied_periods]
                
#                 if free_periods:
#                     day_entry["rooms"].append({
#                         "room_name": room_name,
#                         "available_periods": get_period_ranges(free_periods)
#                     })
            
#             if day_entry["rooms"]:
#                 free_rooms_by_day.append(day_entry)

#         # 6. Save output
#         output_dir = '/opt/airflow/parsed_data'
#         os.makedirs(output_dir, exist_ok=True)
#         output_path = os.path.join(output_dir, 'available_rooms_ranges.json')
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(free_rooms_by_day, f, ensure_ascii=False, indent=4)

#         print(f"Success. Accounted for lesson durations. Saved to {output_path}")

#     except Exception as e:
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     extract_free_rooms()

import requests
import json
import os
import hashlib
from itertools import groupby
from operator import itemgetter

def compute_hash(data: list) -> str:
    content = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def get_period_ranges(periods):
    """Converts a list like [1, 2, 3, 5] into '1-3, 5'"""
    ranges = []
    periods = sorted([int(p) for p in periods])
    for k, g in groupby(enumerate(periods), lambda x: x[0] - x[1]):
        group = list(map(itemgetter(1), g))
        if len(group) > 1:
            ranges.append(f"{group[0]}-{group[-1]}")
        else:
            ranges.append(str(group[0]))
    return ", ".join(ranges)

def extract_free_rooms():
    url = "https://iut.edupage.org/timetable/server/regulartt.js?__func=regularttGetData"
    payload = {"__args": [None, "139"], "__gsh": "00000000"}
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        tables = data['r']['dbiAccessorRes']['tables']

        def get_table_rows(tid):
            return next((t for t in tables if t['id'] == tid), {'data_rows': []})['data_rows']

        # 1. Load data
        classrooms = get_table_rows('classrooms')
        cards = get_table_rows('cards')
        lessons = get_table_rows('lessons')
        periods_table = get_table_rows('periods')

        # 2. Map Lesson Durations
        lesson_duration_map = {l['id']: int(l.get('durationperiods', 1)) for l in lessons}

        # 3. Basic mappings
        all_rooms_map = {r['id']: r['name'] for r in classrooms if r.get('name')}
        all_room_ids = set(all_rooms_map.keys())
        all_period_ids = sorted([int(p['id']) for p in periods_table if p.get('id')])

        # 4. Build Occupancy Grid (Accounting for Duration)
        occupancy_grid = {}

        for card in cards:
            day = card.get('days', '').strip()
            if not day:
                continue

            start_period = int(card.get('period'))
            lesson_id = card.get('lessonid')
            duration = lesson_duration_map.get(lesson_id, 1)
            room_ids = card.get('classroomids', [])

            if day not in occupancy_grid:
                occupancy_grid[day] = {}

            for r_id in room_ids:
                if r_id not in occupancy_grid[day]:
                    occupancy_grid[day][r_id] = set()
                for i in range(duration):
                    occupancy_grid[day][r_id].add(str(start_period + i))

        # 5. Determine Free Ranges
        free_rooms_by_day = []
        unique_days = sorted(list(set(
            card['days'].strip() for card in cards
            if card.get('days') and card['days'].strip() != ""
        )))

        for day in unique_days:
            day_entry = {"day_mask": day, "rooms": []}

            for r_id in sorted(all_room_ids):
                room_name = all_rooms_map[r_id]
                occupied_periods = occupancy_grid.get(day, {}).get(r_id, set())
                free_periods = [p for p in all_period_ids if str(p) not in occupied_periods]

                if free_periods:
                    day_entry["rooms"].append({
                        "room_name": room_name,
                        "available_periods": get_period_ranges(free_periods)
                    })

            if day_entry["rooms"]:
                free_rooms_by_day.append(day_entry)

        # 6. Check hash and save if changed
        output_dir = '/opt/airflow/parsed_data'
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'available_rooms_ranges.json')
        new_hash = compute_hash(free_rooms_by_day)

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_hash = compute_hash(json.load(f))
            if new_hash == existing_hash:
                print("AVAILABLE ROOMS: No changes detected — file remains the same.")
                return
            else:
                print("AVAILABLE ROOMS: Data has changed — updating file.")
        else:
            print("AVAILABLE ROOMS: No existing file found — creating new file.")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(free_rooms_by_day, f, ensure_ascii=False, indent=4)
        print(f"AVAILABLE ROOMS: Saved {len(free_rooms_by_day)} days to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    extract_free_rooms()