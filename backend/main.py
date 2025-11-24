from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
import os

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = genai.Client(api_key=os.getenv("API_KEY"))

class Prompt(BaseModel):
    message: str

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/prompt")
def update_item(prompt: Prompt):
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt.message,
    )

    return {"message": response.text}
