from fastapi import FastAPI
from pydantic import BaseModel
import subprocess

app = FastAPI()

class Request(BaseModel):
    message: str

@app.get("/")
def home():
    return {"message": "AI Travel Agent Running"}

@app.post("/chat")
def chat(req: Request):
    
    process = subprocess.Popen(
        ["adk", "run", "app/agent"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    output, error = process.communicate(req.message + "\n")

    return {"response": output}