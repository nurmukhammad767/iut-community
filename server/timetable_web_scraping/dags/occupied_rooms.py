# import requests
# import json
# import os

# def extract_occupied_rooms():
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

#         # 1. Load data tables
#         classrooms = get_table_rows('classrooms')
#         teachers = get_table_rows('teachers')
#         subjects = get_table_rows('subjects')
#         classes = get_table_rows('classes')
#         lessons = get_table_rows('lessons')
#         cards = get_table_rows('cards')

#         # 2. Create Lookup Maps
#         room_map = {r['id']: r['name'] for r in classrooms if r.get('name')}
#         teacher_map = {t['id']: t['name'] for t in teachers}
#         subject_map = {s['id']: s['name'] for s in subjects}
#         class_map = {c['id']: c['name'] for c in classes}

#         # 3. Process Lessons (The connection between Subject, Teacher, and Group)
#         lesson_lookup = {}
#         for lesson in lessons:
#             l_id = lesson['id']
#             lesson_lookup[l_id] = {
#                 "subject": subject_map.get(lesson.get('subjectid'), "Unknown"),
#                 "professors": [teacher_map.get(tid, tid) for tid in lesson.get('teacherids', [])],
#                 "groups": [class_map.get(cid, cid) for cid in lesson.get('classids', [])]
#             }

#         # 4. Extract Occupied Slots from Cards
#         occupied_data = []
#         for card in cards:
#             day = card.get('days', '').strip()
#             period = card.get('period')
            
#             # Filter: Skip cards with missing day or period information
#             if not day or not period:
#                 continue
            
#             lesson_info = lesson_lookup.get(card['lessonid'], {})
#             room_ids = card.get('classroomids', [])
            
#             for r_id in room_ids:
#                 if r_id in room_map:
#                     occupied_data.append({
#                         "day_mask": day,
#                         "period": period,
#                         "room_name": room_map[r_id],
#                         "subject": lesson_info.get("subject"),
#                         "professors": lesson_info.get("professors"),
#                         "groups": lesson_info.get("groups")
#                     })

#         # 5. Sort by Day and Period for better readability
#         occupied_data.sort(key=lambda x: (x['day_mask'], int(x['period'])))

#         # 6. Save to JSON
#         output_dir = '/opt/airflow/parsed_data'
#         os.makedirs(output_dir, exist_ok=True)
#         output_path = os.path.join(output_dir, 'occupied_rooms.json')
        
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(occupied_data, f, ensure_ascii=False, indent=4)

#         print(f"Occupied rooms extracted. {len(occupied_data)} entries saved to {output_path}")

#     except Exception as e:
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     extract_occupied_rooms()

import requests
import json
import os
import hashlib

def compute_hash(data: list) -> str:
    content = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def extract_occupied_rooms():
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

        # 1. Load data tables
        classrooms = get_table_rows('classrooms')
        teachers = get_table_rows('teachers')
        subjects = get_table_rows('subjects')
        classes = get_table_rows('classes')
        lessons = get_table_rows('lessons')
        cards = get_table_rows('cards')

        # 2. Create Lookup Maps
        room_map = {r['id']: r['name'] for r in classrooms if r.get('name')}
        teacher_map = {t['id']: t['name'] for t in teachers}
        subject_map = {s['id']: s['name'] for s in subjects}
        class_map = {c['id']: c['name'] for c in classes}

        # 3. Process Lessons
        lesson_lookup = {}
        for lesson in lessons:
            l_id = lesson['id']
            lesson_lookup[l_id] = {
                "subject": subject_map.get(lesson.get('subjectid'), "Unknown"),
                "professors": [teacher_map.get(tid, tid) for tid in lesson.get('teacherids', [])],
                "groups": [class_map.get(cid, cid) for cid in lesson.get('classids', [])]
            }

        # 4. Extract Occupied Slots from Cards
        occupied_data = []
        for card in cards:
            day = card.get('days', '').strip()
            period = card.get('period')
            if not day or not period:
                continue

            lesson_info = lesson_lookup.get(card['lessonid'], {})
            room_ids = card.get('classroomids', [])

            for r_id in room_ids:
                if r_id in room_map:
                    occupied_data.append({
                        "day_mask": day,
                        "period": period,
                        "room_name": room_map[r_id],
                        "subject": lesson_info.get("subject"),
                        "professors": lesson_info.get("professors"),
                        "groups": lesson_info.get("groups")
                    })

        # 5. Sort by Day and Period
        occupied_data.sort(key=lambda x: (x['day_mask'], int(x['period'])))

        # 6. Check hash and save if changed
        output_dir = '/opt/airflow/parsed_data'
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'occupied_rooms.json')
        new_hash = compute_hash(occupied_data)

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_hash = compute_hash(json.load(f))
            if new_hash == existing_hash:
                print("OCCUPIED ROOMS: No changes detected — file remains the same.")
                return
            else:
                print("OCCUPIED ROOMS: Data has changed — updating file.")
        else:
            print("OCCUPIED ROOMS: No existing file found — creating new file.")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(occupied_data, f, ensure_ascii=False, indent=4)
        print(f"OCCUPIED ROOMS: Saved {len(occupied_data)} entries to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    extract_occupied_rooms()