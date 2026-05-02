from pydantic import BaseModel

class Registration(BaseModel):
    student_id : str
    password : str
    full_name : str
    role : str

class Login(BaseModel):
    student_id : str
    password : str
