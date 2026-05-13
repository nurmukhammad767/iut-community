from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db_config import get_connection
from jwt import get_current_user
from models import Club, ClubMember, ClubPost, User
from rate_limiter import rate_limit
from schemas import PostCreate, PostOut


# 5-token burst, 1 token / 5s refill = max 12 posts/min sustained
_post_limit = rate_limit("posts:create", capacity=5, refill_rate=0.2)


router = APIRouter(prefix="/clubs", tags=["Posts"])


def _ensure_member(db: Session, club_id: UUID, student_id: UUID) -> None:
    if not db.query(Club).filter(Club.id == club_id).first():
        raise HTTPException(status_code=404, detail="Club not found")
    member = (
        db.query(ClubMember)
        .filter(ClubMember.club_id == club_id, ClubMember.student_id == student_id)
        .first()
    )
    if not member:
        raise HTTPException(status_code=403, detail="Join the club to post or read")


@router.get("/{club_id}/posts", response_model=List[PostOut])
def list_posts(
    club_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    _ensure_member(db, club_id, UUID(current_user["sub"]))
    rows = (
        db.query(ClubPost, User)
        .join(User, ClubPost.author_id == User.id)
        .filter(ClubPost.club_id == club_id)
        .order_by(ClubPost.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        PostOut(
            id=p.id,
            club_id=p.club_id,
            author_id=p.author_id,
            author_name=u.full_name,
            body=p.body,
            created_at=p.created_at,
        )
        for p, u in rows
    ]


@router.post(
    "/{club_id}/posts",
    response_model=PostOut,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Missing or invalid JWT"},
        403: {"description": "Not a member of this club"},
        429: {"description": "Rate limit exceeded (token bucket empty)"},
    },
    dependencies=[Depends(_post_limit)],
)
def create_post(
    club_id: UUID,
    payload: PostCreate,
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    student_id = UUID(current_user["sub"])
    _ensure_member(db, club_id, student_id)

    author = db.query(User).filter(User.id == student_id).first()
    if not author:
        raise HTTPException(status_code=404, detail="Author not found")

    post = ClubPost(club_id=club_id, author_id=student_id, body=payload.body)
    db.add(post)
    db.commit()
    db.refresh(post)

    return PostOut(
        id=post.id,
        club_id=post.club_id,
        author_id=post.author_id,
        author_name=author.full_name,
        body=post.body,
        created_at=post.created_at,
    )
