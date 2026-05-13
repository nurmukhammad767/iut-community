from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from schemas import Registration, Login, TokenResponse
from jwt import hash_password, verify_password, create_access_token, get_current_user
from db_config import engine, get_connection
from models import User, UserRole
from graphql_api.router import router as graphql_router
from routers import bookings, clubs, dashboard, posts
from telemetry import init_telemetry
from ws import chat as ws_chat
from ws import notifications as ws_notifications

app = FastAPI(title="IUT Community API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
init_telemetry(app, sqlalchemy_engine=engine)


@app.get("/healthz", tags=["Health"])
def healthz():
    return {"status": "ok"}


app.include_router(clubs.router)
app.include_router(posts.router)
app.include_router(bookings.router)
app.include_router(dashboard.router)
app.include_router(ws_chat.router)
app.include_router(ws_notifications.router)
app.include_router(graphql_router)

@app.post("/register", status_code=201, tags=["Auth"])
def register(data: Registration, db: Session = Depends(get_connection)):
    existing = db.query(User).filter(
        User.student_identifier == data.student_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Student ID already registered")
    new_user = User(
        student_identifier=data.student_id,
        password_hash=hash_password(data.password[:72]),
        full_name=data.full_name,
        group = data.group,
        role=UserRole[data.role],
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": f"User '{new_user.full_name}' registered successfully"}

@app.post("/login", response_model=TokenResponse, tags=["Auth"])
def login(data: Login, db: Session = Depends(get_connection)):
    user = db.query(User).filter(
        User.student_identifier == data.student_id
    ).first()
    if not user:
        raise HTTPException(status_code=404, detail="Student ID not found")
    if not verify_password(data.password[:72], user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect password")
    token = create_access_token(data={
        "sub": str(user.id),
        "student_id": user.student_identifier,
        "full_name": user.full_name,
        "group": user.group,
        "role": user.role.value if hasattr(user.role, "value") else str(user.role),
    })
    return TokenResponse(
        token_type="bearer",
        access_token=token
    )

@app.get("/me", tags=["Auth"])
def get_me(current_user: dict = Depends(get_current_user)):
    return {
        "student_id": current_user["student_id"],
        "full_name": current_user["full_name"],
        "group": current_user["group"],
        "role": current_user["role"]
    }