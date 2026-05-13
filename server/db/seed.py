"""Idempotent seed data for development & demo.

Run after `alembic upgrade head`. Safe to re-run: every insert is guarded by
an existence check on a natural key.

Invoked from server/entrypoint.sh after migrations complete.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from db_config import SessionLocal
from models import (
    User, UserRole, Course, CourseEnrollment, Assignment,
    Club, ClubMember, ClubPost,
)


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


DEMO_PASSWORD = "Password123!"


DEMO_USERS = [
    # (student_id, full_name, group, role)
    ("U22107001", "Alice Karimova", "SOC-22-A", UserRole.student),
    ("U22107002", "Bobur Tursunov", "SOC-22-A", UserRole.student),
    ("U22107003", "Charos Yusupova", "SOC-22-A", UserRole.student),
    ("U22107004", "Davron Saidov", "SOC-22-B", UserRole.student),
    ("U22107005", "Elnura Akhmedova", "SOC-22-B", UserRole.student),
    ("U22107006", "Farrukh Nazarov", "SOC-22-B", UserRole.student),
    ("U22107007", "Gulnoza Rakhimova", "ICE-22-A", UserRole.student),
    ("U22107008", "Hasan Mirzayev", "ICE-22-A", UserRole.student),
    ("U22107009", "Iroda Sodiqova", "ICE-22-A", UserRole.student),
    ("U22107010", "Jasur Kamalov", "ICE-22-B", UserRole.student),
    ("U22107011", "Kamila Yuldasheva", "ICE-22-B", UserRole.student),
    ("U22107012", "Laziz Tashpulatov", "ICE-22-B", UserRole.student),
    ("U22107013", "Madina Salimova", "BBA-22-A", UserRole.student),
    ("U22107014", "Nodir Khasanov", "BBA-22-A", UserRole.student),
    ("U22107015", "Otabek Rashidov", "BBA-22-A", UserRole.student),
    ("U22107016", "Parvina Tursunbaeva", "BBA-22-B", UserRole.student),
    ("U22107017", "Qodir Ergashev", "BBA-22-B", UserRole.student),
    ("PROF001", "Dr. Sarvar Abdullaev", "FACULTY", UserRole.professor),
    ("PROF002", "Dr. Aziza Karimova", "FACULTY", UserRole.professor),
    ("ADMIN001", "System Administrator", "STAFF", UserRole.admin),
]


DEMO_COURSES = [
    ("CS301", "Database Application and Design"),
    ("CS302", "Operating Systems"),
    ("CS303", "Computer Networks"),
    ("CS304", "Software Engineering"),
    ("CS305", "Web Programming"),
]


DEMO_CLUBS = [
    ("Coding Club", "Weekly competitive programming and project hacking sessions."),
    ("Photography Society", "Campus photo walks, gear talks, monthly themed contests."),
    ("Debate Club", "Inha Tashkent's home for MUN, BP, and AP debate formats."),
]


DEMO_POSTS = [
    ("Coding Club", "Welcome to the Coding Club! First meeting Friday 5pm in A605."),
    ("Coding Club", "Codeforces Round #900 watch party tonight in the lounge."),
    ("Coding Club", "Anyone has notes from the DDIA chapter 5 reading group?"),
    ("Photography Society", "Sunset photo walk this Saturday — meet at the main gate 6pm."),
    ("Photography Society", "October theme announced: 'Geometry in Architecture'."),
    ("Photography Society", "Looking for a 50mm prime to borrow for the weekend, anyone?"),
    ("Debate Club", "MUN selections opening next Monday — sign up via the form."),
    ("Debate Club", "Practice round Thursday 7pm, motion: THBT social media has..."),
    ("Debate Club", "Welcome new members! Onboarding doc in the pinned message."),
    ("Coding Club", "Reminder: Database project deadline is May 17."),
]


def seed_users(db: Session) -> dict:
    existing = {u.student_identifier: u for u in db.query(User).all()}
    created = {}
    for student_id, full_name, group, role in DEMO_USERS:
        if student_id in existing:
            created[student_id] = existing[student_id]
            continue
        user = User(
            student_identifier=student_id,
            password_hash=pwd_context.hash(DEMO_PASSWORD),
            full_name=full_name,
            group=group,
            role=role,
        )
        db.add(user)
        db.flush()
        created[student_id] = user
    db.commit()
    return created


def seed_courses(db: Session) -> dict:
    existing = {c.code: c for c in db.query(Course).all()}
    created = {}
    for code, name in DEMO_COURSES:
        if code in existing:
            created[code] = existing[code]
            continue
        course = Course(code=code, name=name)
        db.add(course)
        db.flush()
        created[code] = course
    db.commit()
    return created


def seed_enrollments(db: Session, users: dict, courses: dict) -> None:
    student_ids = [u.id for sid, u in users.items() if not sid.startswith(("PROF", "ADMIN"))]
    course_ids = [c.id for c in courses.values()]
    existing_pairs = {
        (e.student_id, e.course_id)
        for e in db.query(CourseEnrollment).all()
    }
    for sid in student_ids:
        for cid in course_ids[:3]:  # enroll each student in first 3 courses
            if (sid, cid) in existing_pairs:
                continue
            db.add(CourseEnrollment(student_id=sid, course_id=cid))
    db.commit()


def seed_assignments(db: Session, courses: dict) -> None:
    existing_titles = {a.title for a in db.query(Assignment).all()}
    samples = [
        ("CS301", "ER Diagram Draft", 3),
        ("CS301", "Normalization Worksheet", 7),
        ("CS301", "Final Project Submission", 4),
        ("CS302", "Scheduling Algorithms", 5),
        ("CS303", "TCP/IP Lab Report", 10),
    ]
    for code, title, days_out in samples:
        if title in existing_titles:
            continue
        db.add(Assignment(
            course_id=courses[code].id,
            title=title,
            due_date=datetime.utcnow() + timedelta(days=days_out),
            status="active",
        ))
    db.commit()


def seed_clubs(db: Session, users: dict) -> dict:
    admin = users["ADMIN001"]
    existing = {c.name: c for c in db.query(Club).all()}
    created = {}
    for name, description in DEMO_CLUBS:
        if name in existing:
            created[name] = existing[name]
            continue
        club = Club(name=name, description=description, created_by=admin.id)
        db.add(club)
        db.flush()
        created[name] = club
    db.commit()
    return created


def seed_club_members(db: Session, users: dict, clubs: dict) -> None:
    pairs = [
        ("Coding Club", ["U22107001", "U22107002", "U22107003", "U22107007", "U22107008"]),
        ("Photography Society", ["U22107004", "U22107005", "U22107013", "U22107014"]),
        ("Debate Club", ["U22107009", "U22107010", "U22107015", "U22107016", "U22107017"]),
    ]
    existing = {
        (m.club_id, m.student_id) for m in db.query(ClubMember).all()
    }
    for club_name, student_ids in pairs:
        club = clubs[club_name]
        for sid in student_ids:
            student = users[sid]
            if (club.id, student.id) in existing:
                continue
            db.add(ClubMember(club_id=club.id, student_id=student.id))
    db.commit()


def seed_posts(db: Session, users: dict, clubs: dict) -> None:
    existing_bodies = {p.body for p in db.query(ClubPost).all()}
    # rotate post authors so each club has multiple authors
    author_pools = {
        "Coding Club": ["U22107001", "U22107002", "U22107003"],
        "Photography Society": ["U22107004", "U22107005", "U22107013"],
        "Debate Club": ["U22107009", "U22107010", "U22107015"],
    }
    counters = {k: 0 for k in author_pools}
    for club_name, body in DEMO_POSTS:
        if body in existing_bodies:
            continue
        pool = author_pools[club_name]
        author_sid = pool[counters[club_name] % len(pool)]
        counters[club_name] += 1
        db.add(ClubPost(
            club_id=clubs[club_name].id,
            author_id=users[author_sid].id,
            body=body,
        ))
    db.commit()


def main() -> None:
    db = SessionLocal()
    try:
        print("Seeding users...")
        users = seed_users(db)
        print(f"  {len(users)} users present")

        print("Seeding courses...")
        courses = seed_courses(db)
        print(f"  {len(courses)} courses present")

        print("Seeding enrollments...")
        seed_enrollments(db, users, courses)

        print("Seeding assignments...")
        seed_assignments(db, courses)

        print("Seeding clubs...")
        clubs = seed_clubs(db, users)
        print(f"  {len(clubs)} clubs present")

        print("Seeding club members...")
        seed_club_members(db, users, clubs)

        print("Seeding club posts...")
        seed_posts(db, users, clubs)

        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
