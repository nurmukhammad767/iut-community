from fastapi import FastAPI, HTTPException, Depends
from schemas import Registration, Login, TokenResponse
from jwt import hash_password, verify_password, create_access_token, get_current_user

app = FastAPI()

# ── Fake DB (replace with real DB like SQLAlchemy) ──────────────────────────
fake_db: dict = {

    "U2310249": {
        "password": hash_password("123456"),
        "full_name": "Nurmuhammad",
        "role": "student",
    },
    "U2310268": {
        "password": hash_password("123456"),
        "full_name": "Behruz",
        "role": "student",
    }
}  # { student_id: { password, full_name, role } }


# ── REGISTER ─────────────────────────────────────────────────────────────────
@app.post("/register", status_code=201)
def register(data: Registration):
    # 1. Check duplicate
    if data.student_id in fake_db:
        raise HTTPException(status_code=400, detail="Student ID already registered")

    # 2. Save to DB with hashed password
    fake_db[data.student_id] = {
        "password": hash_password(data.password),
        "full_name": data.full_name,
        "role": data.role,
    }

    return {"message": f"User '{data.full_name}' registered successfully"}


# ── LOGIN ─────────────────────────────────────────────────────────────────────
@app.post("/login", response_model=TokenResponse)
def login(data: Login):
    # 1. Find user
    user = fake_db.get(data.student_id)
    if not user:
        raise HTTPException(status_code=404, detail="Student ID not found")

    # 2. Verify password
    if not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    # 3. Create JWT token
    token = create_access_token(data={
        "sub": data.student_id,
        "full_name": user["full_name"],
        "role": user["role"],
    })

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        full_name=user["full_name"],
        role=user["role"],
    )


# ── PROTECTED EXAMPLE ─────────────────────────────────────────────────────────
# @app.get("/me")
# def get_me(current_user: dict = Depends(get_current_user)):
#     return {
#         "student_id": current_user["sub"],
#         "full_name": current_user["full_name"],
#         "role": current_user["role"],
#     }