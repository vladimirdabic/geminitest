from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from google.genai import types
from uuid import uuid4
from session import SessionStorage
import os

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("API_KEY"))
session_storage = SessionStorage(client=client)

class Prompt(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/prompt")
def update_item(req: Request, resp: Response, prompt: Prompt):
    session_id = req.cookies.get("session_id")
    if not session_id:
        resp.set_cookie('session_id', value=str(uuid4()), max_age=86400, samesite='lax')

    session = session_storage.get_or_new(
        session_id,
        "You are an expert in quantum computing and programming, and a good teacher and lecturer. You have a teaching philosophy similar to Leonard Susskind and Richard Feynman, but you do not oversimplify. You think that the student should understand the mathematical explanation behind each concept, such that their understanding is concrete."
    )
    response = session.chat.send_message(message=prompt.message)

    return {"message": response.text}
