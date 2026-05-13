from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from db_config import get_connection
from jwt import get_current_user
from models import RoomBooking
from schemas import BookingCreate, BookingOut


router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _has_conflict(
    db: Session, room: str, day: str, start: int, end: int
) -> bool:
    return (
        db.query(RoomBooking)
        .filter(
            RoomBooking.room_name == room,
            RoomBooking.day == day,
            RoomBooking.status == "active",
            or_(
                and_(RoomBooking.start_period <= start, RoomBooking.end_period >= start),
                and_(RoomBooking.start_period <= end, RoomBooking.end_period >= end),
                and_(RoomBooking.start_period >= start, RoomBooking.end_period <= end),
            ),
        )
        .first()
        is not None
    )


@router.post(
    "",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"description": "Time slot conflict with another booking"}},
)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    if payload.start_period > payload.end_period:
        raise HTTPException(
            status_code=400,
            detail="start_period must be <= end_period",
        )

    if _has_conflict(
        db, payload.room_name, payload.day,
        payload.start_period, payload.end_period,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Room {payload.room_name} on {payload.day} "
                   f"periods {payload.start_period}-{payload.end_period} is taken",
        )

    booking = RoomBooking(
        student_id=UUID(current_user["sub"]),
        room_name=payload.room_name,
        day=payload.day,
        start_period=payload.start_period,
        end_period=payload.end_period,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=List[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    student_id = UUID(current_user["sub"])
    return (
        db.query(RoomBooking)
        .filter(
            RoomBooking.student_id == student_id,
            RoomBooking.status == "active",
        )
        .order_by(RoomBooking.booked_at.desc())
        .all()
    )


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: UUID,
    db: Session = Depends(get_connection),
    current_user: dict = Depends(get_current_user),
):
    booking = db.query(RoomBooking).filter(RoomBooking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    if str(booking.student_id) != current_user["sub"]:
        raise HTTPException(status_code=403, detail="Not your booking")

    booking.status = "cancelled"
    db.commit()
