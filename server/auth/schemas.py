from pydantic import BaseModel

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
    full_name: str
    role: str