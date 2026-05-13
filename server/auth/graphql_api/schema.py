"""GraphQL schema exposing a single `dashboard` query.

REST would require 4+ round-trips (user, courses, assignments, bookings, clubs).
GraphQL collapses this to one request with client-selected fields, which is
the textbook use case for protocol choice justification (R7).
"""
from datetime import datetime, timedelta
from uuid import UUID

import graphene

from db_config import SessionLocal
from models import (
    Assignment, Club, ClubMember, Course, CourseEnrollment,
    RoomBooking, User,
)


class CourseType(graphene.ObjectType):
    id = graphene.String()
    code = graphene.String()
    name = graphene.String()


class AssignmentType(graphene.ObjectType):
    id = graphene.String()
    course_code = graphene.String()
    course_name = graphene.String()
    title = graphene.String()
    due_date = graphene.DateTime()
    status = graphene.String()


class BookingType(graphene.ObjectType):
    id = graphene.String()
    room_name = graphene.String()
    day = graphene.String()
    start_period = graphene.Int()
    end_period = graphene.Int()
    status = graphene.String()
    booked_at = graphene.DateTime()


class ClubType(graphene.ObjectType):
    id = graphene.String()
    name = graphene.String()
    description = graphene.String()


class DashboardType(graphene.ObjectType):
    student_id = graphene.String()
    full_name = graphene.String()
    group = graphene.String()
    enrolled_courses = graphene.List(CourseType)
    upcoming_assignments = graphene.List(AssignmentType)
    my_bookings = graphene.List(BookingType)
    my_clubs = graphene.List(ClubType)


class Query(graphene.ObjectType):
    dashboard = graphene.Field(
        DashboardType,
        student_id=graphene.String(required=True),
        description="Personalized dashboard payload for a student.",
    )

    def resolve_dashboard(self, info, student_id: str):
        try:
            sid = UUID(student_id)
        except ValueError:
            return None

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.id == sid).first()
            if not user:
                return None

            enrolled = (
                db.query(Course)
                .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
                .filter(CourseEnrollment.student_id == sid)
                .all()
            )

            horizon = datetime.utcnow() + timedelta(days=14)
            course_ids = [c.id for c in enrolled]
            assignment_rows = []
            if course_ids:
                assignment_rows = (
                    db.query(Assignment, Course)
                    .join(Course, Assignment.course_id == Course.id)
                    .filter(
                        Assignment.course_id.in_(course_ids),
                        Assignment.status == "active",
                        Assignment.due_date <= horizon,
                    )
                    .order_by(Assignment.due_date.asc())
                    .all()
                )

            bookings = (
                db.query(RoomBooking)
                .filter(
                    RoomBooking.student_id == sid,
                    RoomBooking.status == "active",
                )
                .order_by(RoomBooking.booked_at.desc())
                .limit(10)
                .all()
            )

            clubs = (
                db.query(Club)
                .join(ClubMember, ClubMember.club_id == Club.id)
                .filter(ClubMember.student_id == sid)
                .all()
            )

            return DashboardType(
                student_id=str(user.id),
                full_name=user.full_name,
                group=user.group,
                enrolled_courses=[
                    CourseType(id=str(c.id), code=c.code, name=c.name)
                    for c in enrolled
                ],
                upcoming_assignments=[
                    AssignmentType(
                        id=str(a.id),
                        course_code=c.code,
                        course_name=c.name,
                        title=a.title,
                        due_date=a.due_date,
                        status=a.status,
                    )
                    for a, c in assignment_rows
                ],
                my_bookings=[
                    BookingType(
                        id=str(b.id),
                        room_name=b.room_name,
                        day=b.day,
                        start_period=b.start_period,
                        end_period=b.end_period,
                        status=b.status,
                        booked_at=b.booked_at,
                    )
                    for b in bookings
                ],
                my_clubs=[
                    ClubType(id=str(c.id), name=c.name, description=c.description)
                    for c in clubs
                ],
            )
        finally:
            db.close()


schema = graphene.Schema(query=Query)
