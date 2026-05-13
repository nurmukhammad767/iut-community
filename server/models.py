import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Enum, ForeignKey, Index, Integer,
    UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()
metadata = Base.metadata


# ----- Enums -----

class UserRole(enum.Enum):
    student = "student"
    professor = "professor"
    admin = "admin"


# ----- Models -----

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_identifier = Column(String(50), unique=True, nullable=False, comment="Can be email or university ID")
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False, comment="Needed to display names in Chat")
    group=Column(String(50), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.student)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_users_identifier", "student_identifier"),
    )


class Course(Base):
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False, comment="e.g., CS101")
    name = Column(String(100), nullable=False)


class CourseEnrollment(Base):
    __tablename__ = "course_enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE")
    )
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", deferrable=True, initially="IMMEDIATE")
    )

    __table_args__ = (
        UniqueConstraint("student_id", "course_id", name="idx_unique_enrollment"),
    )


class Assignment(Base):
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(
        UUID(as_uuid=True),
        ForeignKey("courses.id", deferrable=True, initially="IMMEDIATE")
    )
    title = Column(String(255), nullable=False)
    due_date = Column(DateTime, nullable=False)
    status = Column(String(20), default="active")

    __table_args__ = (
        Index("idx_assignment_due_date", "due_date"),
    )


class Club(Base):
    __tablename__ = "clubs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    image_url = Column(String(500), comment="Stores relative path or S3 link")
    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE"),
        comment="Admin who created the club"
    )
    created_at = Column(DateTime, default=func.now())


class ClubMember(Base):
    __tablename__ = "club_members"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clubs.id", deferrable=True, initially="IMMEDIATE")
    )
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE")
    )
    joined_at = Column(DateTime, default=func.now())

    __table_args__ = (
        UniqueConstraint("club_id", "student_id", name="idx_unique_club_member"),
    )


class RoomBooking(Base):
    __tablename__ = "room_bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_name = Column(String(50), nullable=False)
    student_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    day = Column(String(20), nullable=False, comment="Monday..Friday")
    start_period = Column(Integer, nullable=False)
    end_period = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False, default="active",
                    comment="active | cancelled | expired")
    booked_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_room_bookings_day_room", "day", "room_name"),
        Index("idx_room_bookings_student", "student_id"),
    )


class ClubPost(Base):
    __tablename__ = "club_posts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clubs.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    author_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE"),
        nullable=False,
    )
    body = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_club_posts_club_created", "club_id", "created_at"),
    )


class RoomUsageDaily(Base):
    __tablename__ = "room_usage_daily"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day = Column(String(20), nullable=False)
    room_name = Column(String(50), nullable=False)
    occupied_periods = Column(Integer, nullable=False, default=0)
    free_periods = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("day", "room_name", "computed_at",
                         name="idx_unique_room_usage_daily"),
        Index("idx_room_usage_day", "day"),
    )


class RateLimitAudit(Base):
    __tablename__ = "rate_limit_audit"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", deferrable=True, initially="IMMEDIATE"),
        nullable=True,
        comment="Null for anonymous denials",
    )
    endpoint = Column(String(255), nullable=False)
    denied_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_rate_limit_audit_user", "user_id", "denied_at"),
    )