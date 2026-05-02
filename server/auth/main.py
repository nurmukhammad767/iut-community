from fastapi import FastAPI, Response
from schemas import Registration, Login
app=FastAPI(title="Registration and Login APIS")



@app.post('/register')
def registration(reg : Registration):
    print(reg)
    return Response('sucess')


@app.post('/login')
def login(login : Login):
    print(login)
    return 'Success'