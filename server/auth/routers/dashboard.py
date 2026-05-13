from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db_config import get_connection
from jwt import get_current_user
from models import (
    Assignment, Club, ClubMember, Course, CourseEnrollment,
    RoomBooking, User,
)
from schemas import (
    AssignmentOut, BookingOut, ClubOut, CourseOut, DashboardOut,
)


router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardOut)
def get_dashboard(
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    student_id = UUID(current_user["sub"])
    user = db.query(User).filter(User.id == student_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    enrolled_courses = (
        db.query(Course)
        .join(CourseEnrollment, CourseEnrollment.course_id == Course.id)
        .filter(CourseEnrollment.student_id == student_id)
        .all()
    )

    # upcoming assignments in the next 14 days for courses the user is enrolled in
    horizon = datetime.utcnow() + timedelta(days=14)
    course_ids = [c.id for c in enrolled_courses]
    assignments_rows = []
    if course_ids:
        assignments_rows = (
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

    my_bookings = (
        db.query(RoomBooking)
        .filter(
            RoomBooking.student_id == student_id,
            RoomBooking.status == "active",
        )
        .order_by(RoomBooking.booked_at.desc())
        .limit(5)
        .all()
    )

    my_clubs = (
        db.query(Club)
        .join(ClubMember, ClubMember.club_id == Club.id)
        .filter(ClubMember.student_id == student_id)
        .all()
    )

    return DashboardOut(
        student_id=user.id,
        full_name=user.full_name,
        group=user.group,
        enrolled_courses=[CourseOut.model_validate(c) for c in enrolled_courses],
        upcoming_assignments=[
            AssignmentOut(
                id=a.id,
                course_code=c.code,
                course_name=c.name,
                title=a.title,
                due_date=a.due_date,
                status=a.status,
            )
            for a, c in assignments_rows
        ],
        my_bookings=[BookingOut.model_validate(b) for b in my_bookings],
        my_clubs=[ClubOut.model_validate(c) for c in my_clubs],
    )
