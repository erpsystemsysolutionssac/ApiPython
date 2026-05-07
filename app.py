from fastapi import FastAPI
from routes.sunat import sunat

app = FastAPI()

app.include_router(sunat)