from fastapi import APIRouter

sunat = APIRouter()

@sunat.get("/")
def helloworld():
    return "hello world....."