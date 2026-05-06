"""
ADK agent definition + a synchronous handle_query() helper that the
FastAPI layer can call.

The agent is built once at import time. Each request reuses the same
agent + Runner, so the MCP server subprocess is spun up once and kept
alive for the lifetime of the container - NOT per request.
"""
import os
import asyncio
import logging

from dotenv import load_dotenv

from google.adk.agents import LlmAgent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import (
  MCPToolset,
  StdioServerParameters,
  StdioConnectionParams,
)
from google.genai import types as genai_types

load_dotenv()

log = logging.getLogger(__name__)

MODEL = os.getenv("MODEL", "gemini-2.5-flash")
APP_NAME = "ai-travel-agent"
DEFAULT_USER_ID = "default-user"

# ---- ADK AGENT (uses MCP tools) ----
# Use `python -m app.adk_mcp_server.server` so the path works regardless
# of the current working directory (Docker, local dev, anywhere).
root_agent = LlmAgent(
  model=Gemini(model=MODEL),
  name="tourist_agent",
  instruction="""
You are a helpful tourist assistant.

IMPORTANT:
- ALWAYS use available tools to answer user queries.
- NEVER answer from your own knowledge when a tool is available.

Mapping:
- "tourist places in <city>" -> call get_places(city=<city>)
- "directions from X to Y" / "distance from X to Y" -> call get_directions(origin=X, destination=Y)

After calling the tool:
- Read the JSON result.
- Convert it into a clear, friendly, human-readable answer.
- If the result has an "error" field, apologize and explain briefly.
""",
  tools=[
    MCPToolset(
      connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
          command="python",
          args=["-m", "app.adk_mcp_server.server"],
          env={
            "GOOGLE_MAPS_API_KEY": os.getenv("GOOGLE_MAPS_API_KEY", ""),
          },
        ),
        timeout=20,
      )
    )
  ],
)

# Alias used by ADK CLI (`adk run app/agent`) for local interactive testing
agent = root_agent

# ---- Programmatic runner (used by FastAPI) ----
_session_service = InMemorySessionService()
_runner = Runner(
  agent=root_agent,
  app_name=APP_NAME,
  session_service=_session_service,
)


async def _run_async(message: str, user_id: str, session_id: str) -> str:
  # Ensure a session exists
  session = await _session_service.get_session(
    app_name=APP_NAME, user_id=user_id, session_id=session_id
  )
  if session is None:
    await _session_service.create_session(
      app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

  content = genai_types.Content(
    role="user", parts=[genai_types.Part(text=message)]
  )

  final_text = ""
  async for event in _runner.run_async(
    user_id=user_id, session_id=session_id, new_message=content
  ):
    if event.is_final_response() and event.content and event.content.parts:
      final_text = "".join(
        part.text for part in event.content.parts if part.text
      )
  return final_text or "(no response)"


def handle_query(message: str, user_id: str = DEFAULT_USER_ID, session_id: str = "default-session") -> str:
  """Synchronous wrapper so FastAPI route handlers can call the agent."""
  try:
    return asyncio.run(_run_async(message, user_id, session_id))
  except RuntimeError:
    # If we're already inside an event loop (rare in FastAPI sync routes),
    # fall back to creating a new loop.
    loop = asyncio.new_event_loop()
    try:
      return loop.run_until_complete(_run_async(message, user_id, session_id))
    finally:
      loop.close()