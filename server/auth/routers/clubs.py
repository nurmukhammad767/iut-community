from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db_config import get_connection
from jwt import get_current_user
from models import Club, ClubMember, User
from schemas import ClubMemberOut, ClubOut


router = APIRouter(prefix="/clubs", tags=["Clubs"])


@router.get("", response_model=List[ClubOut])
def list_clubs(
    db: Session = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    return db.query(Club).order_by(Club.created_at.desc()).all()


@router.get("/{club_id}", response_model=ClubOut)
def get_club(
    club_id: UUID,
    db: Session = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.post("/{club_id}/join", status_code=status.HTTP_201_CREATED)
def join_club(
    club_id: UUID,
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")

    student_id = UUID(current_user["sub"])
    existing = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club_id, ClubMember.student_id == student_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Already a member")

    membership = ClubMember(club_id=club_id, student_id=student_id)
    db.add(membership)
    db.commit()
    return {"message": f"Joined club '{club.name}'"}


@router.delete("/{club_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
def leave_club(
    club_id: UUID,
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    student_id = UUID(current_user["sub"])
    membership = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club_id, ClubMember.student_id == student_id)
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Not a member")
    db.delete(membership)
    db.commit()


@router.get("/{club_id}/members", response_model=List[ClubMemberOut])
def list_members(
    club_id: UUID,
    db: Session = Depends(get_connection),
    _user: dict = Depends(get_current_user),
):
    if not db.query(Club).filter(Club.id == club_id).first():
        raise HTTPException(status_code=404, detail="Club not found")

    rows = (
        db.query(ClubMember, User)
        .join(User, ClubMember.student_id == User.id)
        .filter(ClubMember.club_id == club_id)
        .order_by(ClubMember.joined_at.asc())
        .all()
    )
    return [
        ClubMemberOut(
            student_id=user.id,
            full_name=user.full_name,
            group=user.group,
            joined_at=member.joined_at,
        )
        for member, user in rows
    ]
