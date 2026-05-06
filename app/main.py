"""
FastAPI entrypoint for the AI Travel Agent.

Endpoints:
- GET  /         -> health check
- GET  /healthz  -> Cloud Run health probe
- POST /chat     -> { "message": "..." } -> agent response
"""
import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.agent.agent import handle_query

logging.basicConfig(
  level=logging.INFO,
  format="[app] %(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

app = FastAPI(title="AI Travel Agent", version="1.0.0")


class ChatRequest(BaseModel):
  message: str = Field(..., min_length=1, max_length=2000)
  session_id: str | None = None


class ChatResponse(BaseModel):
  user: str
  response: str


@app.get("/")
def home():
  return {
    "service": "AI Travel Agent",
    "status": "ok",
    "endpoints": ["/chat (POST)", "/healthz (GET)"],
}


@app.get("/healthz")
def healthz():
  return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
  log.info("chat request: %s", req.message)
  try:
    answer = handle_query(
        req.message,
        session_id=req.session_id or "default-session",
    )
  except Exception as e:
    log.exception("agent failed")
    raise HTTPException(status_code=500, detail=f"Agent error: {e}")
  return ChatResponse(user=req.message, response=answer)