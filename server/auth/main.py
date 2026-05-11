from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from schemas import Registration, Login, TokenResponse
from jwt import hash_password, verify_password, create_access_token, get_current_user
from db_config import get_connection
from models import User, UserRole

app = FastAPI()

@app.post("/register", status_code=201, tags=["Auth"])
def register(data: Registration, db: Session = Depends(get_connection)):
    # 1. Check duplicate
    existing = db.query(User).filter(
        User.student_identifier == data.student_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already registered")

    # 2. Save to DB with hashed password
    new_user = User(
        student_identifier=data.student_id,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole[data.role],
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": f"User '{new_user.full_name}' registered successfully"}


@app.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(data: Login, db: Session = Depends(get_connection)):
    # 1. Find user
    user = db.query(User).filter(
        User.student_identifier == data.student_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student ID not found")

    # 2. Verify password
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # 3. Create JWT token
    token = create_access_token(data={
        "sub": str(user.id),
        "student_id": user.student_identifier,
        "full_name": user.full_name,
        "role": user.role.value,
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        full_name=user.full_name,
        role=user.role.value,
    )


@app.get("/me", tags=["Auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "student_id": current_user["student_id"],
        "full_name": current_user["full_name"],
        "role": current_user["role"],
    }