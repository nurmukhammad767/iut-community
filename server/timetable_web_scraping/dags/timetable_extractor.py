# import requests
# import json
# import os

# def fetch_complete_timetable():
#     url = "https://iut.edupage.org/timetable/server/regulartt.js?__func=regularttGetData"
#     payload = {"__args": [None, "139"], "__gsh": "00000000"}
#     headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

#     try:
#         response = requests.post(url, json=payload, headers=headers)
#         response.raise_for_status()
#         raw_data = response.json()
#         tables = raw_data['r']['dbiAccessorRes']['tables']

#         def find_table(tid):
#             return next((t for t in tables if t['id'] == tid), {'data_rows': []})

#         # 1. Extract Primary Tables
#         subjects_data = find_table('subjects')['data_rows']
#         teachers_data = find_table('teachers')['data_rows']
#         classrooms_data = find_table('classrooms')['data_rows']
#         classes_data = find_table('classes')['data_rows']
#         lessons_data = find_table('lessons')['data_rows']
#         cards_data = find_table('cards')['data_rows']

#         # 2. Create Lookup Maps
#         subject_map = {s['id']: s['name'] for s in subjects_data}
#         teacher_map = {t['id']: t['name'] for t in teachers_data}
#         room_map = {r['id']: r['name'] for r in classrooms_data}
#         class_map = {c['id']: c['name'] for c in classes_data}

#         # 3. Process Lessons
#         lesson_lookup = {}
#         for lesson in lessons_data:
#             l_id = lesson['id']
#             c_ids = lesson.get('classids', [])
#             group_names = [class_map.get(cid, cid) for cid in c_ids]
#             lesson_lookup[l_id] = {
#                 "subject": subject_map.get(lesson.get('subjectid'), "Unknown"),
#                 "professors": [teacher_map.get(tid, tid) for tid in lesson.get('teacherids', [])],
#                 "groups": group_names
#             }

#         # 4. Build Final Timetable with Validation
#         full_timetable = []
#         for card in cards_data:
#             # Extract and clean Day and Period
#             day = card.get('days', '').strip()
#             period = card.get('period', '').strip()

#             # --- FIX: Skip cards that have empty day_mask or period ---
#             if not day or not period:
#                 continue

#             l_info = lesson_lookup.get(card['lessonid'], {"subject": "N/A", "professors": [], "groups": []})
            
#             # Resolve room names
#             rooms = [room_map.get(rid, rid) for rid in card.get('classroomids', [])]
            
#             full_timetable.append({
#                 "day_mask": day,
#                 "period": period,
#                 "subject": l_info['subject'],
#                 "professors": l_info['professors'],
#                 "groups": l_info['groups'],
#                 "rooms": rooms
#             })

#         # 5. Save to persist on your local machine
#         output_dir = '/opt/airflow/parsed_data'
#         os.makedirs(output_dir, exist_ok=True)
#         output_path = os.path.join(output_dir, 'timetable_with_groups.json')
#         with open(output_path, 'w', encoding='utf-8') as f:
#             json.dump(full_timetable, f, ensure_ascii=False, indent=4)

#         print(f"Data cleaned and extracted successfully to {output_path}")

#     except Exception as e:
#         print(f"Error: {e}")

# if __name__ == "__main__":
#     fetch_complete_timetable()



import requests
import json
import os
import hashlib

def compute_hash(data: list) -> str:
    content = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode('utf-8')).hexdigest()

def fetch_complete_timetable():
    url = "https://iut.edupage.org/timetable/server/regulartt.js?__func=regularttGetData"
    payload = {"__args": [None, "139"], "__gsh": "00000000"}
    headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        raw_data = response.json()
        tables = raw_data['r']['dbiAccessorRes']['tables']

        def find_table(tid):
            return next((t for t in tables if t['id'] == tid), {'data_rows': []})

        # 1. Extract Primary Tables
        subjects_data = find_table('subjects')['data_rows']
        teachers_data = find_table('teachers')['data_rows']
        classrooms_data = find_table('classrooms')['data_rows']
        classes_data = find_table('classes')['data_rows']
        lessons_data = find_table('lessons')['data_rows']
        cards_data = find_table('cards')['data_rows']

        # 2. Create Lookup Maps
        subject_map = {s['id']: s['name'] for s in subjects_data}
        teacher_map = {t['id']: t['name'] for t in teachers_data}
        room_map = {r['id']: r['name'] for r in classrooms_data}
        class_map = {c['id']: c['name'] for c in classes_data}

        # 3. Process Lessons
        lesson_lookup = {}
        for lesson in lessons_data:
            l_id = lesson['id']
            c_ids = lesson.get('classids', [])
            group_names = [class_map.get(cid, cid) for cid in c_ids]
            lesson_lookup[l_id] = {
                "subject": subject_map.get(lesson.get('subjectid'), "Unknown"),
                "professors": [teacher_map.get(tid, tid) for tid in lesson.get('teacherids', [])],
                "groups": group_names
            }

        # 4. Build Final Timetable
        full_timetable = []
        for card in cards_data:
            day = card.get('days', '').strip()
            period = card.get('period', '').strip()
            if not day or not period:
                continue
            l_info = lesson_lookup.get(card['lessonid'], {"subject": "N/A", "professors": [], "groups": []})
            rooms = [room_map.get(rid, rid) for rid in card.get('classroomids', [])]
            full_timetable.append({
                "day_mask": day,
                "period": period,
                "subject": l_info['subject'],
                "professors": l_info['professors'],
                "groups": l_info['groups'],
                "rooms": rooms
            })

        # 5. Check hash and save if changed
        output_dir = '/opt/airflow/parsed_data'
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'timetable_with_groups.json')
        new_hash = compute_hash(full_timetable)

        if os.path.exists(output_path):
            with open(output_path, 'r', encoding='utf-8') as f:
                existing_hash = compute_hash(json.load(f))
            if new_hash == existing_hash:
                print("TIMETABLE: No changes detected — file remains the same.")
                return
            else:
                print("TIMETABLE: Data has changed — updating file.")
        else:
            print("TIMETABLE: No existing file found — creating new file.")

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(full_timetable, f, ensure_ascii=False, indent=4)
        print(f"TIMETABLE: Saved {len(full_timetable)} records to {output_path}")

    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    fetch_complete_timetable()