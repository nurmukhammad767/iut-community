import uuid
from sqlalchemy import (
    Column, String, Text, DateTime, Enum, ForeignKey, Index, UniqueConstraint
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