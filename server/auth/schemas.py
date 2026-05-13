from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Registration(BaseModel):
    student_id : str
    password : str
    full_name : str
    group : str
    role : str

class Login(BaseModel):
    student_id : str
    password : str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str


# ---------- Clubs ----------

class ClubOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    description: str
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ClubMemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    student_id: UUID
    full_name: str
    group: str
    joined_at: datetime


# ---------- Posts ----------

class PostCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    club_id: UUID
    author_id: UUID
    author_name: str
    body: str
    created_at: datetime


# ---------- Dashboard ----------

class AssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    course_code: str
    course_name: str
    title: str
    due_date: datetime
    status: str


class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    code: str
    name: str


class DashboardOut(BaseModel):
    student_id: UUID
    full_name: str
    group: str
    enrolled_courses: List[CourseOut]
    upcoming_assignments: List[AssignmentOut]
    my_clubs: List[ClubOut]