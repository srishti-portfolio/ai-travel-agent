from fastapi import FastAPI
from pydantic import BaseModel
from app.agent import handle_query

app = FastAPI(title="AI Tourist Agent")

class ChatRequest(BaseModel):
  message: str

@app.post("/chat")
def chat(request: ChatRequest):
  response = handle_query(request.message)

  return {
    "user": request.message,
    "response": response
  }